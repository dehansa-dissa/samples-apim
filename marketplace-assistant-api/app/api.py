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
from langchain.callbacks import get_openai_callback
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

# streaming stage constants
START_STREAM = "START_STREAM"
FIND_LLM_RESPONSE = "FIND_LLM_RESPONSE"
SEND_LLM_RESPONSE = "SEND_LLM_RESPONSE"
END_LLM_RESPONSE = "END_LLM_RESPONSE"
FIND_API = "FIND_API"
SEND_API = "SEND_API"
BUFFER_API = "BUFFER_API"
FINISH_STREAM = "FINISH_STREAM"

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


class ChoreoQuery(BaseModel):
    questions: list
    history: Optional[list]
    # tenant_domain: Optional[str] = None


class ChoreoResponse(BaseModel):
    content: str
    usage: dict


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


def get_retriever(tenant_domain, partition_id) -> MultiQueryRetriever:
    vectorstore = get_vectorstore()
    # TODO: Try adding a Self Query retriever
    # Incorporate score based filtering mechanism once Milverse introduces it
    if SOURCE_PLATFORM == APIM:
        retriever = vectorstore.as_retriever(search_type="similarity",
                                             search_kwargs={"k": 5,
                                                            "expr": 'key_id == "' + partition_id + '" && tenant_domain == "' + tenant_domain + '"'})

        llm = AzureChatOpenAI(
            #     temperature=0.3,
            model_name="gpt-35-turbo",
            #     max_tokens=2048,
            deployment_name=AZURE_CHAT_DEPLOYMENT,
            api_version=AZURE_CHAT_VERSION,
            azure_endpoint=AZURE_ENDPOINT,
        )

    elif SOURCE_PLATFORM == CHOREO:
        retriever = vectorstore.as_retriever(search_type="similarity",
                                             search_kwargs={"k": 5, "expr": 'org_id == "' + partition_id + '"'})

        llm = AzureChatOpenAI(
            #     temperature=0.3,
            # model_name="gpt-35-turbo",
            #     max_tokens=2048,
            deployment_name=AZURE_CHAT_DEPLOYMENT,
            api_version=AZURE_CHAT_VERSION,
            azure_endpoint=AZURE_ENDPOINT,
        )


    QUERY_PROMPT = PromptTemplate(
        input_variables=["question"],
        template="""You are an API Marketplace assistant. Your task is to generate three 
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
    if not docs:
        return ["No API information available!"]
    else:
        return "\n\n".join(str({"api_details": doc.metadata, "api_spec": doc.page_content}) for doc in docs)


def prepare_rag_chain(tenant_domain: str, partition_id: str, stream=False):
    retriever = get_retriever(tenant_domain, partition_id)

    llm = AzureChatOpenAI(
        temperature=0.3,
        model_name="gpt-35-turbo",
        #     max_tokens=2048,
        deployment_name=AZURE_CHAT_DEPLOYMENT,
        api_version=AZURE_CHAT_VERSION,
        azure_endpoint=AZURE_ENDPOINT,
    )

    contextualize_q_system_prompt = """You are a helpful assistant. Based on the chat history, please rephrase the final user’s question into a standalone question. \
    STRICT CONDITION: DO NOT ANSWER THE QUESTION!!, just reformulate it if needed and otherwise return it as is \
    Please ignore the history if the latest question is not relevant to the history
    Make sure to reference any relevant API names from the history in the new question
    If the human question is not a valid english language text, return it as it is"""
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )

    if SOURCE_PLATFORM == CHOREO:
        # Condition was added so if needed, we can add a separate prompt for streaming.
        if stream:
            qa_system_prompt = """System: You are a simple, and cheerful API Marketplace assistant. who only speaks using JSON. Based on the provided API details, 
            recommend relevant APIs. Ensure the recommendation is accurate and tailored to the user's needs. If you can't find the API from the context, just say that you don't know politely.
            Understand the provided context and IGNORE the APIs that does not match the human question. 
            Please note that the context contains information about different types of APIs: REST, GraphQL, and Async.
            Only recommend APIs that are specified in the context and avoid including made-up APIs. Provide a JSON response with the following format(here, names of APIs are made up to explain the json format):
              {{\"response\": \"LLM output in natural language explaining the recommendation\", \"apis\": [{{\"apiId\": \"id1\", \"apiName\": \"SampleAPI1\",
                \"version\": \"2.0\"}}, {{\"apiId\": \"id2\", \"apiName\": \"SampleAPI2\", \"version\": \"4.0\"}}]}}.
            Make sure to give an easily understandable explanation of the API or APIs selected in the \"response\" section. Leave the \"apis\" list empty in case you do not have any API recommendations included in the response.
            Given below are the actual API context you need to use to construct the response. 
            Context: {context}"""
        else:
            qa_system_prompt = """System: You are a simple, and cheerful API Marketplace assistant. Who only speak correct markdown text. Based on the provided API details, 
            recommend all relevant APIs. Ensure the recommendation is accurate and tailored to the user's needs. If you can't find the API from the context, API politely inform about it.
            Understand the provided context and IGNORE the APIs that does not match the human question. DO NOT SHOW ANY URLS including REDIRECT URLS in the response. 
            Please note that the context contains information about different types of APIs: REST, GraphQL, and Async.
            Only recommend APIs that are specified in the context and avoid including made-up APIs.
            Given below are the actual API context you need to use to construct the response.
            Context: {context}"""
    else:
        qa_system_prompt = """You are a simple, and cheerful API Marketplace assistant. who only speaks using JSON. Based on the provided API details, 
            recommend all relevant APIs. Ensure the recommendation is accurate and tailored to the user's needs. 
            Strict Condition: If you can't find the API from the context, Just say that you are not aware of such an API politely. Please don't share false information!
            Understand the provided context, which is are the only APIs you are aware of and IGNORE the APIs that does not match the human question. 
            Please note that the context contains information about different types of APIs: REST, GraphQL, and Async.
            Only recommend APIs that are specified in the context and avoid including made-up APIs. Provide a JSON response with the following format(here, names of APIs are made up to explain the json format):
              {{\"response\": \"LLM output in natural language explaining the recommendation\", \"apis\": [{{\"apiId\": \"id1\", \"apiName\": \"SampleAPI1\",
                \"version\": \"2.0\"}}, {{\"apiId\": \"id2\", \"apiName\": \"SampleAPI2\", \"version\": \"4.0\"}}]}}.
            Make sure to give an easily understandable explanation of the API or APIs selected in the \"response\" section. Leave the \"apis\" list empty in case you do not have any API recommendations included in the response.
            Given below are the actual API context you need to use to construct the response.
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
        tenant_domain: str, message: str, history: list, partitionID: str
):
    results = await asyncio.gather(
        in_thread(prepare_rag_chain, tenant_domain, partitionID),
        prepare_history(history),
    )
    rag_chain = results[0]
    chat_history = results[1]

    with get_openai_callback() as cb:
        chain_response = await rag_chain.ainvoke({
            "question": message,
            "chat_history": chat_history},
            # config={
            #     'callbacks': [ConsoleCallbackHandler()]
            #     }
        )
        chain_response = parse_json(chain_response.content, cb)
    return chain_response


async def generate_choreo_response(messages: list, org_id: str):
    history = []
    response = ChoreoResponse(content="", usage={})
    results = await asyncio.gather(
        in_thread(prepare_rag_chain, None, org_id),
        prepare_history(history),
    )
    rag_chain = results[0]
    chat_history = results[1]

    questions = ""
    for message in messages:
        questions = questions + message + "\n"

    with get_openai_callback() as cb:
        assist_response = (rag_chain.invoke({
            "question": questions,
            "chat_history": chat_history},
            # config={
            #     'callbacks': [ConsoleCallbackHandler()]
            #     }
        ))

    assist_response_json = parse_choreo_json(assist_response.content, cb)
    response.content = create_str_markdown(assist_response_json["response"])
    response.usage = assist_response_json["usage"]

    return response


async def generate_sse_response(
        tenant_domain: str, message: str, history: list, org_id: str
) -> AsyncGenerator[str, QuerySSEResponse]:
    results = await asyncio.gather(
        in_thread(prepare_rag_chain, tenant_domain, org_id, True),
        prepare_history(history),
    )
    rag_chain = results[0]
    chat_history = results[1]

    try:
        stage = START_STREAM
        api_buffer = ""
        async for token in rag_chain.astream({"question": message, "chat_history": chat_history}):
            if stage == START_STREAM:
                if "{" not in token.content:
                    yield token.content
                    continue
                stage = FIND_LLM_RESPONSE

            stage, response = await process_sse_response(stage, token.content)

            if not response:
                continue

            if stage == SEND_LLM_RESPONSE or stage == END_LLM_RESPONSE:
                yield response
                if stage == END_LLM_RESPONSE:
                    stage = FIND_API
                continue

            if stage == BUFFER_API:
                api_buffer = api_buffer + response

            if stage == SEND_API:
                if api_buffer != "":
                    api_buffer = api_buffer + response
                    stage = FIND_API
                    yield api_buffer
                api_buffer = ""
                continue

    except Exception as e:  # TODO: Add proper exception handling
        yield QuerySSEResponse(type="error", value=str(e)).json()


async def process_sse_response(stage, token_content):
    if stage == FIND_LLM_RESPONSE:
        if token_content.startswith("\":"):
            return SEND_LLM_RESPONSE, None

    elif stage == SEND_LLM_RESPONSE:
        if "\"," in token_content:
            head, sep, tail = token_content.partition(',')
            return END_LLM_RESPONSE, head

    elif stage == FIND_API:
        if "{" in token_content:
            head, sep, tail = token_content.partition('{')
            return BUFFER_API, "\n" + sep + tail
        else:
            return FIND_API, None

    elif stage == BUFFER_API and "}" in token_content:
        head, sep, tail = token_content.partition('}')
        return SEND_API, head + sep

    return stage, token_content

def parse_json(json_resp, token_usage):
    try:
        json_object = json.loads(json_resp)
        #Handle the case where the LLM responds with the key name instead of apiName
        if "name" in json_object:
            json_object["apiName"] = json_object["name"]
            del json_object["name"]
        json_object["usage"] = {
            "prompt_tokens": token_usage.prompt_tokens,
            "completion_tokens": token_usage.completion_tokens,
            "total_tokens": token_usage.total_tokens
        }
    except ValueError as e:
        return {
            "response": json_resp,
            "apis": [],
            "usage": {
                "prompt_tokens": token_usage.prompt_tokens,
                "completion_tokens": token_usage.completion_tokens,
                "total_tokens": token_usage.total_tokens
            }
        }
    return json_object

def parse_choreo_json(json_resp, token_usage):
    try:
        json_object = json.loads(json_resp)
        # todo get the correct token counts
        if "usage" not in json_object:
            json_object["usage"] = {
                "prompt_tokens": token_usage.prompt_tokens,
                "completion_tokens": token_usage.completion_tokens,
                "total_tokens": token_usage.total_tokens
            }
    except ValueError as e:
        return {"response": json_resp,
                "usage": {
                    "prompt_tokens": token_usage.prompt_tokens,
                    "completion_tokens": token_usage.completion_tokens,
                    "total_tokens": token_usage.total_tokens
                }
                }
    return json_object


def create_str_markdown(response):
    return "\n" + response


@api.post("/marketplace-assistant")
async def marketplace_assistant(request: Query, keyID: str):
    response = await generate_response(tenant_domain=request.tenant_domain, message=request.query,
                                       history=request.history, partitionID=keyID)
    return response


@api.post("/choreo-marketplace-assistant")
async def marketplace_assistant(request: ChoreoQuery, orgID: str):
    response = await generate_choreo_response(messages=request.questions, org_id=orgID)

    return response


@api.post("/marketplace-assistant/streaming")
async def marketplace_assistant_sse(
        request: Query, orgID: str
) -> StreamingResponse:
    return StreamingResponse(
        generate_sse_response(tenant_domain=request.tenant_domain, message=request.query, history=request.history,
                              org_id=orgID),
        media_type="text/event-stream",
    )


@api.get("/health")
def health():
    """Check the api is running"""
    return {"status": "Running"}
