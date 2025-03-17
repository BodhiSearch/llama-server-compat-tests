#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, **kwargs):
  """Run a command and return its output and return code."""
  print("\n" + "=" * 80)
  print(f"Running command: {' '.join(cmd)}")
  print("=" * 80)

  try:
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, **kwargs)

    stdout_lines = []
    stderr_lines = []

    while True:
      stdout_line = process.stdout.readline()
      stderr_line = process.stderr.readline()

      if not stdout_line and not stderr_line and process.poll() is not None:
        break

      if stdout_line:
        stdout_lines.append(stdout_line)
        print(stdout_line, end="")
      if stderr_line:
        stderr_lines.append(stderr_line)
        print(stderr_line, end="", file=sys.stderr)

    process.wait()
    return "".join(stdout_lines), "".join(stderr_lines), process.returncode

  except Exception as e:
    error_msg = str(e)
    print(f"Error: {error_msg}", file=sys.stderr)
    return "", error_msg, 1


def check_poetry():
  """Check if poetry is installed, install if not present."""
  stdout, stderr, code = run_command(["poetry", "--version"])
  if code != 0:
    print("Poetry not found. Attempting to install poetry...")
    if sys.platform == "win32":
      cmd = [sys.executable, "-m", "pip", "install", "poetry"]
    else:
      cmd = ["pip", "install", "poetry"]

    stdout, stderr, code = run_command(cmd)
    if code != 0:
      print(f"Failed to install poetry:\n{stderr}")
      sys.exit(1)
    print("Poetry installed successfully!")
  return True


def setup_reports_dir():
  """Create or clean the reports directory."""
  reports_dir = Path("reports")
  if reports_dir.exists():
    shutil.rmtree(reports_dir)
  reports_dir.mkdir()
  return reports_dir


def main():
  # Check/install poetry
  check_poetry()

  # Install dependencies
  print("\nInstalling dependencies...")
  stdout, stderr, code = run_command(["poetry", "install", "--no-root"])
  if code != 0:
    print(f"Failed to install dependencies:\n{stderr}")
    sys.exit(1)
  print("Dependencies installed successfully!")

  # Setup reports directory
  reports_dir = setup_reports_dir()

  # Run pytest
  print("\nRunning tests...")
  stdout, stderr, code = run_command(["poetry", "run", "pytest", "-s", "-vv"])

  # Write output to report file
  report_path = reports_dir / "pytest.txt"
  with open(report_path, "w") as f:
    f.write(stdout)
    if stderr:
      f.write("\nErrors:\n")
      f.write(stderr)

  print(f"\nTest results saved to {report_path}")
  sys.exit(code)


if __name__ == "__main__":
  main()
