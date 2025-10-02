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

load_dotenv()

# openai proxy related env variables
USE_PROXY = os.getenv("USE_PROXY", "false").lower() == "true"
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_CHAT_VERSION = os.getenv("AZURE_CHAT_VERSION", "2025-01-01-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_CHAT_DEPLOYMENT = os.getenv("AZURE_CHAT_DEPLOYMENT")

def get_api_key(auth_token: str = None):
    if USE_PROXY:
        return auth_token
    else:
        return OPENAI_API_KEY

def get_llm(auth_token: str = None):
    api_key = get_api_key(auth_token)

    return AzureAIChatCompletionsModel(
            endpoint=AZURE_ENDPOINT,
            credential=AzureKeyCredential(api_key),
            model_name=AZURE_CHAT_DEPLOYMENT,
            api_version=AZURE_CHAT_VERSION,
        )

r = redis.Redis(
    host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    db=int(os.getenv("REDIS_DB")),
    ssl=True
)
