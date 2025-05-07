from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.services.ai_operations import generate_mock_scripts, modify_method

api_router = APIRouter()

@api_router.post('/generate-mocks', status_code=201)
async def generate_mock_scripts_endpoint(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON payload", "details": str(e)})
    
    if not data:
        raise HTTPException(status_code=400, detail={"error": "No JSON payload provided"})

    open_api_spec = data.get('swagger')
    config = data.get('config')
    mock_scripts = generate_mock_scripts(open_api_spec, config)
    return JSONResponse(content=mock_scripts, status_code=201)

@api_router.post('/modify-method', status_code=201)
async def modify_method_endpoint(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON payload", "details": str(e)})

    if not data:
        raise HTTPException(status_code=400, detail={"error": "No JSON payload provided"})

    open_api_spec = data.get('swagger')
    config = data.get('config')
    path = config.get('modify').get('path') if config and config.get('modify') else None
    method = config.get('modify').get('method') if config and config.get('modify') else None
    is_default_script = config.get('modify').get('defaultScript') if config and config.get('modify') else None
    script = config.get('script')
    instructions = config.get('instructions')

    if not (open_api_spec and path and method and script and instructions):
        raise HTTPException(status_code=400, detail={"error": "Open API Spec, path, method, script, and instructions are required"})

    mock_script = modify_method(open_api_spec, script, path, method, instructions, is_default_script)
    return JSONResponse(content=mock_script, status_code=201)
