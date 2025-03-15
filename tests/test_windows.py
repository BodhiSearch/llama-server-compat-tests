import pytest
import requests
import time
from typing import Callable, List


SUPPORTED_ARTIFACTS = ["llama-server-generic.exe", "llama-server-haswell.exe"]


def wait_for_server(port=8080, max_retries=5):
  """Wait for server to be ready to accept connections"""
  for _ in range(max_retries):
    try:
      response = requests.get(f"http://127.0.0.1:{port}/health")
      if response.status_code == 200:
        return True
    except requests.exceptions.ConnectionError:
      time.sleep(1)
  return False


@pytest.fixture
def server_setup(artifact_name: str, model_path: str, release_artifacts: List[str], server_instance: Callable):
  """Setup server for each test"""
  assert model_path is not None, "Model path not provided"
  print(f"Using model at: {model_path}")
  assert release_artifacts is not None, "No release artifacts found"

  # Get the specific artifact path
  artifact_path = next((path for path in release_artifacts if path.endswith(artifact_name)), None)
  assert artifact_path is not None, f"Artifact {artifact_name} not found in {release_artifacts}"
  print(f"Testing artifact: {artifact_path}")

  # Start server with current artifact
  server = server_instance(artifact_path, model_path)
  assert wait_for_server(), f"Server failed to start with artifact {artifact_name}"

  yield {"server": server, "artifact_path": artifact_path}

  # Cleanup handled by server_instance fixture


@pytest.mark.parametrize("artifact_name", SUPPORTED_ARTIFACTS)
def test_health_check(server_setup):
  """Test that server responds to health check"""
  response = requests.get("http://127.0.0.1:8080/health")
  assert response.status_code == 200, "Health check failed"
  print(f"✓ Health check passed for {server_setup['artifact_path']}")


@pytest.mark.parametrize("artifact_name", SUPPORTED_ARTIFACTS)
@pytest.mark.parametrize(
  "prompt_config", [{"prompt": "Hello, how are you?", "n_predict": 128}, {"prompt": "What is 2+2?", "n_predict": 32}]
)
def test_completion(server_setup, prompt_config):
  """Test model completion with different prompts"""
  response = requests.post("http://127.0.0.1:8080/completion", json=prompt_config)
  assert response.status_code == 200, "Completion request failed"
  result = response.json()
  assert "content" in result, "Response missing content field"
  assert len(result["content"]) > 0, "Empty response from model"
  print(f"✓ Completion test passed for {server_setup['artifact_path']} with prompt: {prompt_config['prompt'][:20]}...")
