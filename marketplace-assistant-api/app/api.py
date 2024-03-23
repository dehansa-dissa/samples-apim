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
from langchain.callbacks.tracers import ConsoleCallbackHandler
from pydantic import BaseModel, BaseSettings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import asyncio

from functools import partial
from functools import lru_cache
from typing import AsyncGenerator, Literal

from langchain.chat_models import AzureChatOpenAI
from langchain_community.vectorstores import Milvus
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import PromptTemplate


api = FastAPI(
    title="API Marketplace Chatbot",
    version="0.1.0",
)

ZILLIZ_CLOUD_URI =  os.getenv('ZILLIZ_CLOUD_URI')
ZILLIZ_CLOUD_API_KEY = os.getenv('ZILLIZ_CLOUD_API_KEY')
AZURE_ENDPOINT =  os.getenv('AZURE_ENDPOINT')
AZURE_EMBEDDING_DEPLOYMENT = os.getenv('AZURE_EMBEDDING_DEPLOYMENT')
AZURE_CHAT_DEPLOYMENT = os.getenv('AZURE_CHAT_DEPLOYMENT')
AZURE_CHAT_VERSION = os.getenv('AZURE_CHAT_VERSION')

# request input format
class Query(BaseModel):
    query: str
    history: list
    tenant_domain: str

class QuerySSEResponse(BaseModel):
    type: Literal["start", "streaming", "end", "error"]
    value: str

@lru_cache()
def get_vectorstore(orgID: str) -> Milvus:
    collection_name = orgID + '__apim__'
    model_name = 'text-embedding-ada-002'
    embeddings = AzureOpenAIEmbeddings(
        model=model_name,
        azure_deployment=AZURE_EMBEDDING_DEPLOYMENT,
        azure_endpoint=AZURE_ENDPOINT,
        openai_api_type="azure",
    )
    vectorstore = Milvus(
        embeddings,
        connection_args={
            "uri": ZILLIZ_CLOUD_URI,
            "token": ZILLIZ_CLOUD_API_KEY,
            "secure": True,
        },
        collection_name=collection_name,
        text_field="page_content",
        metadata_field="metadata"
    )

    return vectorstore

def get_retriever(tenant_domain, orgID) -> MultiQueryRetriever:
    vectorstore = get_vectorstore(orgID)
    # TODO: Try adding a Self Query retriever
    # Incorporate score based filtering mechanism once Milverse introduces it
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5, "expr": 'tenant_domain == "' + tenant_domain + '"'})
    llm = AzureChatOpenAI(
    #     temperature=0.3,
        model_name="gpt-35-turbo",
    #     max_tokens=2048,
        deployment_name=AZURE_CHAT_DEPLOYMENT,
        api_version=AZURE_CHAT_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
    )

    mq_retriever = MultiQueryRetriever.from_llm(
        retriever=retriever, llm=llm
    )
    return mq_retriever


def format_docs(docs):
    return "\n\n".join(str({"api_details": doc.metadata, "api_spec":doc.page_content}) for doc in docs)

def prepare_rag_chain(tenant_domain: str, orgID: str):
    retriever = get_retriever(tenant_domain, orgID)

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
    
    contextualize_q_system_prompt = """Given a chat history and the latest user question \
    which might reference context in the chat history, formulate a standalone question \
    which can be understood without the chat history. Do NOT answer the question, \
    just reformulate it if needed and otherwise return it as is."""
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )
    contextualize_q_chain = contextualize_q_prompt | llm | StrOutputParser()

    qa_system_prompt = """You are an assistant for question-answering tasks. \
    Use the following pieces of retrieved context to answer the question. \
    If you don't know the answer, just say that you don't know. \

    {context}"""
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )


    def contextualized_question(input: dict):
        if input.get("chat_history"):
            return contextualize_q_chain
        else:
            return input["question"]


    rag_chain = (
        RunnablePassthrough.assign(
            context=contextualized_question | retriever | format_docs
        )
        | qa_prompt
        | llm
    )
    return rag_chain


async def in_thread(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args))

async def prepare_history(history: list):
    return [(chat["role"],chat["content"]) for chat in history]

async def generate_response(
    tenant_domain: str, message: str, history: list, orgID: str
):
    results = await asyncio.gather(
        in_thread(prepare_rag_chain, tenant_domain, orgID), 
        prepare_history(history),
    )
    rag_chain = results[0]
    chat_history = results[1]
    
    return(rag_chain.invoke({ 
        "question": message,
        "chat_history": chat_history},
        # config={
        #     'callbacks': [ConsoleCallbackHandler()]
        #     }
        ))
    # response = ""
    # async for token in rag_chain.astream({ 
    #     "question": message,
    #     "chat_history": chat_history}):
    #     yield token.content
    # response += token.content


async def generate_sse_response(
    tenant_domain: str, message: str, history: list, orgID: str
) -> AsyncGenerator[str, QuerySSEResponse]:
    
    results = await asyncio.gather(
        in_thread(prepare_rag_chain, tenant_domain, orgID), 
        prepare_history(history),
    )
    rag_chain = results[0]
    chat_history = results[1]

    response = ""
    try:
        yield QuerySSEResponse(type="start", value="").json()
        async for token in rag_chain.astream({ 
                            "question": message,
                            "chat_history": chat_history}):  # type: ignore
            yield QuerySSEResponse(type="streaming", value=token.content).json()
            response += token.content

        yield QuerySSEResponse(type="end", value="").json()
    except Exception as e:  # TODO: Add proper exception handling
        yield QuerySSEResponse(type="error", value=str(e)).json()

@api.post("/marketplace-assistant")
async def marketplace_assistant(request: Query, orgID: str):
    response = await generate_response(tenant_domain=request.tenant_domain, message=request.query, history=request.history, orgID=orgID)
    
    return {"response": response.content, "apis": []}

@api.post("/marketplace-assistant/streaming")
async def marketplace_assistant_sse(
    request: Query, orgID: str
) -> StreamingResponse:

    return StreamingResponse(
        generate_sse_response(tenant_domain=request.tenant_domain, message=request.query, history=request.history, orgID=orgID),
        media_type="text/event-stream",
    )

@api.get("/health")
def health():
    """Check the api is running"""
    return {"status": "Running"}
