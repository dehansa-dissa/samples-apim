# APIM API Design Assistant

AI-based tool for designing APIs through natural language commands.

# Deployment
Follow these steps to set up the API Design Assistant service locally.

## Prerequisites

### 1. Obtain An Access Token
- Use Postman to generate a valid access token by following the [authentication guide](https://apim.docs.wso2.com/en/latest/reference/product-apis/publisher-apis/publisher-v4/publisher-v4/#section/Authentication) for invoking APIs.

### 2. Configuring the API Design Assistant Service
1. Clone this repo.
```bash
git clone https://github.com/wso2-enterprise/apim-ai-deployments.git
```
2. Create the `.env` with the following configurations.
```plaintext
OPENAI_API_KEY= # OpenAI API Key
AZURE_CHAT_DEPLOYMENT= # Azure chat model name
AZURE_CHAT_VERSION= # Azure API version
AZURE_ENDPOINT= # Azure API URL
REDIS_HOST= # Redis Host
REDIS_PASSWORD= # Redis Password
REDIS_PORT= # Redis Port
REDIS_DB= # Redis Database Number
REDIS_SSL_CERT= # path/to/the/sslCertificate.pem
```

# Run

Follow the instructions below to run the API design assistant service and access the service.

## Prerequisites

- Ensure you have **Python 3.12.4** installed on your system.
- Install the required dependencies listed in the `requirements.txt` file using the following command:

```bash
pip install -r requirements.txt
```
## Running the Project
To run the service, run the `main.py` file located in the `api-design-assistant` directory. You can also execute the following command from the root folder to achieve this:
```
python api-design-assistant/main.py
```

## Accessing the Service
Once the service is running, it will be accessible at the following URL:

```arduino
http://127.0.0.1:8000/{PATH}
```
Replace {PATH} with the appropriate endpoint path (`/chat` or `/generate-api-payload`) for the specific API functionality you want to access.

## Example Request
Test the service using tools such as curl or Postman. Here's an example curl command for the `/chat` endpoint:

```bash
curl -X POST http://127.0.0.1:8000/chat \
-H "Content-Type: application/json" \
-d '{
  "text": "create an API for a banking transaction.",
  "session_id": "1234567890"
}'
```

Here's an example curl command for the `/generate-api-payload` endpoint:

```bash
curl -X POST http://127.0.0.1:8000/generate-api-payload \
-H "Content-Type: application/json" \
-d '{
  "session_id": "1234567890"
}'
```
