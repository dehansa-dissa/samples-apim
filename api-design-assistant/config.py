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
import datetime
from datetime import datetime, timedelta
import base64
import requests

load_dotenv()

# openai proxy related env variables
USE_PROXY = os.getenv("USE_PROXY", "false").lower() == "true"
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET") 
TOKEN_ENDPOINT_URL = os.getenv("TOKEN_ENDPOINT_URL")
AZURE_CHAT_VERSION = os.getenv("AZURE_CHAT_VERSION", "2025-01-01-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_CHAT_DEPLOYMENT = os.getenv("AZURE_CHAT_DEPLOYMENT")

# Token cache to store access token and expiry time
_token_cache = {
    "access_token": None,
    "expires_at": None
}

def generate_access_token():
    """
    Generate access token using OAuth2 client credentials grant type
    
    This function implements the OAuth2 client credentials flow to generate
    access tokens instead of using direct API keys. It includes:
    - Basic authentication with client_id and client_secret
    - Token caching to avoid unnecessary API calls
    - Graceful fallback to direct API key if OAuth2 fails
    - 60-second safety margin before token expiry
    
    Returns:
        str: Access token or fallback API key
    """
    global _token_cache
    
    # Check if we have a valid cached token
    if (_token_cache["access_token"] and 
        _token_cache["expires_at"] and 
        datetime.now() < _token_cache["expires_at"]):
        return _token_cache["access_token"]

    try:
        # Create Basic Auth header
        credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = "grant_type=client_credentials"

        response = requests.post(TOKEN_ENDPOINT_URL, headers=headers, data=payload)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
        
        # Cache the token with expiry time (subtract 60 seconds for safety margin)
        _token_cache["access_token"] = access_token
        _token_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 60)
        
        print(f"Successfully generated new access token, expires in {expires_in} seconds")
        return access_token
        
    except Exception as e:
        print(f"Failed to generate access token: {str(e)}")
        print("Falling back to direct API key")
        return


def get_api_key():
    """
    Get API key - either from OAuth2 token generation or fallback to direct key
    """
    if USE_PROXY:
        return generate_access_token()
    else:
        return OPENAI_API_KEY

llm = AzureAIChatCompletionsModel(
        endpoint=AZURE_ENDPOINT,
        credential=AzureKeyCredential(get_api_key()),
        model_name=AZURE_CHAT_DEPLOYMENT,
        api_version=AZURE_CHAT_VERSION,
    )

r = redis.Redis(
    host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    db=int(os.getenv("REDIS_DB")),
    ssl=True
)
