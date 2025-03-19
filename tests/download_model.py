#!/usr/bin/env python3

import os
from pathlib import Path
from huggingface_hub import hf_hub_download, try_to_load_from_cache
from huggingface_hub.utils import HfHubHTTPError


def download_model():
  """Downloads the model from HuggingFace or uses cached version if available"""
  # Define model details
  repo_id = "unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF"
  filename = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"

  # Define where to save the model
  cache_dir = str(Path(os.path.join(os.path.dirname(__file__), "..", "models")).absolute())
  os.makedirs(cache_dir, exist_ok=True)

  # First try to load from cache
  cached_path = try_to_load_from_cache(repo_id=repo_id, filename=filename, cache_dir=cache_dir)
  if cached_path:
    print(f"Found cached model at {cached_path}")
    return str(Path(cached_path).absolute())

  # If not in cache, try to download
  try:
    print(f"Downloading model {filename} from {repo_id}...")
    model_path = hf_hub_download(repo_id=repo_id, filename=filename, cache_dir=cache_dir)
    print(f"Model downloaded to {model_path}")
    return str(Path(model_path).absolute())
  except Exception as e:
    raise RuntimeError(
      f"Failed to download model and no cached version found: {str(e)}. "
      "Please ensure you have internet connectivity or a cached model file."
    ) from e


if __name__ == "__main__":
  download_model()
