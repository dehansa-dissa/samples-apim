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
Tests for API Chat endpoints.
"""

import pytest
import requests
from constants import HTTP_201_CREATED, CONTENT_TYPE_JSON
from conftest import make_request, assert_response, get_version_configs
from test_data import TestPayloads
import json
import time

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
        json_data = assert_response(response, expected_status=HTTP_201_CREATED, required_fields=["apiSpec", "queries"])
        assert json_data is not None
    
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
        json_data = assert_response(response, expected_status=HTTP_201_CREATED, required_fields=["taskStatus", "resource"])
        assert json_data is not None

    @pytest.mark.parametrize("config", get_version_configs())
    def test_apichat_flow_success(self, config):
        """Test successful API chat execution."""
        prepare_url = f"{config.url}/ai/api-chat/prepare"
        execute_url = f"{config.url}/ai/api-chat/execute"

        headers = config.get_headers({
            "Content-Type": CONTENT_TYPE_JSON,
            "apiChatRequestId": "1"
        })
        
        prepare_payload = TestPayloads.get_json_payload("API_CHAT_PREPARE")
        
        client = requests.Session()
        prepare_response = make_request(
            client=client,
            method="POST",
            url=prepare_url,
            headers=headers,
            data=prepare_payload,
        )

        json_data = assert_response(prepare_response, expected_status=HTTP_201_CREATED, required_fields=["apiSpec", "queries"])
        assert json_data is not None

        prepare_respnse_body = json.loads(prepare_response.text)

        execute_payload = {
            "apiSpec": prepare_respnse_body["apiSpec"],
            "command": prepare_respnse_body["queries"][1]["query"]
        }

        initiate_execute_response = make_request(
            client=client,
            method="POST",
            url=execute_url,
            headers=headers,
            data=json.dumps(execute_payload),
        )

        json_data = assert_response(initiate_execute_response, expected_status=HTTP_201_CREATED, required_fields=["taskStatus", "resource"])
        assert json_data is not None

        initiate_execute_response_body = json.loads(initiate_execute_response.text)

        get_results_execute_pyload = {
                "response":  {
                    "code": initiate_execute_response.status_code,
                    "path": initiate_execute_response_body["resource"]["path"],
                    "headers": {"contentType": initiate_execute_response.headers.get("Content-Type", CONTENT_TYPE_JSON), "contentLength": int(initiate_execute_response.headers.get("Content-Length", "0"))},
                    "body": initiate_execute_response_body
                }
            }
        
        get_results_execute_response = make_request(
            client=client,
            method="POST",
            url=execute_url,
            headers=headers,
            data=json.dumps(get_results_execute_pyload),
        )

        # Verify response contains required fields
        json_data = assert_response(get_results_execute_response, expected_status=HTTP_201_CREATED)
        assert json_data is not None

    @pytest.mark.parametrize("config", get_version_configs())
    def test_api_chat_two_steps_success(self, config):
        """Test API chat with two steps."""
        url = f"{config.url}/ai/api-chat/execute"
        headers = config.get_headers({
            "Content-Type": CONTENT_TYPE_JSON,
            "apiChatRequestId": "1"
        })
        
        payload_init = TestPayloads.get_json_payload("API_CHAT_EXECUTE")
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload_init,
        )
        
        # Verify response contains required fields
        json_data_init = assert_response(response, expected_status=HTTP_201_CREATED, required_fields=["taskStatus", "resource"])
        assert json_data_init is not None

        payload_cont = TestPayloads.get_json_payload("API_CHAT_EXECUTE_CONT")
        
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload_cont,
        )
        
        # Verify response contains required fields
        json_data_cont = assert_response(response, expected_status=HTTP_201_CREATED, required_fields=["taskStatus", "resource"])
        assert json_data_cont is not None
