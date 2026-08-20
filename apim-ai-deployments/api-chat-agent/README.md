# API Chat Agent

Prepares REST API definitions and executes API test steps from natural-language commands.

# Deployment

## Prerequisites

Install Ballerina 2201.8.4 or a compatible update.

### Configuring the API Chat Agent

Create `Config.toml` in this directory:

```toml
# Azure OpenAI generates API descriptions, sample queries, and test steps.
azureOpenAIToken = ""
azureOpenAIServiceUrl = "https://<your-resource>.openai.azure.com/openai"
azureOpenAIDeploymentId = ""
AZURE_OPENAI_API_VERSION = ""

# Redis caches enriched API definitions and in-progress test cases.
redisHost = "localhost"
redisPassword = ""

```

# Build and Run

```bash
bal run
```

The service listens on `http://localhost:9090`. Check that it is running with:

```bash
curl http://localhost:9090/health
```

The supported endpoints are described in [openapi.yaml](openapi.yaml).

# Testing

```bash
bal test --groups logic --code-coverage
bal test --groups accuracy -CisAccuracyTest=true
```
