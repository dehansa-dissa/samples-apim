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

import asyncio
import os
from typing import Any, List
import json
from typing import Optional
from langchain_openai import AzureOpenAIEmbeddings
from operator import itemgetter
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from queue import Queue
from langchain.callbacks.tracers import ConsoleCallbackHandler
from pydantic import BaseModel, BaseSettings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.output_parsers import StrOutputParser, BaseOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.runnables import RunnableParallel
import asyncio
from pydantic import BaseModel

from functools import partial
from functools import lru_cache
from typing import AsyncGenerator, Literal

from langchain.chat_models import AzureChatOpenAI
from langchain.chains import LLMChain
from langchain_community.vectorstores import Milvus
from langchain.retrievers.multi_query import MultiQueryRetriever

CHOREO = "choreo"
APIM = "apim"

api = FastAPI(
    title="API Marketplace Chatbot",
    version="0.1.0",
)

ZILLIZ_CLOUD_URI = os.getenv('ZILLIZ_CLOUD_URI')
ZILLIZ_CLOUD_API_KEY = os.getenv('ZILLIZ_CLOUD_API_KEY')
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')
AZURE_EMBEDDING_DEPLOYMENT = os.getenv('AZURE_EMBEDDING_DEPLOYMENT', "OpenAPIEmbeddings")
AZURE_CHAT_DEPLOYMENT = os.getenv('AZURE_CHAT_DEPLOYMENT', "APIM-Deployment")
AZURE_CHAT_VERSION = os.getenv('AZURE_CHAT_VERSION', "2023-12-01-preview")
SOURCE_PLATFORM = os.getenv('SOURCE_PLATFORM')


# TODO: implement debug logging switch

collection_name = os.getenv("COLLECTION_NAME")
# request input format
class Query(BaseModel):
    query: str
    history: list
    tenant_domain: Optional[str] = None


class QuerySSEResponse(BaseModel):
    type: Literal["start", "streaming", "end", "error"]
    value: str


@lru_cache()
def get_vectorstore() -> Milvus:
    model_name = 'text-embedding-ada-002'
    embeddings = AzureOpenAIEmbeddings(
        model=model_name,
        azure_deployment=AZURE_EMBEDDING_DEPLOYMENT,
        azure_endpoint=AZURE_ENDPOINT,
        openai_api_type="azure",
    )
    # Todo Check if the collection is available in the Milvus
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
    vectorstore = get_vectorstore()
    # TODO: Try adding a Self Query retriever
    # Incorporate score based filtering mechanism once Milverse introduces it
    if SOURCE_PLATFORM == APIM:
        retriever = vectorstore.as_retriever(search_type="similarity",
                                             search_kwargs={"k": 5, "expr": 'org_id == "' + orgID + '" && tenant_domain == "' + tenant_domain + '"'})
    elif SOURCE_PLATFORM == CHOREO:
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5, "expr": 'org_id == "' + orgID + '"'})

    llm = AzureChatOpenAI(
        #     temperature=0.3,
        model_name="gpt-35-turbo",
        #     max_tokens=2048,
        deployment_name=AZURE_CHAT_DEPLOYMENT,
        api_version=AZURE_CHAT_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
    )


    QUERY_PROMPT = PromptTemplate(
        input_variables=["question"],
        template="""You are an AI language model assistant. Your task is to generate three 
        different versions of the given user question to retrieve relevant documents from a vector 
        database. By generating multiple perspectives on the user question, your goal is to help
        the user overcome some of the limitations of the distance-based similarity search. 
        Provide these alternative questions separated by newlines.
        Original question: {question}""",
    )

    class LineListOutputParser(BaseOutputParser[List[str]]):
        """Output parser for a list of lines."""

        def parse(self, text: str) -> List[str]:
            lines = text.strip().split("\n")
            return lines


    output_parser = LineListOutputParser()
    llm_chain = LLMChain(llm=llm, prompt=QUERY_PROMPT, output_parser=output_parser)

    mq_retriever = MultiQueryRetriever(
        retriever=retriever, llm_chain=llm_chain, parser_key="lines"
    )
    return mq_retriever


