import redis
import hashlib
import json
import os
from typing import Union
from app.models import ErrorInfo, GraphQLCacheRecord, GraphQLTestPreparationResponse, SdlCacheRecord
from dotenv import load_dotenv

load_dotenv()

# Redis connection setup
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_CONN_TIMEOUT = 2000
REDIS_OPENAPI_KEY_EXPIRATION_TIME = 5000  
REDIS_TESTCASE_KEY_EXPIRATION_TIME = 1000
# CACHE_RETRY_COUNT = 2

redis_client = redis.Redis(
    host=REDIS_HOST,  
    port=6380,  
    password=REDIS_PASSWORD, 
    ssl=True,  
    socket_timeout=REDIS_CONN_TIMEOUT  
)

def get_hashed_string(input_str: str) -> str:
    """Returns the SHA-256 hash of the given string as a hex value."""
    return hashlib.sha256(input_str.encode()).hexdigest()

def retrieve_cached_sdl(sdl_hash: str) -> Union[SdlCacheRecord, None]:
    """Retrieve cached SDL from Redis."""
    key = f"SDL_NAMESPACE:{sdl_hash}"
    cached_sdl = redis_client.get(key)
    if cached_sdl:
        data = json.loads(cached_sdl)
        return SdlCacheRecord(**data)
    return None

def update_sdl_cache(sdl_hash: str, cached_sdl: GraphQLTestPreparationResponse):
    """Update the SDL cache in Redis."""
    key = f"SDL_NAMESPACE:{sdl_hash}"
    redis_client.setex(key, REDIS_OPENAPI_KEY_EXPIRATION_TIME, cached_sdl.model_dump_json())

def retrieve_cached_graphql_test_case(test_case_id: str) -> Union[GraphQLCacheRecord, ErrorInfo]:
    """Retrieve cached GraphQL test case from Redis."""
    key = f"TESTCASE_NAMESPACE:{test_case_id}"
    cached_string = redis_client.get(key)
    if cached_string is None:
        return ErrorInfo(response="Test case not found. Invalid or expired test case ID.")
    return json.loads(cached_string)

def clear_test_case_cache(test_case_id: str):
    """Clear test case cache in Redis."""
    key = f"TESTCASE_NAMESPACE:{test_case_id}"
    redis_client.delete(key)

def update_graphql_test_case_cache(test_case_id: str, value: dict):
    """Update the GraphQL test case cache in Redis."""
    key = f"TESTCASE_NAMESPACE:{test_case_id}"
    redis_client.setex(key, REDIS_TESTCASE_KEY_EXPIRATION_TIME, json.dumps(value))
    print(f"Cache updated for key: {key}")
