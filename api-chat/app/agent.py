import json
from graphql import build_schema, validate, parse
from openai import AzureOpenAI
import os
from typing import Union
from app.models import *
from app.cache import clear_test_case_cache
from app.prompts import get_next_tool_prediction_prompt, get_query_correction_prompt, get_apichat_context
from dotenv import load_dotenv

load_dotenv()

llm_client = AzureOpenAI(
    api_key=os.getenv("OPENAI_KEY"),  
    api_version=os.getenv("AZURE_CHAT_VERSION"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT")
)

class GraphQLChatAgent:
    def __init__(self, apiChatRequestId: str, sdl: json, command: str, iteration: int, 
                 executionHistory: list[CacheStep]):
        self.apiChatRequestId = apiChatRequestId
        self.sdl = sdl
        self.command = command
        self.iteration = iteration
        self.executionHistory = executionHistory
        self.isCompleted = False
        global token_count

        self.progress = {
            "query": command,
            "history": [
                {
                    "query": step.query if hasattr(step, "query") else step.get("query"),
                    "code": step.code if hasattr(step, "code") else step.get("code"),
                    "response": step.response if hasattr(step, "response") else step.get("response"),
                }
                for step in executionHistory
            ],
            "context": get_apichat_context()
        }
        print("Agent Initialization Completed.")

    async def execute(self) -> Union[GraphQLExecutionResult, TestCompletionResponse, InvalidResponse, ErrorInfo]:
        """Execute the GraphQL API chat agent."""
        for _ in range(APICHAT_RETRY_COUNT):
            llm_response = await self.reason()

            if isinstance(llm_response, ErrorInfo):
                return ErrorInfo(response=llm_response)

            fixed_llm_response = await self.fix_response(llm_response) 
            if isinstance(fixed_llm_response, ErrorInfo) or isinstance(fixed_llm_response, InvalidResponse):
                return fixed_llm_response
            if isinstance(fixed_llm_response, TestCompletionResponse):   
                print(f"Task completed in {self.iteration} iteration(s).")
                if self.iteration > 1:
                    await clear_test_case_cache(self.apiChatRequestId)
                return fixed_llm_response
            
            validated_response = await self.get_fixed_query_from_llm(fixed_llm_response)
            print(f"Validated response: {validated_response}")
            if isinstance(validated_response, ErrorInfo):
                result = InvalidResponse(
                    taskStatus="TERMINATED",
                    result=validated_response.response,
                    usage=token_count
                )
                return result
            
            if validated_response.operationType == "SUBSCRIPTION":
                validated_response.query = f"SUBSCRIPTION: Sorry, I cannot invoke subscriptions for you. Here is the subscription query: {validated_response.query}"
            
            return GraphQLExecutionResult(
                method="POST",
                path="/",
                inputs=RequestBody(
                    requestBody=ToolComponent(query=validated_response.query)
                )
            )
            
        return ErrorInfo(response="Max iterations reached without a valid response.")
    
    async def reason(self) -> Union[GraphqlToolResponse, ErrorInfo]:
        """Determines the next operation unless the task is completed."""
        if self.isCompleted:
            return ErrorInfo(response="Task is already completed. No more reasoning is needed.")
        
        return await self.selectNextOperation()
    
    async def selectNextOperation(self) -> Union[GraphqlToolResponse, ErrorInfo]:
        """Determines the next GraphQL operation to execute based on schema, user query, 
        execution history, and context."""
        prompt = await get_next_tool_prediction_prompt(self.sdl, self.progress)
        response, tokens = await generate_text_with_llm(prompt)
        token_count.prompt_tokens += tokens["prompt_tokens"]
        token_count.completion_tokens += tokens["completion_tokens"]
        token_count.total_tokens += tokens["total_tokens"]
        return response
    
    async def fix_response(self, response: json) -> Union[TestCompletionResponse, GraphqlToolResponse,  
                                                          InvalidResponse, ErrorInfo]:
        """Processes and validates the response, determining whether it's a completed, 
        invalid, or valid GraphQL function call."""
        response = json.loads(response)
        if response["operationType"] == "COMPLETED":
            self.isCompleted = True
            return TestCompletionResponse(
                taskStatus=response["operationType"], 
                result=response["query"], 
                usage=token_count
            )
        
        if response["operationType"] == "TERMINATED":
            return InvalidResponse(
                taskStatus="TERMINATED", 
                result=response["query"], 
                usage=token_count
            )
        
        if response["operationType"] not in {"QUERY", "MUTATION", "SUBSCRIPTION"}:
            return InvalidResponse(
                taskStatus="TERMINATED", 
                result="An invalid query was generated by LLM.", 
                usage=token_count
            )

        parsed_response = await self.parse_graphql_llm_response(GraphqlToolResponse(**response))
        return parsed_response
    
    async def parse_graphql_llm_response(self, llm_response: GraphqlToolResponse) -> Union[GraphqlToolResponse, 
                                                                            InvalidResponse, ErrorInfo]:
        """Validates and parses the LLM response for GraphQL execution."""
        query = llm_response.query
        if not query:
            return InvalidResponse(
                taskStatus="TERMINATED", 
                result="Empty query in LLM response.", 
                usage=token_count
            )
        return llm_response
    
    async def is_valid_against_schema(self, schema: str, query: str) -> Union[bool, ErrorInfo]:
        """Validates the generated GraphQL query against the provided schema."""
        try:
            schema = build_schema(schema)
            parsed_query = parse(query)
            errors = validate(schema, parsed_query)
            if errors:
                for err in errors:
                    print(f"Validation error: {err}")
                return errors
            return True
        except Exception as e:
            return ErrorInfo(response=f"Exception during schema validation: {e}")

    async def get_fixed_query_from_llm(self, llm_response: GraphqlToolResponse) -> Union[GraphqlToolResponse, ErrorInfo]:
        """Corrects the GraphQL query using the LLM based on the provided schema and error message."""
        schema = self.sdl
        query = llm_response.query
        max_retries = 2
        attempt = 1

        while attempt <= max_retries:
            schema_validation_result = await self.is_valid_against_schema(schema, query)

            if schema_validation_result is True:
                return GraphqlToolResponse(operationType=llm_response.operationType, query=query)
            if isinstance(schema_validation_result, ErrorInfo):
                return schema_validation_result  

            error_message = '\n'.join(str(e) for e in schema_validation_result)
            prompt = await get_query_correction_prompt(schema, query, error_message)

            message_content, tokens = await generate_text_with_llm(prompt)
            token_count.prompt_tokens += tokens["prompt_tokens"]
            token_count.completion_tokens += tokens["completion_tokens"]
            token_count.total_tokens += tokens["total_tokens"]
            if isinstance(message_content, ErrorInfo):
                return message_content

            if isinstance(message_content, str) and "Corrected_query:" in message_content:
                corrected_query = message_content.split("Corrected_query:")[1].strip()
            elif isinstance(message_content, dict) and "Corrected_query" in message_content:
                corrected_query = message_content["Corrected_query"]
            else:
                return ErrorInfo(response="Invalid response format from LLM.")

            query = corrected_query
            attempt += 1

        return ErrorInfo(response="Failed to correct query after multiple attempts.")

async def generate_text_with_llm(prompt: str):
    """Calls the Azure OpenAI GPT model to generate a response based on the given prompt."""
    try:
        response = llm_client.chat.completions.create(
            model=os.getenv("AZURE_CHAT_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": "You are an INTELLIGENT GRAPHQL QUERY GENERATOR and CORRECTOR."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content, {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    except Exception as e:
        return ErrorInfo(response=f"Error calling LLM: {str(e)}"), token_count