def format_docs(docs):
    return "\n\n".join(str({"api_details": doc.metadata, "api_spec": doc.page_content}) for doc in docs)


def prepare_rag_chain(tenant_domain: str, orgID: str):
    retriever = get_retriever(tenant_domain, orgID)

    llm = AzureChatOpenAI(
        #     temperature=0.3,
        model_name="gpt-35-turbo",
        #     max_tokens=2048,
        deployment_name=AZURE_CHAT_DEPLOYMENT,
        api_version=AZURE_CHAT_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
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
    # TODO: alter prompt so that we can handle both streaming case and REST case. We can keep the core of the prompt same and alter the rendering instructions.
    qa_system_prompt = """System: You are an assistant who only speaks using JSON. Based on the provided API details, 
    recommend relevant APIs. Ensure the recommendation is accurate and tailored to the user's needs.
    Please note that the context contains information about different types of APIs: REST, GraphQL, and Async.
    Only recommend APIs that are specified in the context and avoid including made-up APIs. Provide a JSON response with the following format(here, names of APIs are made up to explain the json format):
      {{\"response\": \"LLM output in natural language explaining the recommendation\", \"apis\": [{{\"apiId\": \"id1\", \"apiName\": \"SampleAPI1\",
        \"version\": \"2.0\"}}, {{\"apiId\": \"id2\", \"apiName\": \"SampleAPI2\", \"version\": \"4.0\"}}]}}.
    Make sure to give an easily understandable explanation of the API or APIs selected in the \"response\" section. Leave the \"apis\" list empty in case you do not have any API recommendations included in the response.
    Given below are the actual API context you need to use to construct the response. If you can't find the API from the context, just say that you don't know.
    Context: {context}"""
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            ("human", "{question}"),
        ]
    )
        
    _inputs = RunnableParallel(
        standalone_question=RunnablePassthrough.assign(
            chat_history=lambda x: x["chat_history"]
        )
        | contextualize_q_prompt
        | llm
        | StrOutputParser(),
    )

    # def cond_input(input: dict):
    #     if input.get("chat_history"):
    #         return _inputs
    #     else:
    #         return input["question"]

    _context = {
        "context": itemgetter("standalone_question") | retriever | format_docs,
        "question": lambda x: x["standalone_question"],
    }
    rag_chain = _inputs | _context | qa_prompt | llm

    return rag_chain


async def in_thread(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args))


async def prepare_history(history: list):
    return [(chat["role"], chat["content"]) for chat in history]


async def generate_response(
        tenant_domain: str, message: str, history: list, orgID: str
):
    results = await asyncio.gather(
        in_thread(prepare_rag_chain, tenant_domain, orgID),
        prepare_history(history),
    )
    rag_chain = results[0]
    chat_history = results[1]

    return (rag_chain.invoke({
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


def parse_json(json_resp):
    try:
        json_object = json.loads(json_resp)
    except ValueError as e:
        return json_resp
    return json_object


@api.post("/marketplace-assistant")
async def marketplace_assistant(request: Query, orgID: str):
    response = await generate_response(tenant_domain=request.tenant_domain, message=request.query,
                                       history=request.history, orgID=orgID)

    return parse_json(response.content)


@api.post("/marketplace-assistant/streaming")
async def marketplace_assistant_sse(
        request: Query, orgID: str
) -> StreamingResponse:
    return StreamingResponse(
        generate_sse_response(tenant_domain=request.tenant_domain, message=request.query, history=request.history,
                              orgID=orgID),
        media_type="text/event-stream",
    )


@api.get("/health")
def health():
    """Check the api is running"""
    return {"status": "Running"}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(api, port=8000)
