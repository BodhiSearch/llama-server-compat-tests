import pytest
import os
from .download_model import download_model
from .download_artifacts import download_release_artifacts


def pytest_configure(config):
  """
  This hook is called before test collection begins.
  We use it to ensure artifacts and model are downloaded before any tests are collected.
  """
  # Only download artifacts if no specific artifact path is provided
  if not config.getoption("--artifact-path"):
    download_release_artifacts()
  download_model()


@pytest.fixture(scope="session")
def release_artifacts(request):
  """
  Returns paths to the downloaded artifacts.
  If a specific artifact path is provided, returns just that path.
  Otherwise returns all downloaded artifacts.
  """
  artifact_path = request.config.getoption("--artifact-path")
  if artifact_path:
    if not os.path.exists(artifact_path):
      raise FileNotFoundError(f"Specified artifact not found: {artifact_path}")
    return [artifact_path]

  # If no specific artifact, get all downloaded artifacts
  release_dir = download_release_artifacts()
  paths = [str(path) for path in release_dir.iterdir() if path.name.startswith("llama-server-")]

  if not paths:
    raise FileNotFoundError(
      "No artifacts found. This should not happen as pytest_configure should have downloaded artifacts."
    )
  return paths


@pytest.fixture(scope="session", autouse=True)
def model_path():
  """
  Returns path to the downloaded model.
  The actual download is handled by pytest_configure.
  """
  path = download_model()
  if not os.path.exists(path):
    raise FileNotFoundError(
      "Model not found. This should not happen as pytest_configure should have downloaded the model."
    )
  return path


def pytest_addoption(parser):
  """Add artifact-path command line option"""
  parser.addoption(
    "--artifact-path",
    action="store",
    default=None,
    help="Path to specific artifact to test",
  )
