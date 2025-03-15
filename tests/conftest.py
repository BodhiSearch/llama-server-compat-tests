import pytest
import os
import requests
from pathlib import Path
from huggingface_hub import hf_hub_download
import subprocess
import time
import psutil


@pytest.fixture(scope="session", autouse=True)
def model_path():
  """
  Downloads the model from HuggingFace once before any tests run.
  Using scope="session" ensures it runs only once for the entire test suite.
  The autouse=True parameter makes it run automatically without explicit reference.
  """
  # Define model details
  repo_id = "unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF"
  filename = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"

  # Define where to save the model (you might want to customize this path)
  cache_dir = os.path.join(os.path.dirname(__file__), "..", "models")
  os.makedirs(cache_dir, exist_ok=True)

  # Download the model if it doesn't already exist
  model_path = os.path.join(cache_dir, filename)
  if not os.path.exists(model_path):
    print(f"Downloading model {filename} from {repo_id}...")
    model_path = hf_hub_download(
      repo_id=repo_id, filename=filename, cache_dir=cache_dir
    )
    print(f"Model downloaded to {model_path}")
  else:
    print(f"Model already exists at {model_path}")

  # Make the model path available to tests
  return model_path


@pytest.fixture(scope="session")
def release_artifacts():
  """
  Downloads artifacts from the latest GitHub release and returns their paths.
  This fixture runs once before any tests execute.
  """
  # Repository details
  repo_owner = "BodhiSearch"
  repo_name = "llama.cpp"
  latest_release_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

  # Create artifacts directory in project root
  project_root = Path(__file__).parent.parent
  artifacts_dir = project_root / "artifacts"
  artifacts_dir.mkdir(exist_ok=True)

  # Get the latest release
  response = requests.get(
    latest_release_url, headers={"Accept": "application/vnd.github.v3+json"}
  )
  response.raise_for_status()

  latest_release = response.json()
  git_sha = latest_release.get("target_commitish", "latest")
  release_dir = artifacts_dir / git_sha

  # Check if we already have this release's artifacts
  if release_dir.exists() and any(release_dir.iterdir()):
    print(f"Artifacts for commit {git_sha} already exist at {release_dir}")
  else:
    print(f"Downloading artifacts for commit {git_sha}...")
    release_dir.mkdir(exist_ok=True)

    # Download all assets from the release
    for asset in latest_release.get("assets", []):
      asset_name = asset["name"]
      download_url = asset["browser_download_url"]
      asset_path = release_dir / asset_name

      print(f"Downloading {asset_name}...")
      response = requests.get(download_url, stream=True)
      response.raise_for_status()

      with open(asset_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
          f.write(chunk)

  # Collect all artifact paths
  artifact_paths = list(release_dir.glob("*"))
  print(f"Found {len(artifact_paths)} artifacts")

  # Convert Path objects to strings for easier handling in tests
  return [str(path) for path in artifact_paths]


def kill_process_by_port(port):
  """Kill any process running on the specified port"""
  for proc in psutil.process_iter(['pid', 'name', 'connections']):
    try:
      for conn in proc.connections():
        if conn.laddr.port == port:
          proc.kill()
          break
    except (psutil.NoSuchProcess, psutil.AccessDenied):
      pass


class ServerConfig:
  """Server configuration parameters"""
  def __init__(self,
               context_size: int = 2048,
               n_gpu_layers: int = 0,
               batch_size: int = 512,
               port: int = 8080,
               host: str = "127.0.0.1"):
    self.context_size = context_size
    self.n_gpu_layers = n_gpu_layers
    self.batch_size = batch_size
    self.port = port
    self.host = host

  def to_cmd_args(self) -> list:
    """Convert config to command line arguments"""
    return [
      "-c", str(self.context_size),
      "-ngl", str(self.n_gpu_layers),
      "-b", str(self.batch_size),
      "--port", str(self.port),
      "--host", self.host
    ]


class ServerInstance:
  def __init__(self, artifact_path: str, model_path: str, config: ServerConfig = None):
    self.artifact_path = artifact_path
    self.model_path = model_path
    self.config = config or ServerConfig()
    self.process = None

  def start(self):
    # Kill any existing process on the port
    kill_process_by_port(self.config.port)

    # Start the server process
    cmd = [
      self.artifact_path,
      "-m", self.model_path,
    ] + self.config.to_cmd_args()

    self.process = subprocess.Popen(
      cmd,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE
    )

    # Wait for server to start (adjust sleep time as needed)
    time.sleep(2)

    # Check if process is running
    if self.process.poll() is not None:
      stdout, stderr = self.process.communicate()
      raise RuntimeError(
        f"Server failed to start.\nCommand: {' '.join(cmd)}\n"
        f"Stdout: {stdout.decode()}\nStderr: {stderr.decode()}"
      )

  def stop(self):
    if self.process:
      # Try graceful shutdown first
      self.process.terminate()
      try:
        self.process.wait(timeout=5)
      except subprocess.TimeoutExpired:
        # Force kill if graceful shutdown fails
        self.process.kill()
      self.process = None

      # Make sure the port is cleared
      kill_process_by_port(self.config.port)

@pytest.fixture
def server_config(request):
  """Provides server configuration"""
  return ServerConfig()

@pytest.fixture
def server_instance(request, server_config):
  """
  Fixture that manages server lifecycle for each test.
  Usage: def test_something(server_instance, artifact_path, model_path):
  """
  server = None

  def _create_server(artifact_path: str, model_path: str, config: ServerConfig = None):
    nonlocal server
    server = ServerInstance(artifact_path, model_path, config or server_config)
    server.start()
    return server

  yield _create_server

  # Cleanup after test
  if server:
    server.stop()
