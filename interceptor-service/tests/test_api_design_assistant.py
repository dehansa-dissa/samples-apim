# -------------------------------------------------------------------------------------
#
# Copyright (c) 2025, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.
#
# This software is the property of WSO2 LLC. and its suppliers, if any.
# Dissemination of any information or reproduction of any material contained
# herein in any form is strictly forbidden, unless permitted by WSO2 expressly.
# You may not alter or remove any copyright or other notice from copies of this content.
#
# --------------------------------------------------------------------------------------

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
    
    @pytest.mark.parametrize("config", get_version_configs(ignored_versions=[1]))
    def test_design_assistant_chat_success(self, config):
        """Test successful design assistant chat."""

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
    
    @pytest.mark.parametrize("config", get_version_configs(ignored_versions=[1]))
    def test_generate_api_payload_success(self, config):
        """Test successful API payload generation."""

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

    @pytest.mark.parametrize("config", get_version_configs(ignored_versions=[1]))
    def test_design_assistant_flow_success(self, config):
        """Test successful API payload generation."""
        # Skip if using API key authentication (not supported for this endpoint)
        
        chat_url = f"{config.url}/ai/api-design-assistant/chat"
        headers = config.get_headers({"Content-Type": CONTENT_TYPE_JSON})
        
        chat_payload = TestPayloads.get_json_payload("API_DESIGN_CHAT")
        
        client = requests.Session()
        chat_response = make_request(
            client=client,
            method="POST",
            url=chat_url,
            headers=headers,
            data=chat_payload,
        )

        generate_url = f"{config.url}/ai/api-design-assistant/generate-api-payload"
        
        generate_payload = {"sessionId": json.loads(chat_payload)["sessionId"]}
        
        generate_response = make_request(
            client=client,
            method="POST",
            url=generate_url,
            headers=headers,
            data=json.dumps(generate_payload),
        )
        
        # Verify response structure
        json_data = assert_response(generate_response, expected_status=HTTP_201_CREATED)
        assert json_data is not None
