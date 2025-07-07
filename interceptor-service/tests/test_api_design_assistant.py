"""
Tests for API Design Assistant endpoints.
"""

import json
import pytest
import requests
from constants import HTTP_201_CREATED, CONTENT_TYPE_JSON, AUTH_METHOD_API_KEY
from conftest import make_request, assert_response, get_version_configs
from test_data import TestPayloads


class TestAPIDesignAssistant:
    """Test API Design Assistant endpoints."""
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_design_assistant_chat_success(self, config):
        """Test successful design assistant chat."""
        # Skip if using API key authentication (not supported for this endpoint)
        if config.auth.method == AUTH_METHOD_API_KEY:
            pytest.skip("API Design Assistant not available with API key authentication")
        
        url = f"{config.url}/ai/api-design-assistant/chat"
        headers = config.get_headers({"Content-Type": CONTENT_TYPE_JSON})
        
        payload = TestPayloads.get_json_payload("API_DESIGN_CHAT")
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload,
        )
        
        # Verify response structure
        json_data = assert_response(response, expected_status=HTTP_201_CREATED)
        assert json_data is not None
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_generate_api_payload_success(self, config):
        """Test successful API payload generation."""
        # Skip if using API key authentication (not supported for this endpoint)
        if config.auth.method == AUTH_METHOD_API_KEY:
            pytest.skip("API Design Assistant not available with API key authentication")
        
        url = f"{config.url}/ai/api-design-assistant/generate-api-payload"
        headers = config.get_headers({"Content-Type": CONTENT_TYPE_JSON})
        
        payload = TestPayloads.get_json_payload("API_DESIGN_GENERATE")
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload,
        )
        
        # Verify response structure
        json_data = assert_response(response, expected_status=HTTP_201_CREATED)
        assert json_data is not None
    