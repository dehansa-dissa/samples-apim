from pydantic import BaseModel
from typing import Literal, Dict
from enum import Enum

class TaskStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    TERMINATED = "TERMINATED"
    COMPLETED = "COMPLETED"

class ToolType(str, Enum):
    QUERY = "QUERY"
    MUTATION = "MUTATION"
    SUBSCRIPTION = "SUBSCRIPTION"

APICHAT_RETRY_COUNT = 3

class SdlResponse(BaseModel):
    sdl: str

class GraphQLTestPreparationRequest(BaseModel):
    GRAPHQL_SCHEMA: str

class SampleQueryFormat(BaseModel):
    scenario: str
    query: str

class TokenCounts(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class GraphQLTestPreparationResponse(BaseModel):
    apiSpec: SdlResponse
    queries: list[SampleQueryFormat]
    usage: TokenCounts

class ToolComponent(BaseModel):
    query: str

class RequestBody(BaseModel):
    requestBody: ToolComponent

class GraphqlExecutionResult(BaseModel):
    method: Literal["POST"]
    path: str="/"
    inputs: RequestBody

class GraphQLTestExecutionResponse(BaseModel):
    taskStatus: Literal["IN_PROGRESS", "TERMINATED"]
    resource: GraphqlExecutionResult
    usage: TokenCounts

class GraphQLTestCompletionResponse(BaseModel):
    taskStatus: Literal["COMPLETED"]
    result: str
    usage: TokenCounts

class SdlCacheRecord(BaseModel):
    apiSpec: SdlResponse
    queries: list[SampleQueryFormat]

class GraphQLTestInitializationRequest(BaseModel):
    command: str
    apiSpec: None
    sdl: dict

class PreviousResponse(BaseModel):
    code: int
    path: str
    headers: Dict[str, str]
    body: str

class GraphQLTestExecutionRequest(BaseModel):
    response: PreviousResponse

class CacheStep(BaseModel):
    query: str
    code: int
    response: str

class GraphQLCacheRecord(BaseModel):
    sdl: str
    command: str
    iteration: int
    executionHistory: list[CacheStep]
    previousResponse: str

class GraphqlToolResponse(BaseModel):
    operationType: ToolType
    query: str 

class TestStepResult(BaseModel):
    result: GraphqlExecutionResult
    usage: TokenCounts

class GraphQLTestInvalidResponse(BaseModel):
    taskStatus: Literal["TERMINATED"]
    query: str
    
class ErrorInfo(BaseModel):
    response: str

class InvalidResponse(BaseModel):
    taskStatus: Literal["TERMINATED"]
    result: str
    usage: TokenCounts


