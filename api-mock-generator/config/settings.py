import os
import openai
from dotenv import load_dotenv
#from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI

load_dotenv()

# Azure OpenAI configuration
deployment_name = os.getenv("AZURE_CHAT_DEPLOYMENT")
openai.api_type = "azure"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_version = os.getenv("AZURE_CHAT_VERSION")
openai.azure_endpoint = os.getenv("AZURE_ENDPOINT")

# # LangChain setup
# llm = AzureChatOpenAI(
#     model=deployment_name,
#     temperature=0.1,
#     api_version=openai.api_version,
#     azure_endpoint=openai.azure_endpoint
# )

client = AzureOpenAI(
  azure_endpoint = openai.azure_endpoint, 
  api_key=openai.api_key,  
  api_version=openai.api_version
)

class Config:
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
