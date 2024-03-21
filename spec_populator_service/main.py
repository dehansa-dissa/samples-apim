from milvus import *
from fastapi import FastAPI
from utils import *
from typing import Dict, Any
import asyncio
from functools import partial

embed = get_emb_model()
source = os.getenv("SOURCE_PLATFORM")

app = FastAPI()

@app.post("/add_vector/{uuid}")
async def add_vector(uuid : str, req: Dict[str, Any]):

    # Introspect token and get vector or user
    collection = "common_space"

    if source == "apim":
        api_type = req["api_type"]
        match api_type:
            case "REST":
                record = await pre_process_openapi(req["api_spec"])
            case "GRAPHQL":
                record = await pre_process_graphql_sdl(req["sdl_schema"])
            case "ASYNC":
                record = await pre_process_asyncapi_def(req["async_spec"])
        
        # Add API type, available subscription plans
        record["api_type"] = api_type
        # The actual version is used instead of what is in the Spec,
        # since we know this is the truth, and the spec version can be outdated
        record["version"] = req["version"]
        record["api_name"] = req["api_name"]
        record["apim_description"] = req["description"]

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, partial(upsert_vector_for_onprem, embed, record, collection, uuid, api_type, req["api_name"], req["tenant_domain"]))
    elif source == "choreo":
        record = await pre_process_openapi(req["api_spec"])
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None,partial(upsert_vector_for_choreo, embed, record, collection, uuid))

    return {"message": response}

@app.delete("/remove_vector/{uuid}")
async def remove_vector(uuid : str):
    
    collection = "common_space"

    if source == "apim":
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, partial(delete_vector_for_onprem, [uuid], collection))

    return {"message": response}
