from fastapi import FastAPI, Header, HTTPException
from aiocache import cached, SimpleMemoryCache, caches
import redis.asyncio as redis
from redis.exceptions import (
   ConnectionError,
   TimeoutError
)
import asyncio
from contextlib import asynccontextmanager
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
redis_uri = os.getenv("REDIS_URI")
do_throttle = os.getenv("DO_THROTTLE", "true")

def convert_to_int(s):
    try:
        return int(s)
    except ValueError:
        raise ValueError("Could not convert '{}' to an integer".format(s))

openai_token_count_per_org = convert_to_int(os.getenv("OPENAI_TOKEN_COUNT_PER_ORG", "1000000"))

cache = SimpleMemoryCache()

expire_time = 30 * 24 * 60 * 60 # Number of seconds for 30 days

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global lua_script_sha, redis_client
    try:
        redis_client = redis.from_url(
            redis_uri, retry_on_error=[ConnectionError, TimeoutError] # Delay between retry attempts (1 second)
        )
        lua_script_sha = None
        await test_connection()
        lua_script_sha = await redis_client.script_load(lua_script)
        yield
    except Exception as e:
        print(f"Error initializing Redis connection: {e}")
        raise Exception("Error initializing Redis connection")
    finally:
        await redis_client.aclose()


lua_script = """
    local json_value = redis.call('GET', KEYS[1])
    local data
    if json_value then
        data = cjson.decode(json_value)
    else
        data = {
            prompt_tokens = 0,
            completion_tokens = 0,
            total_tokens = 0
        }
    end
    data["prompt_tokens"] = data["prompt_tokens"] + ARGV[2]
    data["completion_tokens"] = data["completion_tokens"] + ARGV[3]
    data["total_tokens"] = data["total_tokens"] + ARGV[4]
    
    if not json_value then
        redis.call('SET', KEYS[1], cjson.encode(data), 'EX', ARGV[1])
    else
        redis.call('SET', KEYS[1], cjson.encode(data), 'KEEPTTL')
    end
    return cjson.encode(data)
    """


app = FastAPI(
    title="WSO2 APIM AI Interceptor",
    description="Backend for WSO2 APIM AI Features",
    version="0.1.0",
    license_info={"name": "Apache 2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
    lifespan=lifespan
)


async def update_redis_cache(key, increment_value):
    global lua_script_sha
    result = await redis_client.evalsha(lua_script_sha, 1, key, expire_time, *increment_value)
    return


async def test_connection():
    try:
        await redis_client.ping()
        await redis_client.set('test', 'Hello world!')
        res = await redis_client.get('test')
        print(res)
        await redis_client.delete('test')
    except Exception as e:
        raise Exception("Error testing Redis connection")


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


async def throttle(orgID):
    cache_key = "org:" + orgID + ":token_count"
    current_counts_json = await redis_client.get(cache_key)
    if current_counts_json is not None:
        current_counts = json.loads(current_counts_json)
        total_count = int(current_counts["total_tokens"])
        if total_count >= openai_token_count_per_org:
            raise HTTPException(status_code=429, detail="Maximum token limit reached")

@cached(ttl=60, key=lambda orgID: f"api_count:{orgID}")
async def fetch_api_count(orgID):
    async with aiohttp.ClientSession() as session:
        async with session.get(api_publisher_endpoint + "/api_count", params={'orgID': orgID}) as response:
            if response.status == 200:
                count = (await response.json())['count']
                return count
            else:
                raise HTTPException(status_code=response.status, detail=await response.text())

async def fetch_api_count_for_upload(orgID):
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
    if do_throttle == "true":
        await throttle(orgID)
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
                    response_json = await response.json()
                    if 'usage' in response_json:
                        usage = response_json.pop('usage', None)
                        cache_key = "org:" + orgID + ":token_count"
                        asyncio.create_task(update_redis_cache(cache_key, [usage["prompt_tokens"], usage["completion_tokens"], usage["total_tokens"]]))
                    return response_json
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
            raise HTTPException(status_code=429, detail="You have reached your api limit")
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
        count = await fetch_api_count_for_upload(orgID)
        if count < 1000:
            req["apis"] = req["apis"][:1000-count]
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_publisher_endpoint_access_token}"}
                async with session.post(api_publisher_endpoint + '/bulk_add_vector', json=req,
                                        params={'orgID': handle, 'keyID': handle}, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HTTPException(status_code=response.status, detail=await response.text())
        else:
            raise HTTPException(status_code=429, detail="You have reached your api limit")
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")

@app.delete("/ai/spec-populator/bulk-remove")
async def remove_bulk_apis(API_KEY: str = Header(None), TENANT_DOMAIN: str = Header(None)):
    [orgID, handle, status] = await introspect(API_KEY)

    if status == "ACTIVE":
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {api_publisher_endpoint_access_token}"}
            async with session.delete(api_publisher_endpoint + '/bulk_remove_vector',
                                    params={'orgID': handle, 'keyID': handle, "tenantDomain": TENANT_DOMAIN}, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise HTTPException(status_code=response.status, detail=await response.text())
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")

