import subprocess
import time
import requests
import os
import psutil
from pathlib import Path


class ServerResource:
  def __init__(self, executable_name, model_path):
    self.executable_name = executable_name
    self.model_path = model_path
    self.process = None
    self.port = 8080

  def setup(self):
    print(f"\nStarting server with executable {self.executable_name}")
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    executable_path = None

    # Find the executable in artifacts directory
    for path in artifacts_dir.rglob(self.executable_name):
      if path.is_file() and os.access(path, os.X_OK):
        executable_path = path
        break

    if not executable_path:
      raise FileNotFoundError(f"Could not find executable {self.executable_name} in artifacts directory")

    # Start the server process
    self.process = subprocess.Popen(
      [str(executable_path), "--model", self.model_path, "--port", str(self.port), "--host", "127.0.0.1"],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
    )

    # Wait for server to start
    max_retries = 30
    retry_count = 0
    while retry_count < max_retries:
      try:
        response = requests.get(f"http://127.0.0.1:{self.port}/health")
        if response.status_code == 200:
          print(f"Server started successfully on port {self.port}")
          return
      except requests.exceptions.ConnectionError:
        time.sleep(1)
        retry_count += 1

    raise TimeoutError("Server failed to start within the timeout period")

  def cleanup(self):
    if self.process:
      print(f"\nStopping server process (PID: {self.process.pid})")
      # Try graceful shutdown first
      self.process.terminate()
      try:
        self.process.wait(timeout=5)
      except subprocess.TimeoutExpired:
        # Force kill if graceful shutdown fails
        self.process.kill()
        # Kill any child processes
        parent = psutil.Process(self.process.pid)
        for child in parent.children(recursive=True):
          child.kill()
        parent.kill()
      print("Server stopped")
