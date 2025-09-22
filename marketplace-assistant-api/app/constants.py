import os
from dotenv import load_dotenv

load_dotenv()

CHOREO = "choreo"
APIM = "apim"

# streaming stage constants
START_STREAM = "START_STREAM"
FIND_LLM_RESPONSE = "FIND_LLM_RESPONSE"
SEND_LLM_RESPONSE = "SEND_LLM_RESPONSE"
END_LLM_RESPONSE = "END_LLM_RESPONSE"
FIND_API = "FIND_API"
SEND_API = "SEND_API"
BUFFER_API = "BUFFER_API"
FINISH_STREAM = "FINISH_STREAM"

# environment variables
# vector db related env variables
ZILLIZ_CLOUD_URI = os.getenv('ZILLIZ_CLOUD_URI', "")
ZILLIZ_CLOUD_API_KEY = os.getenv('ZILLIZ_CLOUD_API_KEY', "")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

# openai embedding related env variables
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')
AZURE_EMBEDDING_DEPLOYMENT = os.getenv('AZURE_EMBEDDING_DEPLOYMENT', "OpenAPIEmbeddings")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
SOURCE_PLATFORM = os.getenv('SOURCE_PLATFORM')

# openai proxy related env variables
PROXY_URL = os.getenv("PROXY_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET") 
TOKEN_ENDPOINT_URL = os.getenv("TOKEN_ENDPOINT_URL")
MODEL_NAME = "gpt-5-mini"

OUTPUT_FIELDS = ['id', 'metadata', 'api_type', 'api_name', 'page_content', 'org_id']
