#!/usr/bin/env python3

import os
from pathlib import Path
from huggingface_hub import hf_hub_download


def download_model():
  """Downloads the model from HuggingFace"""
  # Define model details
  repo_id = "unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF"
  filename = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"

  # Define where to save the model
  cache_dir = str(Path(os.path.join(os.path.dirname(__file__), "..", "models")).absolute())
  os.makedirs(cache_dir, exist_ok=True)

  # Download the model if it doesn't already exist
  print(f"Downloading model {filename} from {repo_id}...")
  model_path = hf_hub_download(repo_id=repo_id, filename=filename, cache_dir=cache_dir)
  print(f"Model downloaded to {model_path}")

  return str(Path(model_path).absolute())


if __name__ == "__main__":
  download_model()
