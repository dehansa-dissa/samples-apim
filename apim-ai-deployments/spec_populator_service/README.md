# Spec Populator Service

Indexes API definitions in the vector store used by Marketplace Assistant.

# Deployment

## Prerequisites

Use Python 3.9 or later. From this directory:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuring the Spec Populator Service

Create a `.env` file with the Azure OpenAI embedding and Milvus settings:

```dotenv
# Azure OpenAI creates embeddings from API definitions.
AZURE_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_DEPLOYMENT=

# Milvus stores the API vectors used by Marketplace Assistant.
MILVERSE_URL=
MILVERSE_API_KEY=
COLLECTION_NAME=
CREATE_COLLECTION=true
```

# Build and Run

Start the service:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Accessing the Service

It is available at `http://localhost:8000`; check it with:

```bash
curl http://localhost:8000/health
```

Use the same Milvus collection, embedding deployment, and `keyID` as Marketplace Assistant. The API operations and request schemas are in [openapi.yaml](openapi.yaml).
