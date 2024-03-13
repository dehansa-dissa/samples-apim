# -------------------------------------------------------------------------------------
#
# Copyright (c) 2024, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.
#
# This software is the property of WSO2 LLC. and its suppliers, if any.
# Dissemination of any information or reproduction of any material contained
# herein in any form is strictly forbidden, unless permitted by WSO2 expressly.
# You may not alter or remove any copyright or other notice from copies of this content.
#
# --------------------------------------------------------------------------------------

import os
import asyncio
from typing import Any
import time
from langchain_openai import AzureOpenAIEmbeddings
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from queue import Queue
from pydantic import BaseModel, BaseSettings

from functools import lru_cache
from typing import AsyncGenerator, Literal

from langchain.chat_models import AzureChatOpenAI
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient, AsyncQdrantClient
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.schema import Document
from langchain.prompts import PromptTemplate


api = FastAPI(
    title="API Marketplace Chatbot",
    version="0.1.0",
)

class Settings(BaseSettings):
    qdrant_api_key: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# request input format
class Query(BaseModel):
    message: str

class QuerySSEResponse(BaseModel):
    type: Literal["start", "streaming", "end", "error"]
    value: str

@lru_cache()
def get_settings() -> Settings:
    return Settings()

@lru_cache()
def get_vectorstore() -> Qdrant:
    settings = get_settings()
    collection_name = 'openapi'
    model_name = 'text-embedding-ada-002'
    embeddings = AzureOpenAIEmbeddings(
        model=model_name,
        azure_deployment="OpenAPIEmbeddings",
        azure_endpoint='https://apim-ai-aus.openai.azure.com/',
        openai_api_type="azure",
    )
    async_qdrant_client = AsyncQdrantClient(
        url="https://c1b96d76-6539-4660-833d-347fc1b7b069.us-east4-0.gcp.cloud.qdrant.io:6333",
        api_key=os.environ["QDRANT_API_KEY"],
    )

    qdrant_client = QdrantClient(
        url="https://c1b96d76-6539-4660-833d-347fc1b7b069.us-east4-0.gcp.cloud.qdrant.io:6333",
        api_key=os.environ["QDRANT_API_KEY"],
    )

    vectorstore = Qdrant(
        client=qdrant_client, async_client=async_qdrant_client, collection_name=collection_name, 
        embeddings=embeddings,
    )

    return vectorstore

async def search_relevant_documents(query: str) -> list[Document]:
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.75})

    llm = AzureChatOpenAI(
    #     temperature=0.3,
        model_name="gpt-35-turbo",
    #     max_tokens=2048,
        deployment_name="APIM-Deployment",
        api_version="2023-12-01-preview",
        azure_endpoint='https://apim-ai-aus.openai.azure.com/',
    )

    mq_retriever = MultiQueryRetriever.from_llm(
        retriever=retriever, llm=llm
    )

    return await mq_retriever.aget_relevant_documents(query=query, k=10)

async def generate_response(
    docs: list[Document], message: str, settings: Settings
) -> AsyncGenerator[str, None]:

    QA_PROMPT = PromptTemplate(
        input_variables=["query", "contexts"],
        template="""System: Use the following Open API definitions to provide easily understandable answers to the user's question. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer.

        Contexts:
        {contexts}

        Human: {query}""",
    )

    llm = AzureChatOpenAI(
    #     temperature=0.3,
        model_name="gpt-35-turbo",
    #     max_tokens=2048,
        deployment_name="APIM-Deployment",
        api_version="2023-12-01-preview",
        azure_endpoint='https://apim-ai-aus.openai.azure.com/',
    )

    chain = QA_PROMPT | llm

    response = ""
    async for token in chain.astream({"contexts": "\n---\n".join([d.page_content for d in docs]), "query": message}):
        yield token.content
        response += token.content

async def generate_sse_response(
    docs: list[Document],
    message: str,
    settings: Settings,
) -> AsyncGenerator[str, QuerySSEResponse]:
    

    start = time.time()

    QA_PROMPT = PromptTemplate(
        input_variables=["query", "contexts"],
        template="""System: Use the following Open API definitions to provide easily understandable answers to the user's question. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer.

        Contexts:
        {contexts}

        Human: {query}""",
    )

    llm = AzureChatOpenAI(
    #     temperature=0.3,
        model_name="gpt-35-turbo",
    #     max_tokens=2048,
        deployment_name="APIM-Deployment",
        api_version="2023-12-01-preview",
        azure_endpoint='https://apim-ai-aus.openai.azure.com/',
    )

    chain = QA_PROMPT | llm  # type: ignore

    response = ""
    try:
        yield QuerySSEResponse(type="start", value="").json()
        async for token in chain.astream({"contexts": "\n---\n".join([d.page_content for d in docs]), "query": message}):  # type: ignore
            yield QuerySSEResponse(type="streaming", value=token.content).json()
            response += token.content

        yield QuerySSEResponse(type="end", value="").json()
    except Exception as e:  # TODO: Add proper exception handling
        yield QuerySSEResponse(type="error", value=str(e)).json()
    end = time.time()
    print("SSE Respond: " + str(end - start))

@api.post("/marketplace-assistant")
async def marketplace_assistant(
    request: Query, settings: Settings = Depends(get_settings)
) -> StreamingResponse:
    relevant_documents = await search_relevant_documents(query=request)
    return StreamingResponse(
        generate_response(
            docs=relevant_documents,
            message=request.message,
            settings=settings,
        ),
        media_type="text/plain",
    )

@api.post("/marketplace-assistant/sse")
async def marketplace_assistant_sse(
    request: Query, settings: Settings = Depends(get_settings)
) -> StreamingResponse:

    relevant_documents = await search_relevant_documents(query=request)

    return StreamingResponse(
        generate_sse_response(
            docs=relevant_documents,
            message=request.message,
            settings=settings,
        ),
        media_type="text/event-stream",
    )

@api.get("/health")
def health():
    """Check the api is running"""
    return {"status": "Running"}
