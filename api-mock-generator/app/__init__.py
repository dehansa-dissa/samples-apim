from fastapi import FastAPI
from config.settings import Config
from app.routes import api_router

def create_app():
    app = FastAPI()
    # If Config has relevant settings, they can be applied here as needed
    app.include_router(api_router)
    return app
