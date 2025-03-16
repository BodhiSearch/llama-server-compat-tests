import pytest
import requests
import time
import logging
import socket
from typing import Callable, List, Any
import subprocess
import random
from .conftest import ServerConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_free_port() -> int:
    """Find a free port on localhost in the non-privileged port range (>1024)"""
    while True:
        # Choose a random port between 1025 and 65535
        port = random.randint(1025, 65535)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                s.listen(1)
                return port
        except OSError:
            # Port is in use, try another one
            continue

def wait_for_server(port: int, max_retries=10, retry_delay=2):
    """Wait for server to be ready to accept connections"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to server on port {port} (attempt {attempt + 1}/{max_retries})")
            response = requests.get(f"http://127.0.0.1:{port}/health")
            if response.status_code == 200:
                logger.info("Server is ready!")
                return True
        except requests.exceptions.ConnectionError:
            logger.info(f"Server not ready yet, waiting {retry_delay} seconds...")
            time.sleep(retry_delay)
    logger.error(f"Server failed to start on port {port} after maximum retries")
    return False

def do_test_health(server: Any):
    """Common health check test"""
    logger.info("Running health check test...")
    port = server.config.port if hasattr(server, 'config') else 8080
    response = requests.get(f"http://127.0.0.1:{port}/health")
    assert response.status_code == 200, "Health check failed"
    logger.info("✓ Health check passed")

def do_test_completion(server: Any, prompt_config: dict):
    """Common completion test"""
    logger.info(f"Running completion test with prompt: {prompt_config['prompt'][:20]}...")
    port = server.config.port if hasattr(server, 'config') else 8080
    response = requests.post(f"http://127.0.0.1:{port}/completion", json=prompt_config)
    assert response.status_code == 200, f"Completion request failed for prompt: {prompt_config['prompt']}"
    result = response.json()
    assert "content" in result, "Response missing content field"
    assert len(result["content"]) > 0, "Empty response from model"
    logger.info("✓ Completion test passed")

TEST_PROMPTS = [
    {"prompt": "Hello, how are you?", "n_predict": 128},
    {"prompt": "What is 2+2?", "n_predict": 32}
]

def build_server(artifact_path: str, model_path: str, server_instance: Callable) -> subprocess.Popen:
    """Common server build and startup logic"""
    logger.info(f"Starting server with artifact: {artifact_path}")
    logger.info(f"Using model at: {model_path}")
    
    # Get a random port for this server instance
    port = find_free_port()
    logger.info(f"Selected port {port} for server")
    
    # Create server config with the random port
    config = ServerConfig(port=port)
    
    # Start server with config
    server = server_instance(artifact_path, model_path, config=config)
    assert wait_for_server(port), f"Server failed to start with artifact {artifact_path} on port {port}"
    return server

def stop_server(server: subprocess.Popen):
    """Common server cleanup logic"""
    if server:
        logger.info("Stopping server...")
        try:
            if hasattr(server, 'stop'):
                server.stop()
                logger.info("Server stopped successfully")
            elif hasattr(server, 'terminate'):
                server.terminate()
                server.wait(timeout=5)
                logger.info("Server stopped successfully")
            else:
                logger.warning("No known method to stop server")
        except subprocess.TimeoutExpired:
            logger.warning("Server did not terminate gracefully, forcing...")
            if hasattr(server, 'kill'):
                server.kill()
        except Exception as e:
            logger.error(f"Error stopping server: {e}") 