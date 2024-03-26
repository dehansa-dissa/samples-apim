from fastapi import FastAPI, Header, HTTPException
import json
import os
from pydantic import BaseModel
import requests
from fastapi import status

api_chat_endpoint = os.getenv("API_CHAT_ENDPOINT")
marketplace_chat_endpoint = os.getenv("MARKETPLACE_CHAT_ENDPOINT")
api_publisher_endpoint = os.getenv("API_PUBLISHER_ENDPOINT")
api_chat_access_token = os.getenv("API_CHAT_ENDPOINT_ACCESS_TOKEN")
introspect_endpoint = os.getenv("INTROSPECTION_ENDPOINT")
marketplace_chat_access_token = os.getenv("MARKETPLACE_CHAT_ENDPOINT_TOKEN")
api_publisher_endpoint_access_token = os.getenv("API_PUBLISHER_ENDPOINT_ACCESS_TOKEN")

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


org_map = {
    "orgToken1": ["orgID1", "ACTIVE"],
    "orgToken2": ["orgID2", "ACTIVE"],
    "orgToken3": ["orgID3", "EXPIRED"],
}

app = FastAPI()

def introspect(on_prem_key):
        
    if on_prem_key in org_map.keys():
        return org_map[on_prem_key]
    else:
        response =  requests.post(introspect_endpoint, json={"key": on_prem_key})
        
        if response.status_code == 200:
            res = [response.json()["orgUuid"], response.json()["status"]]
            org_map[on_prem_key] = res
            return res
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.post("/ai/api-chat/prepare", status_code=status.HTTP_201_CREATED)
async def prepare(req: dict, x_request_id: str = Header(None), API_KEY: str = Header(None)):
    
    [orgID, status] = introspect(API_KEY)
    if status == "ACTIVE":
        response =  requests.post(api_chat_endpoint + "/prepare", headers={"apiChatRequestId": x_request_id, "Authorization": f"Bearer {api_chat_access_token}"}, json=req)
        
        if response.status_code == 201:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.post("/ai/api-chat/execute", status_code=status.HTTP_201_CREATED)
async def execute(req: dict , x_request_id: str = Header(None), API_KEY: str = Header(None)):

    [orgID, status] = introspect(API_KEY)
    if status == "ACTIVE":
        response =  requests.post(api_chat_endpoint + "/chat", headers={"apiChatRequestId": x_request_id, "Authorization": f"Bearer {api_chat_access_token}"}, json=req)
        
        if response.status_code == 201:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.post("/ai/marketplace-assistant/chat", status_code=status.HTTP_201_CREATED)
async def chat(req: dict, API_KEY: str = Header(None)):

    [orgID, status] = introspect(API_KEY)

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
               
        response =  requests.post(marketplace_chat_endpoint + "/marketplace-assistant", params={'orgID':  orgID}, json=payload ,headers={"Authorization": f"Bearer {marketplace_chat_access_token}"})

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    else:
            raise HTTPException(status_code=401, detail="Your key has expired")


@app.post("/ai/spec-populator/publish-api", status_code=status.HTTP_201_CREATED)
async def publish_api(req: dict, API_KEY: str = Header(None)):

    [orgID, status] = introspect(API_KEY)

    if status == "ACTIVE":

        response =  requests.post(api_publisher_endpoint + '/add_vector/' + req["uuid"], json=req, params={'orgID':  orgID}, headers={"Authorization": f"Bearer {api_publisher_endpoint_access_token}"})

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")


@app.delete("/ai/spec-populator/remove-api/{uuid}")
async def remove_api(uuid : str, API_KEY: str = Header(None)):
    
    [orgID, status] = introspect(API_KEY)

    if status == "ACTIVE":

        response =  requests.delete(api_publisher_endpoint + "/remove_vector/" + uuid, params={'orgID':  orgID}, headers={"Authorization": f"Bearer {api_publisher_endpoint_access_token}"})

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")

@app.get("/ai/spec-populator/api-count")
async def api_count(API_KEY: str = Header(None)):

    [orgID, status] = introspect(API_KEY)
    if status == "ACTIVE":
        count_response = {"count" : 100, "limit": 1000}
        return count_response
    else:
        raise HTTPException(status_code=401, detail="Your key has expired")
