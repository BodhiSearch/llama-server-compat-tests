#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime


class OutputCapture:
  """Captures all output while still printing to terminal."""
  def __init__(self):
    self.output_lines = []

  def write(self, text):
    self.output_lines.append(text)
    sys.__stdout__.write(text)

  def write_err(self, text):
    self.output_lines.append(text)
    sys.__stderr__.write(text)

  def get_output(self):
    return "".join(self.output_lines)


def run_command(cmd, output_capture, **kwargs):
  """Run a command and return its output and return code."""
  output_capture.write("\n" + "=" * 80 + "\n")
  output_capture.write(f"Running command: {' '.join(cmd)}\n")
  output_capture.write("=" * 80 + "\n")

  try:
    # Use pipe redirection to capture both stdout and stderr in order
    process = subprocess.Popen(
      cmd,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,  # Redirect stderr to stdout
      text=True,
      bufsize=1,
      **kwargs
    )

    while True:
      line = process.stdout.readline()
      if not line and process.poll() is not None:
        break
      if line:
        output_capture.write(line)

    process.wait()
    return process.returncode

  except Exception as e:
    error_msg = str(e)
    output_capture.write_err(f"Error: {error_msg}\n")
    return 1


def check_poetry(output_capture):
  """Check if poetry is installed, install if not present."""
  code = run_command(["poetry", "--version"], output_capture)
  if code != 0:
    output_capture.write("Poetry not found. Attempting to install poetry...\n")
    if sys.platform == "win32":
      cmd = [sys.executable, "-m", "pip", "install", "poetry"]
    else:
      cmd = ["pip", "install", "poetry"]

    code = run_command(cmd, output_capture)
    if code != 0:
      output_capture.write("Failed to install poetry\n")
      sys.exit(1)
    output_capture.write("Poetry installed successfully!\n")
  return True


def setup_reports_dir():
  """Create or clean the reports directory."""
  reports_dir = Path("reports")
  if reports_dir.exists():
    shutil.rmtree(reports_dir)
  reports_dir.mkdir()
  return reports_dir


def main():
  # Initialize output capture
  output_capture = OutputCapture()
  start_time = datetime.now()
  output_capture.write(f"Script started at: {start_time}\n")

  try:
    # Check/install poetry
    check_poetry(output_capture)

    # Install dependencies
    output_capture.write("\nInstalling dependencies...\n")
    code = run_command(["poetry", "install", "--no-root"], output_capture)
    if code != 0:
      output_capture.write("Failed to install dependencies\n")
      sys.exit(1)
    output_capture.write("Dependencies installed successfully!\n")

    # Setup reports directory
    reports_dir = setup_reports_dir()

    # Run pytest
    output_capture.write("\nRunning tests...\n")
    code = run_command([
      "poetry", "run", "pytest",
      "-s",  # Show print statements
      "-v",  # Verbose output
      "--verbose",  # Extra verbose (shows skip reasons)
      "-r", "fEsxXa",  # Show extra test summary info (including skip reasons)
    ], output_capture)

    # Add completion time
    end_time = datetime.now()
    duration = end_time - start_time
    output_capture.write(f"\nScript completed at: {end_time}\n")
    output_capture.write(f"Total duration: {duration}\n")

    # Write output to report file
    report_path = reports_dir / "pytest.txt"
    with open(report_path, "w") as f:
      f.write(output_capture.get_output())

    output_capture.write(f"\nTest results saved to {report_path}\n")
    sys.exit(code)

  except KeyboardInterrupt:
    output_capture.write("\nScript interrupted by user\n")
    sys.exit(1)
  except Exception as e:
    output_capture.write_err(f"\nUnexpected error: {str(e)}\n")
    sys.exit(1)


if __name__ == "__main__":
  main()
