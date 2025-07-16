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
