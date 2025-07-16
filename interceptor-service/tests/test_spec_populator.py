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
Tests for Spec Populator endpoints.
"""

import json
import pytest
import requests
from constants import HTTP_200_OK, HTTP_201_CREATED, CONTENT_TYPE_JSON, TEST_TENANT_DOMAIN
from conftest import make_request, assert_response, get_version_configs
from test_data import TestPayloads


class TestSpecPopulatorEndpoints:
    """Test Spec Populator endpoints."""
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_publish_api_success(self, config):
        """Test successful API publishing."""
        url = f"{config.url}/ai/spec-populator/publish-api"
        headers = config.get_headers({"Content-Type": CONTENT_TYPE_JSON})
        
        payload = TestPayloads.get_json_payload("SPEC_POPULATOR_UPLOAD")
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload,
        )
        
        # Verify successful response
        json_data = assert_response(response, expected_status=HTTP_201_CREATED)
        assert json_data is not None
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_remove_api_success(self, config):
        """Test successful API removal."""
        test_uuid = TestPayloads.SPEC_POPULATOR_UPLOAD["uuid"]
        url = f"{config.url}/ai/spec-populator/remove-api/{test_uuid}"
        headers = config.get_headers()
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="DELETE",
            url=url,
            headers=headers,
        )
        
        # Verify successful response
        json_data = assert_response(response, expected_status=HTTP_200_OK)
        assert json_data is not None
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_api_count_success(self, config):
        """Test successful API count retrieval."""
        url = f"{config.url}/ai/spec-populator/api-count"
        headers = config.get_headers()
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="GET",
            url=url,
            headers=headers,
        )
        
        # Verify response contains required fields
        assert_response(response, expected_status=HTTP_200_OK, required_fields=["count", "limit"])
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_bulk_upload_success(self, config):
        """Test successful bulk API upload."""
        url = f"{config.url}/ai/spec-populator/bulk-upload"
        headers = config.get_headers({"Content-Type": CONTENT_TYPE_JSON})
        
        # Create bulk upload payload
        bulk_payload = {
            "apis": [
                TestPayloads.SPEC_POPULATOR_UPLOAD,
                TestPayloads.SPEC_POPULATOR_UPLOAD
            ]
        }
        
        payload_data = json.dumps(bulk_payload)
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            data=payload_data,
        )
        
        # Verify successful response
        json_data = assert_response(response, expected_status=HTTP_200_OK)
        assert json_data is not None
    
    @pytest.mark.parametrize("config", get_version_configs())
    def test_bulk_remove_success(self, config):
        """Test successful bulk API removal."""
        url = f"{config.url}/ai/spec-populator/bulk-remove"
        headers = config.get_headers({
            "Content-Type": CONTENT_TYPE_JSON,
            "tenant-domain": TEST_TENANT_DOMAIN
        })
        
        client = requests.Session()
        response = make_request(
            client=client,
            method="DELETE",
            url=url,
            headers=headers,
        )
        
        # Verify successful response
        json_data = assert_response(response, expected_status=HTTP_200_OK)
        assert json_data is not None
