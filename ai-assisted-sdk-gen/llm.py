"""
 Copyright (c) 2025, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.

  This software is the property of WSO2 LLC. and its suppliers, if any.
  Dissemination of any information or reproduction of any material contained
  herein is strictly forbidden, unless permitted by WSO2 in accordance with
  the WSO2 Commercial License available at http://wso2.com/licenses.
  For specific language governing the permissions and limitations under
  this license, please see the license as well as any agreement you’ve
  entered into with WSO2 governing the purchase of this software and any
"""
from langchain_openai import AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from config import DEPLOYMENT_NAME, API_VERSION, AZURE_ENDPOINT, ANTHROPIC_API_KEY, MODEL_NAME

def create_llm():
    return AzureChatOpenAI(
        model=DEPLOYMENT_NAME,
        api_version=API_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
        temperature=0
    )

def initialize_chat_model():
    return ChatAnthropic(
        model=MODEL_NAME,
        anthropic_api_key=ANTHROPIC_API_KEY,
        max_tokens_to_sample=8192,
        model_kwargs={
            "system": "Respond only with the final output in a COMPLETE manner. Do not include any conversational text or comments."
        }
    )

chat = initialize_chat_model()