import subprocess
import time
import requests
import os
import psutil
from pathlib import Path


class ServerResource:
  def __init__(self, executable_path, model_path):
    self.executable_path = Path(executable_path)
    self.model_path = model_path
    self.process = None
    self.port = 8080

  def setup(self):
    print(f"\nStarting server with executable {self.executable_path}")

    if not self.executable_path.is_file():
      raise FileNotFoundError(f"Executable not found: {self.executable_path}")
    if not os.access(self.executable_path, os.X_OK):
      raise PermissionError(f"Executable is not executable: {self.executable_path}")

    # Start the server process
    self.process = subprocess.Popen(
      [str(self.executable_path), "--model", self.model_path, "--port", str(self.port), "--host", "127.0.0.1"],
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
