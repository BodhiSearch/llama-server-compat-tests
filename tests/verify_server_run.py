import subprocess
import time
import requests
import os
import psutil
from pathlib import Path


def check_required_files(server_path, model_path):
  if not server_path.exists():
    raise FileNotFoundError(
      f"Server executable not found at: {server_path}\n"
      "Please ensure you have downloaded the server executable to the artifacts directory."
    )

  if not model_path.exists():
    raise FileNotFoundError(
      f"Model file not found at: {model_path}\n"
      "Please ensure you have downloaded the model file to the models directory."
    )

  if not os.access(server_path, os.X_OK):
    raise PermissionError(
      f"Server executable is not executable: {server_path}\nPlease make it executable with: chmod +x {{server_path}}"
    )


def start_server(executable_path, model_path, port=8080):
  print(f"\nStarting server with executable {executable_path}")
  executable_path = Path(executable_path)

  # Wait for server to start
  max_retries = 30
  retry_count = 0

  # Start the server process
  process = subprocess.Popen(
    [str(executable_path), "--model", model_path, "--port", str(port), "--host", "127.0.0.1"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )

  while retry_count < max_retries:
    try:
      response = requests.get(f"http://127.0.0.1:{port}/health")
      if response.status_code == 200:
        try:
          json_response = response.json()
          if json_response.get("status") == "ok":
            print(f"Server started successfully on port {port}")
            return process
        except (ValueError, KeyError):
          pass
    except requests.exceptions.ConnectionError:
      # Check if process is still running
      if process.poll() is not None:
        stdout, stderr = process.communicate()
        raise RuntimeError(
          f"Server process died unexpectedly. Exit code: {process.returncode}\n"
          f"stdout: {stdout.decode()}\n"
          f"stderr: {stderr.decode()}"
        )
    time.sleep(1)
    retry_count += 1

  # If we get here, server didn't start properly
  stop_server(process)  # Clean up the process
  raise TimeoutError("Server failed to start within the timeout period")


def stop_server(process):
  if process:
    try:
      print(f"\nStopping server process (PID: {process.pid})")
      # Try graceful shutdown first
      process.terminate()
      try:
        process.wait(timeout=5)
      except subprocess.TimeoutExpired:
        # Force kill if graceful shutdown fails
        process.kill()
        # Kill any child processes
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
          child.kill()
        parent.kill()
      print("Server stopped")
    except (psutil.NoSuchProcess, ProcessLookupError):
      # Process already died
      pass


def test_chat_completion(port):
  url = f"http://127.0.0.1:{port}/v1/chat/completions"

  payload = {
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Say 'Hello, World!'"},
    ],
    "model": "default",  # Model name doesn't matter as we only have one loaded
    "stream": False,
  }

  print("\nSending chat completion request...")
  response = requests.post(url, json=payload)
  print(f"\nStatus Code: {response.status_code}")
  print("\nResponse Body:")
  print(response.json())
  return response


if __name__ == "__main__":
  artifacts_dir = Path(__file__).parent.parent / "artifacts/build-8c63e5b9"
  models_dir = Path(__file__).parent.parent / "models"
  server_path = artifacts_dir / "llama-server-macos-cpu"
  model_path = (
    models_dir
    / "models--unsloth--DeepSeek-R1-Distill-Qwen-1.5B-GGUF/snapshots/9784122b3247cc074b19c42bf38ee256d8aacce7/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
  )
  port = 8080

  process = None
  try:
    # Check required files before starting
    check_required_files(server_path, model_path)

    process = start_server(server_path, model_path, port)
    response = test_chat_completion(port)
    assert response.status_code == 200, "Chat completion request failed"
    print("\nServer verification completed successfully!")
  except Exception as e:
    print(f"\nError during verification: {e}")
    raise
  finally:
    if process:
      stop_server(process)
