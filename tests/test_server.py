import pytest
import requests
import sys
from resources import ServerResource
from pathlib import Path


def pytest_generate_tests(metafunc):
  """Generate test parameters for server tests"""
  if "server_fixture" in metafunc.fixturenames:
    # Get all server executables from artifacts directory
    project_root = Path(__file__).parent.parent
    artifacts_dir = project_root / "artifacts"
    if not artifacts_dir.exists():
      return []

    # Find the most recent release directory
    release_dirs = [d for d in artifacts_dir.iterdir() if d.is_dir()]
    if not release_dirs:
      return []

    latest_release_dir = max(release_dirs, key=lambda x: x.stat().st_mtime)

    # Get all server executables with their names as IDs
    server_executables = [
      {"executable_name": f.name} for f in latest_release_dir.iterdir() if f.name.startswith("llama-server-")
    ]
    ids = [f["executable_name"] for f in server_executables]

    metafunc.parametrize("server_fixture", server_executables, indirect=True, scope="class", ids=ids)


@pytest.fixture(scope="class")
def server_fixture(request, model_path, release_artifacts):
  """Class-scoped fixture that manages server lifecycle"""
  params = request.param
  executable_name = params["executable_name"]

  # Platform-specific skipping logic
  if sys.platform == "darwin":  # macOS
    if not executable_name.startswith("llama-server-macos-"):
      pytest.skip(f"Skipping {executable_name} as it's not a macOS executable")
  elif sys.platform.startswith("linux"):  # Linux
    if not executable_name.startswith("llama-server-linux-"):
      pytest.skip(f"Skipping {executable_name} as it's not a Linux executable")
  elif sys.platform == "win32":  # Windows
    if not (executable_name.startswith("llama-server-windows-") and executable_name.endswith(".exe")):
      pytest.skip(f"Skipping {executable_name} as it's not a Windows executable")

  executable_path = next(x for x in release_artifacts if x.endswith(executable_name))
  if not executable_path:
    raise FileNotFoundError(f"Could not find executable {executable_name} in artifacts directory")

  server = ServerResource(executable_path, model_path)
  server.setup()

  yield server

  server.cleanup()


class TestServer:
  """
  Test class that runs against different server executables.
  Each server instance is started once per class and cleaned up after all tests complete.
  """

  @pytest.mark.timeout(10)
  def test_health_check(self, server_fixture):
    """Test that the server's health endpoint returns 200 OK"""
    response = requests.get(f"http://127.0.0.1:{server_fixture.port}/health")
    assert response.status_code == 200

  @pytest.mark.timeout(60)  # 60 seconds timeout for chat completion
  def test_chat_completion(self, server_fixture):
    """Test that the server can handle a basic chat completion request"""
    url = f"http://127.0.0.1:{server_fixture.port}/v1/chat/completions"

    payload = {
      "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello, World!'"},
      ],
      "model": "default",  # Model name doesn't matter as we only have one loaded
      "stream": False,
    }

    response = requests.post(url, json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "message" in data["choices"][0]
    assert "content" in data["choices"][0]["message"]
    assert data["choices"][0]["message"]["content"].strip() != ""
    assert "hello" in data["choices"][0]["message"]["content"].strip().lower()
