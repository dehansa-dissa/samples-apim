# Interceptor Service Tests

This directory contains comprehensive automated integration tests for the Interceptor Service. The tests are organized using best practices and provide robust coverage of all AI service endpoints.

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Setup

1. **Create and activate a virtual environment:**

   ```bash
   cd interceptor-service/tests
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run tests:**

   ```bash
   # Run all tests
   python run_tests.py

   # Run with verbose output
   python run_tests.py --verbose

   # Run specific test category using environment variable
   TEST_TYPE=apichat python run_tests.py
   ```

## 📁 Project Structure

```
tests/
├── conftest.py                      # Pytest configuration and hooks
├── constants.py                     # Test constants and configuration
├── test_data.py                     # Test payloads and data
├── run_tests.py                     # Enhanced test runner script
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment configuration template
├── 
├── # Individual test modules
├── test_api_chat.py                 # API Chat endpoint tests
├── test_marketplace_assistant.py    # Marketplace Assistant tests
├── test_spec_populator.py          # Spec Populator tests
├── test_api_design_assistant.py    # API Design Assistant tests
```

## 🔧 Configuration

### Environment Variables

Configure the following in your `.env` file:

```bash
# API Endpoints (add as many versions as needed)
ENDPOINT_V1=https://your-v1-endpoint.com
ENDPOINT_V2=https://your-v2-endpoint.com

# Authentication tokens
TOKEN_V1=your_api_key_v1
TOKEN_V2=your_basic_auth_token_v2
TOKEN_ENDPOINT_V2=https://your-token-endpoint.com

# Test type selection
TEST_TYPE=all  # Options: all, apichat, marketplaceassistant, specpopulator, apidesignassistant, apimockgenerator, sdkgeneration
```

## 🧪 Test Categories

| Category | Description | Test File |
|----------|-------------|-----------|
| `apichat` | API Chat endpoints | `test_api_chat.py` |
| `marketplaceassistant` | Marketplace Assistant | `test_marketplace_assistant.py` |
| `specpopulator` | Spec Populator services | `test_spec_populator.py` |
| `apidesignassistant` | API Design Assistant | `test_api_design_assistant.py` |

## 📊 Running Tests

### Basic Usage

```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py --verbose

# Run specific category using environment variable
TEST_TYPE=apichat python run_tests.py
TEST_TYPE=specpopulator python run_tests.py --verbose
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run specific test file
pytest test_api_chat.py

# Run specific test method
pytest test_api_chat.py::TestAPIChatEndpoints::test_prepare_endpoint_success
```

## 🚀 Adding New Tests

To add tests for a new service:

1. **Create a new test file**: `test_new_service.py`
2. **Add test data**: Update `test_data.py` with new payloads
3. **Update test runner**: Add the new category to `TEST_MODULES` in `run_tests.py`
4. **Follow the pattern**: Use existing test files as templates

Example structure:
```python
"""
Tests for New Service endpoints.
"""

import pytest
from constants import HTTP_201_CREATED, CONTENT_TYPE_JSON
from conftest import make_request, assert_response, get_version_configs
from test_data import TestPayloads

class TestNewService:
    """Test New Service endpoints."""
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_new_endpoint_success(self, config):
        """Test successful new endpoint."""
        # Test implementation
        pass
```

### Debugging

```bash
# Run with verbosity
python run_tests.py --verbose

# Run a single test for debugging
pytest test_api_chat.py::TestAPIChatEndpoints::test_prepare_endpoint_success -v -s
```
