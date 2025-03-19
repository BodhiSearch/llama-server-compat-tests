import subprocess
import time
import requests
import os
import psutil
import random
from pathlib import Path


class ServerResource:
  def __init__(self, executable_path, model_path):
    self.executable_path = Path(executable_path)
    self.model_path = model_path
    self.process = None
    self.port = random.randint(20000, 65535)  # Random port between 20000 and max port

  def setup(self):
    print(f"\nStarting server with executable {self.executable_path}")
    print(f"Selected random port: {self.port}")

    if not self.executable_path.is_file():
      raise FileNotFoundError(f"Executable not found: {self.executable_path}")
    if not os.access(self.executable_path, os.X_OK):
      raise PermissionError(f"Executable is not executable: {self.executable_path}")

    try:
      # Start the server process
      print(f"Launching server on port {self.port}...")
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
            try:
              json_response = response.json()
              if json_response.get("status") == "ok":
                print(f"Server started successfully on port {self.port}")
                return
            except (ValueError, KeyError):
              pass
        except requests.exceptions.ConnectionError as e:
          print(f'server failed to start with error: {e}, retrying...')
        time.sleep(1)
        retry_count += 1

      # If we get here, server failed to start
      error_msg = "Server failed to start within the timeout period"
      print(f"Error: {error_msg}")
      if self.process:
        try:
          stdout, stderr = self.process.communicate(timeout=1)
          if stdout:
            print(f"Server stdout: {stdout.decode()}")
          if stderr:
            print(f"Server stderr: {stderr.decode()}")
        except subprocess.TimeoutExpired:
          pass
      raise TimeoutError(error_msg)
    except Exception as e:
      print(f"Error during server setup: {str(e)}")
      self.cleanup()
      raise  # Re-raise the exception to mark the test as failed

  def cleanup(self):
    """Clean up server resources"""
    if self.process:
      try:
        print(f"\nStopping server process (PID: {self.process.pid})")
        # Try graceful termination first
        self.process.terminate()
        try:
          self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
          # If graceful termination fails, force kill
          print("Graceful termination failed, forcing kill")
          self.process.kill()
      except Exception as e:
        print(f"Warning: Error during process cleanup: {e}")
      finally:
        self.process = None
        print("Server cleanup completed")

  def __enter__(self):
    """Context manager entry"""
    self.setup()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    """Context manager exit"""
    self.cleanup()
