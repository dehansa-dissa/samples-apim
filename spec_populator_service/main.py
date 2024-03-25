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
async def add_vector(uuid: str, req: Dict[str, Any], orgID: str):

    if source == "apim":
        api_type = req["api_type"]
        if api_type == "REST":
            record = await pre_process_openapi(req["api_spec"])
        elif api_type == "GRAPHQL":
            record = await pre_process_graphql_sdl(req["sdl_schema"])
        elif api_type == "ASYNC":
            record = await pre_process_asyncapi_def(req["async_spec"])
        
        # Add available subscription plans
        record["apim_description"] = req["description"]
        api = API(
            id=uuid,
            # The actual version is used instead of what is in the Spec,
            # since we know this is the truth, and the spec version can be outdated
            version=req["version"],
            type=req["api_type"],
            name=req["api_name"],
            spec=record
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, partial(upsert_vector_for_onprem, embed, orgID, api, req["tenant_domain"]))
    elif source == "choreo":
        record = await pre_process_openapi(req["api_spec"])
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None,partial(upsert_vector_for_choreo, embed, record, orgID, uuid))

    return {"message": response}

@app.delete("/remove_vector/{uuid}")
async def remove_vector(uuid : str, orgID: str):

    if source == "apim":
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, partial(delete_vector_for_onprem, [uuid], orgID))

    return {"message": response}
