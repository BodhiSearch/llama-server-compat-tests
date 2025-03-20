#!/usr/bin/env python3

import subprocess
import sys
from datetime import datetime
from pathlib import Path
import re


class TextFilter:
  """Base class for text filters in the pipeline."""

  def filter(self, text: str) -> str:
    """Filter the text and return modified version."""
    return text


class PIIFilter(TextFilter):
  """Filter to remove personally identifiable information from text."""

  def __init__(self):
    # Order matters - project dir replacement should happen before home dir
    self.replacements = [
      # First replace project directory paths
      (r'[^\s"]*?/llama-server-compat-tests/', "$PROJECT_DIR/"),
      (r'[^\s"]*?\\\\llama-server-compat-tests\\\\', "$PROJECT_DIR\\\\"),  # Double escape for Windows paths
      # Then replace home directories
      (r"/Users/[^/]+", "$HOME"),
      (r"/home/[^/]+", "$HOME"),
      (r"C:\\\\Users\\\\[^\\\\]+", "$HOME"),  # Double escape for Windows paths
    ]
    # Compile regex patterns for better performance
    self.patterns = [(re.compile(pattern), repl) for pattern, repl in self.replacements]

  def filter(self, text: str) -> str:
    """Replace PII patterns with generic placeholders in specified order."""
    for pattern, repl in self.patterns:
      text = pattern.sub(repl, text)
    return text


class RealTimeLogger:
  """Logs output in real-time to both console and file."""

  def __init__(self, log_file):
    self.log_file = log_file
    self.file = open(log_file, "w", buffering=1)  # Line buffering
    self.filters = [PIIFilter()]  # Initialize with PII filter, can add more filters

  def apply_filters(self, text: str) -> str:
    """Apply all filters in the pipeline to the text."""
    for filter in self.filters:
      text = filter.filter(text)
    return text

  def write(self, text):
    filtered_text = self.apply_filters(text)
    sys.__stdout__.write(filtered_text)
    self.file.write(filtered_text)
    self.file.flush()  # Ensure immediate write to disk

  def write_err(self, text):
    filtered_text = self.apply_filters(text)
    sys.__stderr__.write(filtered_text)
    self.file.write(filtered_text)
    self.file.flush()  # Ensure immediate write to disk

  def close(self):
    if not self.file.closed:
      self.file.close()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.close()


def run_command(cmd, logger, **kwargs):
  """Run a command and stream its output in real-time."""
  logger.write("\n" + "=" * 80 + "\n")
  logger.write(f"Running command: {' '.join(cmd)}\n")
  logger.write("=" * 80 + "\n")

  try:
    process = subprocess.Popen(
      cmd,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,  # Redirect stderr to stdout
      text=True,
      bufsize=1,  # Line buffering
      **kwargs,
    )

    while True:
      line = process.stdout.readline()
      if not line and process.poll() is not None:
        break
      if line:
        logger.write(line)

    process.wait()
    return process.returncode

  except Exception as e:
    error_msg = str(e)
    logger.write_err(f"Error: {error_msg}\n")
    return 1


def check_poetry(logger):
  """Check if poetry is installed, install if not present."""
  code = run_command(["poetry", "--version"], logger)
  if code != 0:
    logger.write("Poetry not found. Attempting to install poetry...\n")
    if sys.platform == "win32":
      cmd = [sys.executable, "-m", "pip", "install", "poetry"]
    else:
      cmd = ["pip", "install", "poetry"]

    code = run_command(cmd, logger)
    if code != 0:
      logger.write("Failed to install poetry\n")
      sys.exit(1)
    logger.write("Poetry installed successfully!\n")
  return True


def setup_reports_dir():
  """Create the reports directory if it doesn't exist."""
  reports_dir = Path("reports")
  if not reports_dir.exists():
    reports_dir.mkdir()
  return reports_dir


