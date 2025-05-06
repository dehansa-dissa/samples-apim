import re
import json
from typing import Union
from app.models import *
from app.cache import get_hashed_string, retrieve_cached_sdl, update_sdl_cache, retrieve_cached_graphql_test_case, update_graphql_test_case_cache
from app.agent import GraphQLChatAgent, generate_text_with_llm, get_token_count

def process_graphql_sdl(request: GraphQLTestPreparationRequest) -> Union[GraphQLTestPreparationResponse, ErrorInfo]:
    """Process GraphQL SDL by removing comments, descriptions, and minifying."""
    token_counts = TokenCounts(
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0
    )
    sdl = request["GRAPHQL_SCHEMA"]
    hashed_sdl = get_hashed_string(sdl)
    cached_sdl = retrieve_cached_sdl(hashed_sdl)

    if cached_sdl:
        print("Returning cached SDL")
        return GraphQLTestPreparationResponse(
            apiSpec=SdlResponse(sdl=cached_sdl.apiSpec.sdl),
            queries=cached_sdl.queries,
            usage=token_counts
        )

    # Minify SDL
    sdl = re.sub(r"#.*", "", sdl)
    sdl = re.sub(r'""".*?"""', "", sdl, flags=re.DOTALL)
    sdl = re.sub(r'"[^"]*"', "", sdl)
    sdl = re.sub(r"@deprecated([^\s}]*)*", "", sdl)
    sdl = re.sub(r"\s+", " ", sdl).strip()

    # Generate sample queries
    query_prompt = get_query_generation_prompt(sdl)
    sample_queries = generate_text_with_llm(query_prompt)
    token_counts.prompt_tokens = get_token_count(query_prompt)
    token_counts.completion_tokens = get_token_count(sample_queries)
    token_counts.total_tokens = token_counts.prompt_tokens + token_counts.completion_tokens

    if isinstance(sample_queries, ErrorInfo):
        return ErrorInfo(response="Error occurred during SDL processing.")
    
    parsed_queries = [{"scenario": k, "query": v} for k, v in json.loads(sample_queries).items()]

    cached_sdl = SdlCacheRecord(
        apiSpec=SdlResponse(sdl=sdl),
        queries=parsed_queries
    )
    update_sdl_cache(hashed_sdl, cached_sdl)

    response = GraphQLTestPreparationResponse(
        apiSpec=SdlResponse(sdl=sdl),
        queries=parsed_queries,
        usage=token_counts
    )
    return response

def get_query_generation_prompt(sdl: str) -> str:
    """Generate a prompt for query generation based on the SDL."""
    return f'''You are a technical writer who understands GraphQL schemas. You are given the SDL (Schema Definition Language) of a GraphQL API below. Your task is to generate natural language tasks that users might ask, based on this schema.
    The schema is as follows:
    {sdl}

    You must return THREE natural language requests:

    1. **Simple Query** :A task that retrieves data from a single GraphQL type with minimal or no nested fields.
    2. **Complex Query** :A task that retrieves data from a GraphQL type **with nested/related types**, or multiple levels of relationships.
    3. **Mutation Task** :A task that **modifies** the data (e.g., creates, updates, deletes something), based on the mutations defined in the schema.

    Use realistic example values for arguments like IDs, names, filters, or input payloads.

    Do NOT include the actual GraphQL queries or mutations. Only return the **natural language task descriptions**.

    The response must strictly follow this JSON format:

    {{
        "simpleQuery": {{A natural language query using basic fields from the schema}},
        "complexQuery": {{A natural language query involving nested or related types}},
        "mutationTask": {{A natural language description of a mutation action based on the schema (if available)}}
    }}

    If the schema does not define any mutations, leave "mutationTask" as empty string.'''

async def create_chat_agent(payload: json, apiChatRequestId: str) -> Union[GraphQLTestExecutionResponse, GraphQLTestCompletionResponse, InvalidResponse, ErrorInfo]:
    """Execute a single step of the GraphQL chat agent."""
    token_count = TokenCounts(
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0
    )
    if "command" in payload and "sdl" in payload:
        payload_obj = GraphQLTestInitializationRequest(**payload)
        print("Agent Initialization Started.")
        sdl = payload_obj.sdl
        command = payload_obj.command
        iteration = 1
        executionHistory = []
    elif "response" in payload:
        payload_obj = GraphQLTestExecutionRequest(**payload)
        print("Agent Restoration Started.")
        cache_record = retrieve_cached_graphql_test_case(apiChatRequestId)
        if isinstance (cache_record, ErrorInfo):
            return ErrorInfo(response="Test case not found. Invalid or expired test case ID.")
        sdl = cache_record["sdl"]
        command = cache_record["command"]
        iteration = cache_record["iteration"]+1
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
    elif isinstance(response, GraphQLTestCompletionResponse) or isinstance(response, InvalidResponse):
        return response
    elif isinstance(response, TestStepResult):
        update_graphql_test_case_cache(apiChatRequestId, {
            "iteration": iteration,
            "command": command,
            "sdl": sdl,
            "executionHistory": [step if isinstance(step, dict) else step.dict() for step in executionHistory],
            "previousResponse": response.result.inputs.requestBody.query
        })
        return GraphQLTestExecutionResponse(
            taskStatus="IN_PROGRESS",
            resource={
                "method": "POST",
                "path": "/",
                "inputs": RequestBody(requestBody=ToolComponent(query=response.result.inputs.requestBody.query))},
            usage=response.usage
        )
    
