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
git clone <repository-url>
cd api-design-assistant
```
2. Create the `.env` with the following configurations.
```plaintext
OPENAI_API_KEY= # OpenAI API Key
AZURE_CHAT_DEPLOYMENT= # Azure chat model name
AZURE_CHAT_VERSION= # Azure API version
AZURE_ENDPOINT= # Azure API URL
YOUR_API_TOKEN= # Access token (Retrieved following the previous steps)
```

# Run

Follow the instructions below to run the API design assistant service and access the service.

## Prerequisites

- Ensure you have **Python 3.x** installed on your system.
- Install the required dependencies listed in the `requirements.txt` file using the following command:

```bash
pip install -r requirements.txt
```
## Running the Project
To run the service, run the `methods.py` file located in the `api-design-assistant` directory. You can do this with the following command:

```
python methods.py
```

## Accessing the Service
Once the service is running, it will be accessible at the following URL:

```arduino
http://127.0.0.1:5000/{PATH}
```
Replace {PATH} with the appropriate endpoint path (`/generate` or `/createapiinportal`) for the specific API functionality you want to access.

## Example Request
Test the service using tools such as curl or Postman. Here's an example curl command for the `/generate` endpoint:

```bash
curl -X POST http://127.0.0.1:5000/generate \
-H "Content-Type: application/json" \
-d '{
  "user_input": "create an API for a banking transaction.",
  "task_id": "1234567890"
}'
```