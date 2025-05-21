from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import HTTPException
from app.routes import api_router
from app.utils.logger import logger
import traceback

app = FastAPI()
app.include_router(api_router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}\nTraceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": "Internal server error",
                "details": str(exc)
            }
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log only warnings for client errors (4xx), errors for server errors (5xx)
    if 400 <= exc.status_code < 500:
        logger.warning(f"HTTP exception: {exc.detail}")
    else:
        logger.error(f"HTTP exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail if isinstance(exc.detail, str) else exc.detail.get("message", ""),
            }
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "RequestValidationError",
                "message": "Validation error",
                "details": exc.errors()
            }
        },
    )
