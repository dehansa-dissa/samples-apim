# Choreo TestGPT

AI-based API testing using natural language commands.

# Deployment
To configure the TestGPT service locally, you need to:

## Prerequisites

### 1. Creating Azure Models
- Create an [Azure](https://azure.microsoft.com/en-us/features/azure-portal/) account
- Create an [Azure OpenAI resource](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource)
- Using Azure AI Studio, deploy two model resources from `text-davinci-003` and `gpt-35-turbo` by referring to [Deploy a model](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal#deploy-a-model) guide
- Obtain the token and other required parameaters by following [Azure OpenAI Authentication](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/reference#authentication).

### 2. Creating Azure Redis Cache
- Create an Azure Redis Cache following the guide [Azure Cache for Redis](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/quickstart-create-redis)
- Obtain the hostname and the password to connect using the guide [Azure Redis Cache Connection](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-python-get-started#retrieve-host-name-ports-and-access-keys-from-the-azure-portal)

### 3. Configuring the TestGPT Service
1. Clone this repo.
2. [Setup Ballerina](#setup-ballerina).
3. Create the `Config.toml` with the following configurations (Retrieved following the previous steps).
```toml
# Azure OpenAI configs
azureOpenAIToken = "" # Azure OpenAI api access token
azureOpenAIServiceUrl = "" # Azure OpenAI service URL
azureOpenAITextDeploymentId = "" # `text-davinci-003` deployment ID
azureOpenAIChatDeploymentId = "" # `gpt-35-turbo` deplpoyment ID
azureOpenAIApiVersion = "2023-05-15" # Azure OpenAI API version

# Azure Redis configs
redisHost = "" # Azure Redis hostname
redisPassword = "" # Azure Redis password
```

# Testing

## 1. logic testing

To run the logic test cases, use the following command.

```
bal test --groups logic --code-coverage 
```

## 2. Accuracy testing

The accuracy of the API Chat is evaluated using two types of metrics:
    Correct path rate: This evaluates the model-generated path to execute a specific command.
    Success rate: This evaluates the responses received for a specific command.

To run the accuracy test cases, use the following command.

```
bal test --groups accuracy -CisAccuracyTest=true
```

# Build and Run

To build the project use the following command.

```
bal build
```

To run the project directly, use the following command. 

```
bal run
```

The service should be accessible via `http://127.0.0.1:9090/{PATH}`. To verify, whether the service is up and running you can use the health check resource `/health`