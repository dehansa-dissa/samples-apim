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
    def test_design_assistant_chat_two_step_success(self, config):
        """Test successful design assistant chat."""

        url = f"{config.url}/ai/api-design-assistant/chat"
        headers = config.get_headers({"Content-Type": CONTENT_TYPE_JSON})
        
        payload_init = TestPayloads.get_json_payload("API_DESIGN_CHAT")
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload_init,
        )
        
        # Verify response structure
        json_data_init = assert_response(response, expected_status=HTTP_201_CREATED)
        assert json_data_init is not None

        payload_cont = TestPayloads.get_json_payload("API_DESIGN_CHAT_CONT")
        
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload_cont,
        )
        
        # Verify response structure
        json_data_cont = assert_response(response, expected_status=HTTP_201_CREATED)
        assert json_data_cont is not None
