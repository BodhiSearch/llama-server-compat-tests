import pytest


@pytest.mark.parametrize("artifact_name", ["llama-server-generic.exe", "llama-server-haswell.exe"])
def test_windows(model_path, release_artifacts, artifact_name):
  assert model_path is not None
  print(f"Using model at: {model_path}")
  assert release_artifacts is not None

  # Get the specific artifact path
  artifact_path = next((path for path in release_artifacts if path.endswith(artifact_name)), None)
  assert artifact_path is not None, f"Artifact {artifact_name} not found in {release_artifacts}"
  print(f"Testing artifact: {artifact_path}")

  # Your actual model testing logic here
  assert True
