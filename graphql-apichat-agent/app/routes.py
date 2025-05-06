from fastapi import APIRouter, HTTPException, Header, Request
from typing import Union
from app.models import *
from app.services import process_graphql_sdl, create_chat_agent
from app.cache import redis_client

router = APIRouter()

@router.post("/prepare", response_model=Union[GraphQLTestPreparationResponse, ErrorInfo])
async def sdl_prepare( 
    payload: Request,
    apiChatRequestId: str = Header(...)
):
    """Handles SDL preparation requests."""
    print("SdlPrepare called")
    payload = await payload.json()
    processed_sdl = process_graphql_sdl(payload)
    if isinstance(processed_sdl, ErrorInfo):
        return processed_sdl
    return GraphQLTestPreparationResponse(**processed_sdl.dict())

@router.post("/chat", response_model=Union[GraphQLTestExecutionResponse, GraphQLTestCompletionResponse, InvalidResponse, ErrorInfo])
async def graphql_chat(
    response: Request,
    apiChatRequestId: str = Header(...)
):
    """Handles GraphQL chat requests, either initializing or continuing execution."""
    print("GraphQLChat called")
    payload = await response.json()
    response = await create_chat_agent(payload, apiChatRequestId)
    return response

@router.get("/health", status_code=200)
async def health_check():
    """Handles health check requests."""
    try:
        if not redis_client.ping():
            raise Exception("Redis ping failed.")
    except Exception as e:
        print(f"Liveness probe failed: {e}")
        raise HTTPException(status_code=500, detail="Liveness probe failed.")
    return {"status": "ok"}
     