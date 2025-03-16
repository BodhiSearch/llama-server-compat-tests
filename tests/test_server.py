import pytest
import requests
from resources import ServerResource


@pytest.fixture(scope="class")
def server_fixture(request, model_path, release_artifacts):
  """Class-scoped fixture that manages server lifecycle"""
  params = request.param
  executable_name = params["executable_name"]

  server = ServerResource(executable_name, model_path)
  server.setup()

  yield server

  server.cleanup()


test_params = [{"executable_name": "llama-server-macos-cpu"}, {"executable_name": "llama-server-macos-metal"}]


@pytest.mark.parametrize("server_fixture", test_params, indirect=True)
class TestServer:
  """
  Test class that runs against different server executables.
  Each server instance is started once per class and cleaned up after all tests complete.
  """

  def test_health_check(self, server_fixture):
    """Test that the server's health endpoint returns 200 OK"""
    response = requests.get(f"http://127.0.0.1:{server_fixture.port}/health")
    assert response.status_code == 200

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
