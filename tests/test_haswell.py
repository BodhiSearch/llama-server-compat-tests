import pytest
from .test_common import (
    do_test_health,
    do_test_completion,
    TEST_PROMPTS,
    build_server,
    stop_server
)

ARTIFACT_NAME = "llama-server-haswell.exe"

class TestHaswellServer:
    @classmethod
    def setup_class(cls):
        """Setup that runs once for all tests in this class"""
        cls._server = None
    
    @classmethod
    def teardown_class(cls):
        """Cleanup that runs once after all tests in this class"""
        if cls._server:
            stop_server(cls._server)
            cls._server = None

    @pytest.fixture
    def server(self, model_path, release_artifacts, server_instance):
        """Setup server if not already running"""
        if not self.__class__._server:
            # Get the specific artifact path
            artifact_path = next(
                (path for path in release_artifacts if path.endswith(ARTIFACT_NAME)), 
                None
            )
            assert artifact_path is not None, f"Artifact {ARTIFACT_NAME} not found in {release_artifacts}"
            
            # Build and start server
            self.__class__._server = build_server(artifact_path, model_path, server_instance)
            
            # Ensure server has started successfully
            assert hasattr(self.__class__._server, 'port'), "Server instance missing port attribute"
        
        return self.__class__._server

    def test_health(self, server):
        """Test health check endpoint"""
        do_test_health(server)

    @pytest.mark.parametrize("prompt_config", TEST_PROMPTS)
    def test_completion(self, server, prompt_config):
        """Test completion endpoint with different prompts"""
        do_test_completion(server, prompt_config) 