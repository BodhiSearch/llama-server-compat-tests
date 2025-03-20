import subprocess
import time
import requests
import os
import random
import re
from pathlib import Path
import threading


class ServerResource:
  def __init__(self, executable_path, model_path):
    self.executable_path = Path(executable_path)
    self.model_path = model_path
    self.process = None
    self.port = random.randint(20000, 65535)  # Random port between 20000 and max port

  def _check_server_crash(self, stderr_output):
    """Check if server crashed due to CPU compatibility issues"""
    cpu_error_patterns = [
      r"illegal instruction",  # Common CPU instruction error
      r"invalid opcode",  # Another CPU instruction error
      r"undefined symbol.*avx",  # AVX-related linking errors
      r"undefined symbol.*sse",  # SSE-related linking errors
      r"SIGILL",  # Illegal instruction signal
    ]

    if stderr_output:
      stderr_text = stderr_output.decode().lower()
      for pattern in cpu_error_patterns:
        if re.search(pattern, stderr_text, re.IGNORECASE):
          raise RuntimeError(
            f"Server crashed due to CPU compatibility issue. This binary requires CPU features "
            f"that are not available on this machine. Error: {stderr_text}"
          )

    return False

  def _read_server_output(self, stdout, stderr):
    """Read server output in real-time and print it."""
    while True:
      # Read stdout
      stdout_line = stdout.readline()
      if stdout_line:
        print(f"Server stdout: {stdout_line.decode().rstrip()}")

      # Read stderr
      stderr_line = stderr.readline()
      if stderr_line:
        print(f"Server stderr: {stderr_line.decode().rstrip()}")

      # If process has ended and no more output, break
      if not stdout_line and not stderr_line and self.process.poll() is not None:
        break

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
        bufsize=1,  # Line buffering
      )

      # Start reading server output in a separate thread
      output_thread = threading.Thread(
        target=self._read_server_output, args=(self.process.stdout, self.process.stderr), daemon=True
      )
      output_thread.start()

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
        except requests.exceptions.ConnectionError:
          # Check if process has crashed
          if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            # Check for CPU compatibility issues
            self._check_server_crash(stderr)
            # If not a CPU issue, raise generic error
            raise RuntimeError(
              f"Server process died unexpectedly. Exit code: {self.process.returncode}\n"
              f"stdout: {stdout.decode() if stdout else ''}\n"
              f"stderr: {stderr.decode() if stderr else ''}"
            )
        time.sleep(1)
        retry_count += 1

      # If we get here, server failed to start
      error_msg = "Server failed to start within the timeout period"
      print(f"Error: {error_msg}")
      if self.process:
        try:
          stdout, stderr = self.process.communicate(timeout=1)
          # Check for CPU compatibility issues before raising timeout error
          self._check_server_crash(stderr)
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
