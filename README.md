# apim-ai-deployments
[![Build Status](https://dev.azure.com/choreo-devops/choreo-control-plane-components/_apis/build/status%2Fbuild%2Fchoreo-marketplace-assistant-build-x?repoName=wso2-enterprise%2Fapim-ai-deployments&branchName=main)](https://dev.azure.com/choreo-devops/choreo-control-plane-components/_build/latest?definitionId=1411&repoName=wso2-enterprise%2Fapim-ai-deployments&branchName=main)

Included the source code for

- Deployments made on Choreo Control Plane to serve AI features of the on-prem API manager.
- Deployments related to Choreo marcKketplace assistant

## milvus_proxy_service

This service is deployed in choreo control plane, this is used as a proxy to connect to milvus vectorDB. Currently this is being used by Marketplace assistant and docs assistant

### Enviroment variables

### Configs

- MILVERSE_URL = Public URL from the cluster details in zilliz ([Reference: How to setup zilliz milvus vectorDB](#how-to-setup-zilliz-milvus-vectordb))
- LOG_LEVEL = Define the log level (default is INFO) - Not mandotory

### Secrets

- MILVERSE_API_KEY = Token from the cluster details in zilliz ([Reference: How to setup zilliz milvus vectorDB](#how-to-setup-zilliz-milvus-vectordb))

### How to setup zilliz milvus vectorDB (This was setup by the digiops team)

1. Go to - https://cloud.zilliz.com/
2. Login and create a project.
3. Create a cluster providing the required informtion
4. Under the cluster details you can get the public URL and custer APIkey

## spec_populator_service

This service is deployed in choreo control plane. This is used to populate the vector databased with the processed information about the marketpalce APIs.

### Enviroment variables

### Configs

- AZURE_DEPLOYMENT = Azure model deployment name (i.e - choreo-ai-embedding) ([Reference: Set up zure openAI service](#set-up-zure-openai-service-this-was-setup-by-the-sre))
- AZURE_ENDPOINT = Azure openAI service endpoint ([Reference: Set up zure openAI service](#set-up-zure-openai-service-this-was-setup-by-the-sre))
- COLLECTION_NAME = Name of the milvuz zillis collection (i.e DevChoreoMarketplace)
- CREATE_COLLECTION = 'True' if you have not created collection manually. It is recommened to create the collection through code.
- MILVERSE_URL=Public URL from the cluster details in zilliz ([Reference: How to setup zilliz milvus vectorDB](#how-to-setup-zilliz-milvus-vectordb))
- SOURCE_PLATFORM=
- EXCLUDED_ORG_LIST=List of organization uuids which has opt out from AI features (default "")
- LOG_LEVEL=Define the log level (default is INFO) - Not mandotory

### Secrets
- AZURE_OPENAI_API_KEY - Azure OpenAI service key ([Reference: Set up zure openAI service](#set-up-zure-openai-service-this-was-setup-by-the-sre))
- MILVERSE_API_KEY = Token from the cluster details in zilliz ([Reference: How to setup zilliz milvus vectorDB](#how-to-setup-zilliz-milvus-vectordb)) 

### How to setup zilliz milvus vectorDB (This was setup by the digiops team)

1. Go to - https://cloud.zilliz.com/
2. Login and create a project.
3. Create a cluster providing the required informtion
4. Under the cluster details you can get the public URL and custer APIkey

### Set up zure openAI service (This was setup by the SRE)

#### Setup through Terraform
Need to provide the service name and and the model deployment name and the model as `text-embedding-ada-002` and run the scripts. And get the service endpoint and the keys. 

#### Setup Manually
1. Go to - AI foundry | Azure OpenAI
2. Create a openAI service
3. Go to the created openAI service and open the Azure openAI Foundy portal
4. Deploy the embeding model `text-embedding-ada-002` by providing the deployment name.
5. From the overview page of the created openAI service, get the endpoint (URL) and the keys.

