import json
from graphql import build_schema, validate, parse
from openai import AzureOpenAI
import os
from typing import Union
from app.models import *
from app.cache import clear_test_case_cache
from dotenv import load_dotenv

load_dotenv()

llm_client = AzureOpenAI(
    api_key=os.getenv("OPENAI_KEY"),  
    api_version=os.getenv("AZURE_CHAT_VERSION"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT")
)

class GraphQLChatAgent:
    def __init__(self, apiChatRequestId: str, sdl: json, command: str, iteration: int, executionHistory: list[CacheStep]):
        self.apiChatRequestId = apiChatRequestId
        self.sdl = sdl
        self.command = command
        self.iteration = iteration
        self.executionHistory = executionHistory
        self.isCompleted = False

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
            "context": getGraphQLApiChatContext()
        }
        print("Agent Initialization Completed.")

    async def execute(self) -> Union[TestStepResult, GraphQLTestCompletionResponse, InvalidResponse, ErrorInfo]:
        """Execute the GraphQL API chat agent."""
        for _ in range(APICHAT_RETRY_COUNT):
            llm_response = self.reason()  

            if isinstance(llm_response, ErrorInfo):
                return ErrorInfo(llm_response)

            fixed_llm_response = self.fix_response(llm_response) 
            if isinstance(fixed_llm_response, ErrorInfo):
                return fixed_llm_response
            if isinstance(fixed_llm_response, GraphQLTestCompletionResponse):   
                print(f"Task completed in {self.iteration} iteration(s).")
                if self.iteration > 1:
                    clear_test_case_cache(self.apiChatRequestId)
                return GraphQLTestCompletionResponse(taskStatus=fixed_llm_response.taskStatus, result=fixed_llm_response.result)
            
            if isinstance(fixed_llm_response, GraphQLTestInvalidResponse):
                result = InvalidResponse(
                    taskStatus="TERMINATED",
                    result=fixed_llm_response.query
                )
                return result
            
            validated_response = self.get_fixed_query_from_llm(fixed_llm_response)
            if isinstance(validated_response, ErrorInfo):
                result = InvalidResponse(
                    taskStatus="TERMINATED",
                    result=validated_response.query
                )
                return result
            result = GraphqlExecutionResult(
                method="POST",
                path="/",
                inputs=RequestBody(
                    requestBody=ToolComponent(query=validated_response.query)
                )
            )
            return TestStepResult(
                result=result
            )
        return ErrorInfo(response="Max iterations reached without a valid response.")
    
    def reason(self) -> Union[GraphqlToolResponse, ErrorInfo]:
        """Determines the next operation unless the task is completed."""
        if self.isCompleted:
            return ErrorInfo(response="Task is already completed. No more reasoning is needed.")
        
        return self.selectNextOperation()
    
    def selectNextOperation(self) -> Union[GraphqlToolResponse, ErrorInfo]:
        """Determines the next GraphQL operation to execute based on schema, user query, execution history, and context."""
        prompt = f"""
        You are a GraphQL API assistant specializing in GRAPHQL QUERY GENERATION. Your job is to determine the NEXT OPERATION to execute based on:

        - The provided GraphQL schema defining the API capabilities.
        - A natural language user request that needs to be executed via GraphQL.
        - The execution history tracking what has been done so far.
        - The context that helps maintain continuity across turns.

        TASK:

        - Identify whether the next operation is a QUERY, MUTATION, or SUBSCRIPTION, or if the task should be marked as COMPLETED.
        - You must distinguish between:
            1. **Completely Invalid User Commands** — where the overall request is unrelated to the schema.
            2. **Partially Invalid Steps** — where some parts of the request are valid, and others are not supported by the schema.
            3. **Greetings and Introduction Requests** — where the user sends greetings like "hi", "hello", "who are you", "what can you do", etc.

        STRICT INSTRUCTIONS:

        - If the user input is a greeting or introduction request:
            - Respond politely with a short assistant introduction, using:
            {{
                "operationType": "COMPLETED",
                "query": "<Polite greeting or assistant introduction>"
            }}

        - If the **entire user query is invalid** (irrelevant to the schema and not a greeting):
            - First, return an **IN_PROGRESS** response indicating no valid query can be generated.
            - Then return a **COMPLETED** response summarizing the invalid attempt.

        - If only **some steps** in a multi-step task are invalid:
            - Mark those specific steps as FAILED immediately.
            - You MUST NOT reattempt, regenerate, retry, fix, or modify failed steps in any way.
            - Once a step fails, it is considered FINAL and permanently skipped.
            - Any attempt to repair or retry a failed operation is strictly forbidden.
            - Proceed only to the NEXT VALID step without making adjustments.

        - All generated GraphQL operations must:
            - Fully comply with the GraphQL specification.
            - Strictly follow the provided schema.
            - Be guaranteed to pass server-side validation if possible.

        - Carefully review the execution history:
            - If a previous operation has failed (any error, any non-200 status):
                - DO NOT attempt that operation again.
                - Consider it permanently failed.

        RETURN FORMAT:
        Respond STRICTLY as a JSON object WITHOUT markdown formatting or extra characters.

        - If the user input is a greeting or introduction request:
        {{
            "operationType": "COMPLETED",
            "query": "<Polite greeting or short assistant introduction>"
        }}

        - If the full user query is invalid:
        {{
            "operationType": "TERMINATED",
            "query": "I'm unable to generate a valid query based on the given input."
        }}

        - If the task has been completed (e.g., all necessary operations have been executed, or the previous step marked it fully invalid):
        {{
            "operationType": "COMPLETED",
            "query": "<A short summary of what was attempted or completed.>"
        }}

        - If the next valid step exists:
        {{
            "operationType": "<QUERY | MUTATION | SUBSCRIPTION>",
            "query": "<Generated GraphQL operation as a string>"
        }}

        GraphQL Schema: {self.sdl}

        User Query: {self.progress["query"]}

        Execution History: {json.dumps(self.progress["history"])}

        Context: {json.dumps(list(self.progress["context"]))}
        """

        response = generate_text_with_llm(prompt)
        return response
    
    def fix_response(self, response: json) -> Union[GraphQLTestCompletionResponse, GraphQLTestInvalidResponse, ErrorInfo]:
        """Processes and validates the response, determining whether it's a completed, invalid, or valid GraphQL function call."""
        response = json.loads(response)
        if response["operationType"] == "COMPLETED":
            self.is_completed = True
            return GraphQLTestCompletionResponse(taskStatus=response["operationType"], result=response["query"])
        
        if response["operationType"] == "TERMINATED":
            return GraphQLTestInvalidResponse(taskStatus="TERMINATED", query=response["query"])
        
        if response["operationType"] not in {"QUERY", "MUTATION", "SUBSCRIPTION"}:
            return {"taskStatus": "TERMINATED", "error": "An invalid query was generated by LLM."}

        parsed_response = self.parse_graphql_llm_response(GraphqlToolResponse(**response))
        return parsed_response
    
    def parse_graphql_llm_response(self, llm_response: GraphqlToolResponse) -> Union[GraphqlToolResponse, GraphQLTestInvalidResponse, ErrorInfo]:
        """Validates and parses the LLM response for GraphQL execution."""
        query = llm_response.query
        if not query:
            return {"taskStatus": "TERMINATED", "error": "Empty query in LLM response."}
        return llm_response
    
    def is_valid_against_schema(self, schema: str, query: str):
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
        
    def create_prompt(self, schema: str, query: str, error_message: str) -> str:
        prompt_template = '''You are given the GraphQL schema and the query generated based on that schema. And you are given an error message generated by the query validator.
        TASK: Analyse the given query, Error message and the GraphQL schema and correct the errors in the generated query.
        schema : {schema}
        query : {query}
        error_message : {error_message}

        Give the response STRICTLY in the following format.
        Corrected_query: <query>
        '''.format(schema=schema, query=query, error_message=error_message)
        return prompt_template

    def get_fixed_query_from_llm(self, llm_response: GraphqlToolResponse) -> Union[GraphqlToolResponse, ErrorInfo]:
        schema = self.sdl
        query = llm_response.query
        max_retries = 2
        attempt = 1

        while attempt <= max_retries:
            schema_validation_result = self.is_valid_against_schema(schema, query)

            if schema_validation_result is True:
                # Return the successful result
                return GraphqlToolResponse(operationType=llm_response.operationType, query=query)
            if isinstance(schema_validation_result, ErrorInfo):
                return schema_validation_result  

            # Prepare the next prompt using the error message
            error_message = '\n'.join(str(e) for e in schema_validation_result)
            prompt = self.create_prompt(schema, query, error_message)

            message_content = generate_text_with_llm(prompt)
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
 
    def update_progress(self, step: GraphQLTestExecutionResponse):
        self.executionHistory.append(step)

def getGraphQLApiChatContext():
    """Returns the context for the GraphQL API chat agent."""
    return {
        "You are a GraphQL API testing assistant called 'API Chat'. Your capabilities are STRICTLY limited to the following.\n"
            "- Introduce yourself as the API Chat; an Intelligent Agent that can engage with user's GraphQL APIs in natural language.\n"
            "- Answer user's questions by invoking queries, mutations, or subscriptions provided, in order to test those APIs.\n"
            "- You can invoke the functions with the appropriate input parameters to test the APIs. You are NOT allowed to ask for user input to invoke the API.\n"
            "DO NOT respond to questions unrelated to the above capabilities. Respond appropriately to the invalid questions with proper feedback to improve, if needed."
    }

def generate_text_with_llm(prompt: str) -> Union[str, ErrorInfo]:
    """
    Calls the Azure OpenAI GPT model to generate a response based on the given prompt.
    """
    try:
        response = llm_client.chat.completions.create(
            model= "apim-4o-mini",
            messages=[
                {"role": "system", "content": "You are an INTELLIGENT GRAPHQL QUERY GENERATOR and CORRECTOR."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return ErrorInfo(response=f"Error calling LLM: {str(e)}")
    
    