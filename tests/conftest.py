import pytest
import os
from huggingface_hub import hf_hub_download

@pytest.fixture(scope="session", autouse=True)
def download_model():
    """
    Downloads the model from HuggingFace once before any tests run.
    Using scope="session" ensures it runs only once for the entire test suite.
    The autouse=True parameter makes it run automatically without explicit reference.
    """
    # Define model details
    repo_id = "unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF"
    filename = "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
    
    # Define where to save the model (you might want to customize this path)
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Download the model if it doesn't already exist
    model_path = os.path.join(cache_dir, filename)
    if not os.path.exists(model_path):
        print(f"Downloading model {filename} from {repo_id}...")
        model_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir=cache_dir
        )
        print(f"Model downloaded to {model_path}")
    else:
        print(f"Model already exists at {model_path}")
    
    # Make the model path available to tests
    return model_path
