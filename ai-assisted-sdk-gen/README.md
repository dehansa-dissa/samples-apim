# AI-Assisted SDK Generation for Developer Portal APIs

API service that helps merge multiple OpenAPI specifications into single specification and generate application code in the preferred programming language (Java/JavaScript) based on the use case, API specification and SDK methods.

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
  ANTHROPIC_API_KEY = # Your Anthropic API Key
  ANTHROPIC_MODEL_NAME = # Model Name
  ```

  > **Note**: Replace the placeholders with your actual API credentials.

### 3. Run the Application
- To run the service, execute the following command:
  ```bash
  python app.py
  ```

- Once the service is running, it will be accessible at the following URL:
  ```arduino
  http://localhost:5000/{PATH}
  ```
- Replace {PATH} with the appropriate endpoint path (`merge-openapi-specs` or `/generate-application-code`) for the specific API functionality you want to access.

## API Endpoints

### 1. **POST `/merge-openapi-specs`**

Merges multiple OpenAPI specifications into a single specification.

#### Request Body:

  ```json
  {
    "specifications": "/* JSON string containing OpenAPI specs seperated by newline characters */",
    "contexts": {
      "spec1": "/apicontext1/version",
      "spec2": "/apicontext2/version"
    }
  }
  ```
---

### 2. **POST `/generate-application-code`**

Generates sample application code in the preferred language (Java/JavaScript) based on the use case, methods available in the SDK and API specification
#### Request Body:

```json
{
  "useCase": "Description of the use case",
  "sdkMethodsFile": "content of the SDK Methods File",
  "APISpecification": "{ ... }",
  "language": "java"
}
``` 