"""
Tests for API Chat endpoints.
"""

import pytest
import requests
from constants import HTTP_201_CREATED, CONTENT_TYPE_JSON
from conftest import make_request, assert_response, get_version_configs
from test_data import TestPayloads


class TestAPIChatEndpoints:
    """Test API Chat related endpoints."""
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_prepare_endpoint_success(self, config):
        """Test successful API chat preparation."""
        url = f"{config.url}/ai/api-chat/prepare"
        headers = config.get_headers({
            "Content-Type": CONTENT_TYPE_JSON,
            "apiChatRequestId": "1"
        })
        
        payload = TestPayloads.get_json_payload("API_CHAT_PREPARE")
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload
        )
        
        # Verify response contains required fields
        assert_response(response, expected_status=HTTP_201_CREATED, required_fields=["apiSpec", "queries"])
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_execute_endpoint_success(self, config):
        """Test successful API chat execution."""
        url = f"{config.url}/ai/api-chat/execute"
        headers = config.get_headers({
            "Content-Type": CONTENT_TYPE_JSON,
            "apiChatRequestId": "1"
        })
        
        payload = TestPayloads.get_json_payload("API_CHAT_EXECUTE")
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload,
        )
        
        # Verify response contains required fields
        assert_response(response, expected_status=HTTP_201_CREATED, required_fields=["taskStatus", "resource"])
