# LLaMA Server Compatibility Tests

A comprehensive test suite for validating llama.cpp server implementations across different platforms and architectures.

## Overview

This project provides automated compatibility testing for llama.cpp server implementations. It verifies that different server builds work correctly across various platforms (macOS, Linux, Windows) and architectures (x86_64, ARM64).

## Features

- Automated server compatibility testing
- Cross-platform support (macOS, Linux, Windows)
- Multiple architecture support (x86_64, ARM64)
- Automated model downloading
- Comprehensive test reporting
- Server health checks
- Chat completion validation

## Prerequisites

- Python 3.10 or higher
- Poetry (will be automatically installed if not present)
- Internet connection for downloading models and artifacts

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/BodhiSearch/llama-server-compat-tests.git
   cd llama-server-compat-tests
   ```

2. Run the test suite:
   ```bash
   python run_tests.py
   ```

The script will automatically:
- Install Poetry if not present
- Install project dependencies
- Download required models
- Download server artifacts
- Run the test suite
- Generate test reports

## Project Structure

```
llama-server-compat-tests/
├── artifacts/          # Server executables for different platforms
├── models/            # LLaMA model files
├── reports/           # Test execution reports
├── tests/            
│   ├── test_server.py # Main server test suite
│   ├── system_info.py # System information collector
│   └── resources.py   # Test resources and utilities
├── run_tests.py       # Main test runner script
├── pyproject.toml     # Project dependencies and configuration
└── README.md         # This file
```

## Test Suite Details

### Server Tests (`test_server.py`)
- **Health Check**: Verifies server is running and responding (10s timeout)
- **Chat Completion**: Tests basic chat functionality (60s timeout)
- Tests are parameterized to run against all available server executables
- Platform-specific test filtering (only runs tests for current platform)

### Test Runner (`run_tests.py`)
- Manages the complete test execution lifecycle
- Handles dependency installation
- Downloads required models and artifacts
- Captures and logs all output
- Generates timestamped test reports

## Configuration

The project uses Poetry for dependency management. Key dependencies:
- pytest: Test framework
- requests: HTTP client for server communication
- psutil: Process and system utilities
- huggingface-hub: Model downloading
- pytest-timeout: Test execution timeouts

## Test Reports

Test reports are generated in the `reports/` directory with timestamps:
- Format: `pytest_YYMMDDHHMMSS.txt`
- Contains:
  - Full test execution output
  - System information
  - Test results and durations
  - Error details (if any)

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add your license information here]

## Support

[Add support information here]

