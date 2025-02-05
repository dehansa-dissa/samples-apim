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
import redis
import os
import openai
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

deployment_name = os.getenv("AZURE_CHAT_DEPLOYMENT")
openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_version = os.getenv("AZURE_CHAT_VERSION")
openai.azure_endpoint = os.getenv("AZURE_ENDPOINT")

llm = AzureChatOpenAI(
    model=deployment_name,
    temperature=0.1,
    api_version=openai.api_version,
    azure_endpoint=openai.azure_endpoint
)

r = redis.Redis(
    host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    db=int(os.getenv("REDIS_DB")),
    ssl=True,
    ssl_ca_certs=os.getenv("REDIS_SSL_CERT")
)

required_properties = {
    "REST": [
        "name",
        "version",
        "context",
        "endpoint",
        "http methods and paths"
    ],
    "GraphQL": [
        "name",
        "version",
        "paths",
        "schema",
        "queries"
    ],
    "WebSocket": [
        "name",
        "version",
        "channel",
        "endpoint",
        "paths"
    ],
    "WebSub": [
        "name",
        "version",
        "context",
        "paths"
    ],
    "SSE": [
        "name",
        "version",
        "context",
        "endpoint",
        "paths"
    ]
}
