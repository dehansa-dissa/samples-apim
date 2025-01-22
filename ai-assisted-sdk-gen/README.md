# AI-Assisted SDK Generation for Developer Portal APIs

API service that merges multiple OpenAPI specifications into a single specification.

This service is specifically designed to facilitate SDK generation that supports multiple APIs.

## Prerequisites

- Ensure you have **Python 3.x** installed on your system.
- Install the required dependencies listed in the `requirements.txt` file using the following command:

```bash
pip install -r requirements.txt
```

## Setup Instructions

Follow these steps to set up and run the project:

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ai-assisted-sdk-gen
```

### 2. Configure the `.env` File
- Navigate to the `ai-assisted-sdk-gen` terminal.
- Create a `.env` file in the root directory with the following configurations:

  ```env
  OPENAI_API_KEY= # Your OpenAI API Key
  DEPLOYMENT_NAME= # Model Name
  API_TYPE = # API Type
  API_VERSION= # API Version
  AZURE_ENDPOINT= # API URL
  ```

> **Note**: Replace the placeholders with your actual API credentials.

### 3. Run the Application
- Start the Flask server by running the following command:
  ```bash
  python app.py
  ```
- The server will start on `http://localhost:5000` by default.

- You can interact with the API using either of these methods:

   1. Upload OpenAPI specification files (JSON or YAML):
   ```bash
   curl -X POST -F "files=@spec1.json" -F "files=@spec2.json" http://localhost:5000/merge-openapi-specs
   ```

   2. Send OpenAPI specifications as JSON string in the request body:
   ```bash
   curl -X POST -H "Content-Type: application/json" --data-binary @specs.json http://localhost:5000/merge-openapi-specs
---