"""
Test data and payloads for interceptor service tests.
"""

import json
import os


def load_file_content(filename: str) -> str:
    """Load content from a file in the tests directory."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, filename)
    
    with open(file_path, 'r') as f:
        return f.read()


class TestPayloads:
    """Container for test payloads."""
    
    API_CHAT_PREPARE = {
        "openapi": json.loads(load_file_content("pizzashack_openapi.json"))
    }

    API_CHAT_EXECUTE = {
        "apiSpec": {
            "serviceUrl": "https://localhost:9443/am/sample/pizzashack/v1/api",
            "tools": [
                {
                    "name": "GET-menu",
                    "description": "Retrieve a list of available menu items",
                    "method": "GET",
                    "path": "/menu"
                }
            ]
        },
        "command": "Get the menu items"
    }
    
    # Marketplace Assistant payloads
    MARKETPLACE_CHAT = {
        "query": "Hi give me pizza api",
        "tenant_domain": "carbon.super",
        "apim_version": "4.5.0",
        "history": "[{\"role\":\"assistant\",\"content\":\"Hello! How can I help you?\"}]",
        "user_roles": "[\"system/wso2.anonymous.role\"]"
    }
    
    # Spec Populator payloads
    SPEC_POPULATOR_UPLOAD = {
        "api_type": "HTTP",
        "api_name": "PizzaShackAPI",
        "visibility_roles": "",
        "tenant_domain": "carbon.super",
        "api_spec": json.dumps(API_CHAT_PREPARE["openapi"]),
        "description": "Pizza delivery API",
        "apim_version": "4.5.0",
        "uuid": "5acfba2e-7501-481c-a9cd-3d0951f7d3f3",
        "version": "1.0.0"
    }
    
    # API Design Assistant payloads
    API_DESIGN_CHAT = {
        "text": "Create an API for live sports scores",
        "sessionId": "test-session-id"
    }
    
    API_DESIGN_GENERATE = {
        "sessionId": "test-session-id"
    }
    
    # Mock Generator payloads
    MOCK_GENERATE = {
        "swagger": {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    @classmethod
    def get_json_payload(cls, payload_name: str) -> str:
        """Get a payload as JSON string."""
        payload = getattr(cls, payload_name)
        return json.dumps(payload)
