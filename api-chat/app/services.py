import re
import json
from typing import Union
from app.models import *
from app.cache import *
from app.agent import GraphQLChatAgent, generate_text_with_llm
from app.prompts import get_query_generation_prompt

async def process_graphql_sdl(request: GraphQLTestPreparationRequest) -> Union[
    GraphQLTestPreparationResponse, ErrorInfo]:
    """Process GraphQL SDL by removing comments, descriptions, and minifying."""
    global token_count
    sdl = request["GRAPHQL_SCHEMA"]
    hashed_sdl = await get_hashed_string(sdl)
    cached_sdl = await retrieve_cached_sdl(hashed_sdl)

    if cached_sdl:
        print("Returning cached SDL")
        return GraphQLTestPreparationResponse(
            apiSpec=cached_sdl.apiSpec,
            queries=cached_sdl.queries,
            usage=token_count
        )

    sdl = re.sub(r"#.*", "", sdl)                           # Remove single-line comments
    sdl = re.sub(r'""".*?"""', "", sdl, flags=re.DOTALL)    # Remove multi-line comments
    sdl = re.sub(r'"[^"]*"', "", sdl)                       # Remove string literals
    sdl = re.sub(r"@deprecated([^\s}]*)*", "", sdl)         # Remove deprecated annotations
    sdl = re.sub(r"\s+", " ", sdl).strip()                  # Minify whitespace

    # Generate sample queries 
    query_prompt = await get_query_generation_prompt(sdl)  
    sample_queries, token_count = await generate_text_with_llm(query_prompt)

    if isinstance(sample_queries, ErrorInfo):
        return ErrorInfo(response="Error occurred during SDL processing.")
    
    parsed_queries = [{"scenario": k, "query": v} for k, v in json.loads(sample_queries).items()]

    cached_sdl = SdlCacheRecord(
        apiSpec=SdlResponse(sdl=sdl),
        queries=parsed_queries
    )
    await update_sdl_cache(hashed_sdl, cached_sdl)

    response = GraphQLTestPreparationResponse(
        apiSpec=SdlResponse(sdl=sdl),
        queries=parsed_queries,
        usage=token_count
    )
    return response

async def create_chat_agent(payload: json, apiChatRequestId: str) -> Union[
    GraphQLTestExecutionResponse, TestCompletionResponse, InvalidResponse, ErrorInfo]:
    """Execute a single step of the GraphQL chat agent."""
    global token_count
    if "command" in payload and "sdl" in payload:
        payload_obj = GraphQLTestInitializationRequest(**payload)
        print("Agent initialization started.")
        sdl = payload_obj.sdl
        command = payload_obj.command
        iteration = 1
        executionHistory = []
    elif "response" in payload:
        payload_obj = GraphQLTestExecutionRequest(**payload)
        print("Agent restoration started.")
        cache_record = await retrieve_cached_graphql_test_case(apiChatRequestId)
        if isinstance (cache_record, ErrorInfo):
            return cache_record
        sdl = cache_record["sdl"]
        command = cache_record["command"]
        iteration = cache_record["iteration"] + 1
        executionHistory = cache_record["executionHistory"]
        executionHistory.append(CacheStep(
            query=cache_record["previousResponse"],
            code=payload_obj.response.code,
            response=payload_obj.response.body
        ))
    else:
        return ErrorInfo(response="Invalid request payload")
    
    if not command:
        return ErrorInfo(response="Command cannot be empty")

    chat_agent = GraphQLChatAgent(
        apiChatRequestId,
        sdl["sdl"],
        command,
        iteration,
        executionHistory
    )
    if isinstance(chat_agent, ErrorInfo):
        return chat_agent
    response = await chat_agent.execute()

    if isinstance(response, ErrorInfo):
        return InvalidResponse(
            taskStatus="TERMINATED",
            result=response.response,
            usage=token_count
        )
    elif isinstance(response, TestCompletionResponse) or isinstance(response, InvalidResponse):
        return response
    elif isinstance(response, GraphQLExecutionResult):
        await update_graphql_test_case_cache(apiChatRequestId, {
            "iteration": iteration,
            "command": command,
            "sdl": sdl,
            "executionHistory": [step if isinstance(step, dict) else step.dict() for step in executionHistory],
            "previousResponse": response.inputs.requestBody.query
        })
        return GraphQLTestExecutionResponse(
            taskStatus="IN_PROGRESS",
            resource=response,
            usage=token_count
        )
    else:
        return ErrorInfo(response="Error while processing the request.")
