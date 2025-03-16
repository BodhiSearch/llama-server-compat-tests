import pytest
import os
import requests
from pathlib import Path
from huggingface_hub import hf_hub_download


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
    model_path = hf_hub_download(repo_id=repo_id, filename=filename, cache_dir=cache_dir)
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
  response = requests.get(latest_release_url, headers={"Accept": "application/vnd.github.v3+json"})
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
