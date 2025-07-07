"""
Tests for Marketplace Assistant endpoints.
"""

import json
import pytest
import requests
from constants import HTTP_201_CREATED, CONTENT_TYPE_JSON
from conftest import make_request, assert_response, get_version_configs
from test_data import TestPayloads


class TestMarketplaceAssistant:
    """Test Marketplace Assistant endpoints."""
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_marketplace_chat_success(self, config):
        """Test successful marketplace chat."""
        url = f"{config.url}/ai/marketplace-assistant/chat"
        headers = config.get_headers({"Content-Type": CONTENT_TYPE_JSON})
        
        payload = TestPayloads.get_json_payload("MARKETPLACE_CHAT")
        
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
    