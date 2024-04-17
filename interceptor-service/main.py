from fastapi import FastAPI, Header, HTTPException
from aiocache import cached, SimpleMemoryCache, caches
import json
import os
from pydantic import BaseModel
from fastapi import status
import aiohttp

api_chat_endpoint = os.getenv("API_CHAT_ENDPOINT")
marketplace_chat_endpoint = os.getenv("MARKETPLACE_CHAT_ENDPOINT")
api_publisher_endpoint = os.getenv("API_PUBLISHER_ENDPOINT")
api_chat_access_token = os.getenv("API_CHAT_ENDPOINT_ACCESS_TOKEN")
introspect_endpoint = os.getenv("INTROSPECTION_ENDPOINT")
marketplace_chat_access_token = os.getenv("MARKETPLACE_CHAT_ENDPOINT_TOKEN")
api_publisher_endpoint_access_token = os.getenv("API_PUBLISHER_ENDPOINT_ACCESS_TOKEN")

cache = SimpleMemoryCache()

class Message(BaseModel):
    role: str
    content: str


class History(BaseModel):
    history: list


class MarketplaceChatRequest(BaseModel):
    query: str
    history: list
    tenant_domain: str


class apis(BaseModel):
    apiId: str
    apiName: str
    version: str


class MarketplaceChatResponse(BaseModel):
    response: str
    apis: list[apis]


class RemoveRequest(BaseModel):
    uuid: str
    tenant_domain: str


class ApiCountResponse(BaseModel):
    count: int
    limit: int

caches.set_config({
    'default': {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.StringSerializer"
        }
    }
})

app = FastAPI()

@cached(ttl=60, key=lambda on_prem_key: f"introspection:{on_prem_key}")
async def introspect(on_prem_key):
    async with aiohttp.ClientSession() as session:
        async with session.post(introspect_endpoint, json={"key": on_prem_key}) as response:
            if response.status == 200:
                res_json = await response.json()
                return [res_json["orgUuid"], res_json["handle"], res_json["status"]]
            else:
                responseMessage = await response.text()
                if "invalid key" in responseMessage or "expired" in responseMessage:
                    raise HTTPException(status_code=401, detail="Provided key is invalid or expired")
                else:
                    raise HTTPException(status_code=response.status, detail=responseMessage)


@cached(ttl=60, key=lambda orgID: f"api_count:{orgID}")
async def fetch_api_count(orgID):
    async with aiohttp.ClientSession() as session:
        async with session.get(api_publisher_endpoint + "/api_count", params={'orgID': orgID}) as response:
            if response.status == 200:
                count = (await response.json())['count']
                return count
            else:
                raise HTTPException(status_code=response.status, detail=await response.text())


@app.post("/ai/api-chat/prepare", status_code=status.HTTP_201_CREATED)
async def prepare(req: dict, apiChatRequestId: str = Header(None), API_KEY: str = Header(None)):
    [orgID, handle, status] = await introspect(API_KEY)
    if status == "ACTIVE":
        async with aiohttp.ClientSession() as session:
            headers = {"apiChatRequestId": apiChatRequestId, "Authorization": f"Bearer {api_chat_access_token}"}
            async with session.post(api_chat_endpoint + "/prepare", headers=headers, json=req) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.post("/ai/api-chat/execute", status_code=status.HTTP_201_CREATED)
async def execute(req: dict, apiChatRequestId: str = Header(None), API_KEY: str = Header(None)):
    [orgID, handle, status] = await introspect(API_KEY)
    if status == "ACTIVE":
        async with aiohttp.ClientSession() as session:
            headers = {"apiChatRequestId": apiChatRequestId, "Authorization": f"Bearer {api_chat_access_token}"}
            async with session.post(api_chat_endpoint + "/chat", headers=headers, json=req) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.post("/ai/marketplace-assistant/chat", status_code=status.HTTP_201_CREATED)
async def chat(req: dict, API_KEY: str = Header(None)):
    [orgID, handle, status] = await introspect(API_KEY)

    if status == "ACTIVE":
        history_string = req["history"]
        data_list = json.loads(history_string)
        objects_list = []

        for item in data_list:
            role = item['role']
            content = item['content']
            obj = {"role": role, "content": content}
            objects_list.append(obj)

        payload = {
            "query": req['query'],
            "history": objects_list,
            "tenant_domain": req['tenant_domain']
        }

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {marketplace_chat_access_token}"}
            async with session.post(marketplace_chat_endpoint + "/marketplace-assistant", params={'keyID': handle},
                                    json=payload, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.post("/ai/spec-populator/publish-api", status_code=status.HTTP_201_CREATED)
async def publish_api(req: dict, API_KEY: str = Header(None)):
    [orgID, handle, status] = await introspect(API_KEY)

    if status == "ACTIVE":
        count = await fetch_api_count(orgID)
        if count <= 1000:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_publisher_endpoint_access_token}"}
                async with session.post(api_publisher_endpoint + '/add_vector/' + req["uuid"], json=req,
                                        params={'orgID': orgID, 'keyID': handle}, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HTTPException(status_code=response.status, detail=await response.text())
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.delete("/ai/spec-populator/remove-api/{uuid}")
async def remove_api(uuid: str, API_KEY: str = Header(None)):
    [orgID, handle, status] = await introspect(API_KEY)

    if status == "ACTIVE":
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {api_publisher_endpoint_access_token}"}
            async with session.delete(api_publisher_endpoint + "/remove_vector/" + uuid, params={'keyID': handle},
                                      headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.get("/ai/spec-populator/api-count")
async def api_count(API_KEY: str = Header(None)):
    [orgID, handle, status] = await introspect(API_KEY)
    if status == "ACTIVE":
        count = await fetch_api_count(orgID)
        return {"count": count, "limit": 1000}
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.post("/ai/spec-populator/bulk-upload")
async def upload_bulk_apis(req: dict, API_KEY: str = Header(None)):
    [orgID, handle, status] = await introspect(API_KEY)

    if status == "ACTIVE":
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {api_publisher_endpoint_access_token}"}
            async with session.post(api_publisher_endpoint + '/bulk_add_vector', json=req,
                                    params={'orgID': handle, 'keyID': handle}, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")
