"""
 Copyright (c) 2024, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.

  This software is the property of WSO2 LLC. and its suppliers, if any.
  Dissemination of any information or reproduction of any material contained
  herein is strictly forbidden, unless permitted by WSO2 in accordance with
  the WSO2 Commercial License available at http://wso2.com/licenses.
  For specific language governing the permissions and limitations under
  this license, please see the license as well as any agreement you’ve
  entered into with WSO2 governing the purchase of this software and any
"""
import redis.asyncio as redis
import os
from dotenv import load_dotenv
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from azure.core.credentials import AzureKeyCredential
from functools import lru_cache
import requests
import time

load_dotenv()

# openai proxy related env variables
USE_PROXY = os.getenv("USE_PROXY", "false").lower() == "true"
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_PROXY_ENDPOINT = os.getenv("AZURE_PROXY_ENDPOINT")
AZURE_CHAT_VERSION = os.getenv("AZURE_CHAT_VERSION", "2025-01-01-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_CHAT_DEPLOYMENT = os.getenv("AZURE_CHAT_DEPLOYMENT")

@lru_cache(maxsize=2)
def validate_endpoint(endpoint: str) -> tuple:
    try:
        response = requests.options(endpoint, timeout=2)
        is_valid = response.status_code < 300
        return (is_valid, time.time())
    except:
        return (False, time.time())

def validate_endpoint_cached(endpoint: str) -> bool:
    is_valid, timestamp = validate_endpoint(endpoint)
    
    if time.time() - timestamp > 900:
        validate_endpoint.cache_clear()
        is_valid, _ = validate_endpoint(endpoint)
    
    return is_valid

def get_llm(auth_token: str = None):
    """
    Get LLM client with automatic fallback from proxy to direct connection.
    If proxy is enabled but fails, it will automatically fallback to direct connection.
    """
    if USE_PROXY:
        if validate_endpoint_cached(AZURE_PROXY_ENDPOINT + "/chat/completions?api-version=2025-01-01-preview"):
            return AzureAIChatCompletionsModel(
                endpoint=AZURE_PROXY_ENDPOINT,
                credential=AzureKeyCredential(auth_token),
                model=AZURE_CHAT_DEPLOYMENT,
                api_version=AZURE_CHAT_VERSION,
            )
        else:
            print(f"Warning: Proxy endpoint {AZURE_PROXY_ENDPOINT} is not reachable, falling back to direct connection.")

    return AzureAIChatCompletionsModel(
        endpoint=AZURE_ENDPOINT + "/" + AZURE_CHAT_DEPLOYMENT,
        credential=AzureKeyCredential(OPENAI_API_KEY),
        model=AZURE_CHAT_DEPLOYMENT,
        api_version=AZURE_CHAT_VERSION,
    )

r = redis.Redis(
    host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    db=int(os.getenv("REDIS_DB")),
    ssl=True
)
