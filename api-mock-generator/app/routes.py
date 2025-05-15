from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.services.ai_operations import generate_mock_scripts, modify_method
from app.utils.logger import logger

api_router = APIRouter()

class GenerateMockConfig(BaseModel):
    instructions: Optional[str] = None
    usePreviousScripts: bool = False

class ConfigModify(BaseModel):
    path: str
    method: str
    defaultScript: bool = False

class ModifyConfig(BaseModel):
    instructions: str = 'Generate mock scripts for the specified endpoint'
    script: str = 'No Script'
    modify: ConfigModify


class GenerateMocksRequest(BaseModel):
    swagger: str
    config: Optional["GenerateMockConfig"] = None

class ModifyMethodRequest(BaseModel):
    swagger: str
    config: ModifyConfig

# Updated endpoints with request body models
@api_router.post('/generate-mocks', status_code=201)
async def generate_mock_scripts_endpoint(payload: GenerateMocksRequest):
    """
    Endpoint to generate mock scripts based on an OpenAPI specification.

    Request:
        payload (GenerateMocksRequest): Contains the OpenAPI spec as a string and optional configuration.

    Response:
        JSONResponse: Returns generated mock scripts as JSON with HTTP status 201.

    Raises:
        HTTPException: If the OpenAPI spec is missing in the request payload.
    """
    if not payload.swagger:
        logger.warning("Open API Spec is required for generate-mocks endpoint")
        raise HTTPException(status_code=400, detail={
            "type": "BadRequest",
            "message": "Open API Spec is required"
        })

    mock_scripts = generate_mock_scripts(payload.swagger, payload.config.model_dump() if payload.config else {})
    # Removed info log to reduce noise
    return JSONResponse(content=mock_scripts, status_code=201)

@api_router.post('/modify-method', status_code=201)
async def modify_method_endpoint(payload: ModifyMethodRequest):
    """
    Endpoint to modify a method's mock script based on instructions and OpenAPI spec.

    Request:
        payload (ModifyMethodRequest): Contains the OpenAPI spec, modification config including path, method, script, and instructions.

    Response:
        JSONResponse: Returns the modified mock script as JSON with HTTP status 201.

    Raises:
        HTTPException: If required fields are missing in the request payload.
    """
    if not (payload.swagger and payload.config and payload.config.modify and payload.config.script and payload.config.instructions):
        logger.warning("Missing required fields for modify-method endpoint")
        raise HTTPException(status_code=400, detail={
            "type": "BadRequest",
            "message": "Open API Spec, path, method, script, and instructions are required"
        })

    modify_config = payload.config.modify
    mock_script = modify_method(
        payload.swagger,
        payload.config.script,
        modify_config.path,
        modify_config.method,
        payload.config.instructions,
        modify_config.defaultScript
    )
    return JSONResponse(content=mock_script, status_code=201)
