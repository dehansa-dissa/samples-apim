# Marketplace Assistant API

Answers questions about APIs indexed in the shared vector store.

# Deployment

## Prerequisites

Use Python 3.9 or later. From this directory:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r app/requirements.txt
```

### Configuring the Marketplace Assistant API

Create a `.env` file with the Azure OpenAI and vector-store settings:

```dotenv
# Azure OpenAI generates answers and embeddings for API discovery.
OPENAI_API_KEY=
AZURE_ENDPOINT=
AZURE_CHAT_DEPLOYMENT=
AZURE_CHAT_VERSION=
AZURE_EMBEDDING_DEPLOYMENT=

# Zilliz Cloud is the vector store used to search indexed APIs.
ZILLIZ_CLOUD_URI=
ZILLIZ_CLOUD_API_KEY=
COLLECTION_NAME=
```

# Build and Run

Start the service:

```bash
uvicorn app.api:api --host 0.0.0.0 --port 8000 --reload
```

## Accessing the Service

It is available at `http://localhost:8000`; `GET /health` confirms it is running. The vector store must contain records created with the same `keyID` used for chat requests. See [openapi.yaml](openapi.yaml) for the request format.

## Example Request

```bash
curl -X POST 'http://localhost:8000/marketplace-assistant?keyID=local-key' \
  -H 'Content-Type: application/json' \
  -d '{"query":"What APIs are available?","history":[],"tenant_domain":"carbon.super","user_roles":"[]"}'
```
