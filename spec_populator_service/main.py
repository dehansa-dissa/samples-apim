from milvus import *
from fastapi import FastAPI
from utils import *
from typing import Dict, Any, Optional
import asyncio
import uvicorn
from functools import partial
import json

embed = get_emb_model()
source = os.getenv("SOURCE_PLATFORM", "apim")

app = FastAPI()


@app.post("/add_vector/{uuid}")
async def add_vector(uuid: str, req: Dict[str, Any], orgID: str, keyID: Optional[str] = None):
    # TODO: Handle 400 error if request info not sufficient (eg: no KeyID)
    if source == "apim":
        api_type = req["api_type"]
        if api_type == "APIPRODUCT":
            api_type = "HTTP"
            record = await pre_process_openapi(req["api_spec"])
        elif api_type == "REST" or api_type == "HTTP" or api_type == "SOAP" or api_type == "SOAPTOREST" :
            record = await pre_process_openapi(req["api_spec"])
        elif api_type == "GRAPHQL":
            record = await pre_process_graphql_sdl(req["sdl_schema"])
        elif api_type == "ASYNC" or api_type == "WS" or api_type == "WEBSUB" or api_type == "SSE" or api_type == "WEBHOOK":
            record = await pre_process_asyncapi_def(req["async_spec"])

        # Add available subscription plans
        record["apim_description"] = req["description"]
        api = API(
            id=uuid,
            # The actual version is used instead of what is in the Spec,
            # since we know this is the truth, and the spec version can be outdated
            version=req["version"],
            type=api_type,
            name=req["api_name"],
            spec=record
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, partial(upsert_vector_for_onprem, embed, orgID, keyID, api,
                                                            req["tenant_domain"]))
    elif source == "choreo":
        # TODO: Implement for APIs other that REST
        record = await pre_process_openapi(req["api_spec"])
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
        response = await loop.run_in_executor(None,partial(upsert_vector_for_choreo, embed, orgID, api))

    return {"message": response}


@app.delete("/remove_vector/{uuid}")
async def remove_vector(uuid: str, keyID: Optional[str] = None, orgID: Optional[str] = None):
    loop = asyncio.get_event_loop()
    if source == "apim":
        response = await loop.run_in_executor(None, partial(delete_vector, [uuid], keyID))
    elif source == "choreo":
        response = await loop.run_in_executor(None, partial(delete_vector, [uuid], orgID))

    return {"message": response}


@app.post("/bulk_add_vector")
async def bulk_add_vector(req: Dict[str, Any], orgID: str, keyID: str):

    api_details_list = req["apis"]

    api_list = []
    
    if source == "apim":

        for api_details in api_details_list:

            api_type = api_details["api_type"]
            if api_type == "REST":
                record = await pre_process_openapi(api_details["api_spec"])
            elif api_type == "GRAPHQL":
                record = await pre_process_graphql_sdl(api_details["sdl_schema"])
            elif api_type == "ASYNC":
                record = await pre_process_asyncapi_def(api_details["async_spec"])
            
            # Add available subscription plans
            record["apim_description"] = api_details["description"]
            api = API(
                id=api_details["uuid"],
                # The actual version is used instead of what is in the Spec,
                # since we know this is the truth, and the spec version can be outdated
                version=api_details["version"],
                type=api_details["api_type"],
                name=api_details["api_name"],
                spec=record
            )

            res = embed.embed_query(str(api.__dict__))
            payload={
                    "page_content": str(api.spec),
                    "metadata": {
                        "id": api.id,
                        "api_name": api.name,
                        "api_version": api.version,
                        "api_type": api.type
                    },
                    "id": keyID + api.id,
                    "vector": res,
                    "api_type": api.type,
                    "org_id": orgID,
                    "key_id": keyID,
                    "tenant_domain": api_details["tenant_domain"]
                }
            api_list.append(payload)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, partial(upsert_bulk_vector_for_onprem, api_list))


        # elif source == "choreo":
        #     record = await pre_process_openapi(api_details["api_spec"])
        #     loop = asyncio.get_event_loop()
        #     response = await loop.run_in_executor(None,partial(upsert_vector_for_choreo, embed, record, orgID, api_details["uuid"]))

        # return {"message": response}

@app.get("/api_count")
async def get_api_count(orgID: str):
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, partial(get_vector_count_for_onprem, orgID))
    print(response[0]["count(*)"])
    return {"count": response[0]["count(*)"]}