def get_latest_artifacts_dir():
  """Get the most recent artifacts directory by reading latest.txt."""
  artifacts_dir = Path("artifacts")
  latest_txt = artifacts_dir / "latest.txt"

  if not artifacts_dir.exists():
    raise FileNotFoundError("Artifacts directory not found")

  if not latest_txt.exists():
    raise FileNotFoundError("latest.txt not found in artifacts directory")

  # Read the latest release tag from latest.txt
  with open(latest_txt, "r") as f:
    latest_tag = f.read().strip()

  release_dir = artifacts_dir / latest_tag
  if not release_dir.exists():
    raise FileNotFoundError(f"Release directory {latest_tag} referenced in latest.txt not found")

  return release_dir


def run_tests_for_artifact(artifact_path, logger):
  """Run pytest for a specific artifact."""
  logger.write(f"\nRunning tests for artifact: {artifact_path}\n")
  logger.write("=" * 80 + "\n")

  return run_command(
    [
      "poetry",
      "run",
      "pytest",
      "-s",  # Show print statements
      "-v",  # Verbose output
      "--verbose",  # Extra verbose (shows skip reasons)
      "-r",
      "fEsxXa",  # Show extra test summary info
      f"--artifact-path={artifact_path}",  # Pass artifact path to pytest
    ],
    logger,
  )


def main():
  start_time = datetime.now()
  reports_dir = setup_reports_dir()
  timestamp = datetime.now().strftime("%y%m%d%H%M%S")
  report_path = reports_dir / f"pytest_{timestamp}.txt"

  try:
    with RealTimeLogger(report_path) as logger:
      logger.write(f"Script started at: {start_time}\n")

      # Check/install poetry
      check_poetry(logger)

      # Install dependencies
      logger.write("\nInstalling dependencies...\n")
      code = run_command(["poetry", "install"], logger)
      if code != 0:
        logger.write("Failed to install dependencies\n")
        sys.exit(1)
      logger.write("Dependencies installed successfully!\n")

      # Collect system information after dependencies are installed
      logger.write("\nCollecting system information...\n")
      code = run_command(["poetry", "run", "python", "-m", "tests.system_info"], logger)
      if code != 0:
        logger.write("Failed to collect system information\n")
        sys.exit(1)
      logger.write("System information collected successfully!\n")

      # Download model using module
      logger.write("\nDownloading model...\n")
      code = run_command(["poetry", "run", "python", "-m", "tests.download_model"], logger)
      if code != 0:
        logger.write("Failed to download model\n")
        sys.exit(1)
      logger.write("Model downloaded successfully!\n")

      # Download artifacts using module
      logger.write("\nDownloading artifacts...\n")
      code = run_command(["poetry", "run", "python", "-m", "tests.download_artifacts"], logger)
      if code != 0:
        logger.write("Failed to download artifacts\n")
        sys.exit(1)
      logger.write("Artifacts downloaded successfully!\n")

      # Get latest artifacts directory
      artifacts_dir = get_latest_artifacts_dir()
      artifacts = [f for f in artifacts_dir.iterdir() if f.name.startswith("llama-server-")]

      if not artifacts:
        logger.write("No server artifacts found to test\n")
        sys.exit(1)

      # Run tests for each artifact
      failed_artifacts = []
      for artifact in artifacts:
        logger.write(f"\nTesting artifact: {artifact.name}\n")
        code = run_tests_for_artifact(str(artifact), logger)
        if code != 0:
          failed_artifacts.append(artifact.name)
          logger.write(f"Tests failed for {artifact.name}\n")
        else:
          logger.write(f"Tests passed for {artifact.name}\n")

      # Add completion time and summary
      end_time = datetime.now()
      duration = end_time - start_time
      logger.write(f"\nScript completed at: {end_time}\n")
      logger.write(f"Total duration: {duration}\n")
      logger.write(f"\nTest results saved to {report_path}\n")

      # Print summary of failed artifacts
      if failed_artifacts:
        logger.write("\nFailed artifacts:\n")
        for artifact in failed_artifacts:
          logger.write(f"  - {artifact}\n")
        sys.exit(1)
      else:
        logger.write("\nAll artifacts tested successfully!\n")

  except KeyboardInterrupt:
    sys.stderr.write("\nScript interrupted by user\n")
    sys.exit(1)
  except Exception as e:
    sys.stderr.write(f"\nUnexpected error: {str(e)}\n")
    sys.exit(1)


if __name__ == "__main__":
  main()
