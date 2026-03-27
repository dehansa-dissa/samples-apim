import logging

from fastapi import FastAPI, HTTPException, Request, Response
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from pymilvus import DataType, MilvusClient
from http import HTTPStatus
import os
from pydantic import BaseModel

from milvus_proxy_service.log_filters import EndpointFilter
from milvus_proxy_service.utils import get_field_values, authenticate_org
import milvus_proxy_service.constants as const

# A proxy service to create a collection using flask and milvus
app = FastAPI()

# Setting log levels
log_level = os.getenv('LOG_LEVEL', logging.INFO)
logging.basicConfig(level=log_level)
for logger_name in logging.root.manager.loggerDict:
    logging.getLogger(logger_name).setLevel(log_level)

logging.getLogger("uvicorn.access").addFilter(EndpointFilter(const.EXCLUDED_ENDPOINTS))

X_JWT_ASSERTION = 'x-jwt-assertion'

class ProductOrigin(str, Enum):
    CHOREO = "CHOREO"
    DEVANT = "DEVANT"


def get_milvus_client(product_origin: ProductOrigin) -> MilvusClient:
    if product_origin == ProductOrigin.CHOREO:
        url = os.getenv(const.CHOREO_MILVUS_URL)
        api_key = os.getenv(const.CHOREO_MILVUS_API_KEY)
    elif product_origin == ProductOrigin.DEVANT:
        url = os.getenv(const.DEVANT_MILVUS_URL)
        api_key = os.getenv(const.DEVANT_MILVUS_API_KEY)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown product_origin: {product_origin}")

    if not url or not api_key:
        raise HTTPException(status_code=500,
                            detail=f"Milvus credentials not configured for product: {product_origin}")

    return MilvusClient(uri=url, token=api_key)


class FilterReqBody(BaseModel):
    collection_name: str
    filter_query: str
    output_fields: list
    product_origin: ProductOrigin = ProductOrigin.CHOREO


class DeleteReqBody(BaseModel):
    collection_name: str
    id: list
    product_origin: ProductOrigin = ProductOrigin.CHOREO


class UpsertReqBody(BaseModel):
    collection_name: str
    data: Union[dict, list]
    product_origin: ProductOrigin = ProductOrigin.CHOREO


class CreateColReqBody(BaseModel):
    collection_name: str
    schema_fields: list
    product_origin: ProductOrigin = ProductOrigin.CHOREO


class SearchReqBody(BaseModel):
    data: list
    collection_name: str
    expr: str
    output_fields: list
    timeout: int
    anns_field: Optional[str]
    limit: int
    product_origin: ProductOrigin = ProductOrigin.CHOREO


class DocSearchReqBody(BaseModel):
    data: list
    collection_name: str
    output_fields: list
    timeout: int
    anns_field: Optional[str]
    limit: int
    product_origin: ProductOrigin = ProductOrigin.CHOREO


@app.post('/search')
def search(request: Request, response: Response, request_body: SearchReqBody):
    # access_token = request.headers.get('X_JWT_ASSERTION')
    logging.debug(request.headers)

    # logging.debug(f"Access token: {access_token}")
    #
    # if not access_token:
    #     response.status_code = 401
    #     return {"message": "Missing Authorization header to fetch org_id"}
    #
    # # Get the org-id from the headers
    # org_id = request.headers.get('org-id')
    # if not org_id:
    #     response.status_code = 401
    #     return {"message": "Missing org-id header"}
    #
    # authenticated = authenticate_org(access_token, org_id)
    #
    # if authenticated == "Invalid org-id":
    #     response.status_code = 401
    #     return {"message": "Org Id is not matching with the token"}
    # elif authenticated == "Invalid token":
    #     response.status_code = 401
    #     return {"message": "Invalid token"}
    # if not authenticated:
    #     response.status_code = 401
    #     return {"message": "Unauthorized access"}

    # Extract the parameters from the request's JSON body
    data = request_body.data
    anns_field = request_body.anns_field
    limit = request_body.limit
    expr = request_body.expr
    output_fields = request_body.output_fields
    timeout = request_body.timeout
    collection_name = request_body.collection_name

    # Create a Milvus client
    mc = get_milvus_client(request_body.product_origin)

    # Check if the collection exists
    if not mc.has_collection(collection_name):
        response.status_code = HTTPStatus.NOT_FOUND
        return {"message": f"Collection {collection_name} doesn't exist"}

    # Perform the search
    results = mc.search(
        collection_name=collection_name,
        data=data,
        anns_field=anns_field,
        limit=limit,
        filter=expr,
        output_fields=output_fields,
        timeout=timeout
    )

    return results


@app.post('/doc_search')
def doc_search(request: Request, response: Response, request_body: DocSearchReqBody):

    # Extract the parameters from the request's JSON body
    data = request_body.data
    anns_field = request_body.anns_field
    limit = request_body.limit
    output_fields = request_body.output_fields
    timeout = request_body.timeout
    collection_name = request_body.collection_name

    # Create a Milvus client
    mc = get_milvus_client(request_body.product_origin)

    # Check if the collection exists
    if not mc.has_collection(collection_name):
        response.status_code = HTTPStatus.NOT_FOUND
        return {"message": f"Collection {collection_name} doesn't exist"}

    # Perform the search
    results = mc.search(
        collection_name=collection_name,
        data=data,
        anns_field=anns_field,
        limit=limit,
        output_fields=output_fields,
        timeout=timeout
    )

    return results


@app.post('/create_collection')
def create_collection(request: Request, request_body: CreateColReqBody):
    mc = get_milvus_client(request_body.product_origin)
    collection_name = request_body.collection_name
    has = mc.has_collection(collection_name)
    if has:
        return {"message": f"Collection {collection_name} already exists."}

    schema_fields = request_body.schema_fields

    schema = MilvusClient.create_schema(
        auto_id=False,
        enable_dynamic_field=False,
    )

    for field in schema_fields:
        is_primary, is_partition_key, field_type = get_field_values(field)

        if field_type == DataType.FLOAT_VECTOR:
            schema.add_field(
                field_name=field.get('field_name'),
                datatype=field_type,
                is_primary=is_primary,
                is_partition_key=is_partition_key,
                dim=field.get('dim')
            )
        else:
            schema.add_field(
                field_name=field.get('field_name'),
                datatype=field_type,
                is_primary=is_primary,
                is_partition_key=is_partition_key,
                max_length=field.get('max_length')
            )

    index_params = mc.prepare_index_params()

    index_params.add_index(
        field_name="vector",
        index_type="AUTOINDEX",
        metric_type="L2"
    )

    mc.create_collection(
        collection_name=collection_name,
        metric_type="COSINE",
        schema=schema,
        index_params=index_params
    )
    return {"message": f"Collection {collection_name} created."}


@app.post('/upsert_vector')
def upsert_vector(request: Request, request_body: UpsertReqBody):
    mc = get_milvus_client(request_body.product_origin)
    collection_name = request_body.collection_name
    if not mc.has_collection(collection_name):
        return {"message": f"Collection {collection_name} doesn't exist, create collection first using "
                           f"/create_collection endpoint."}

    response = mc.upsert(collection_name=collection_name, data=request_body.data)

    return {"message": response}


@app.get('/filter_data')
async def filter_data(request: Request, request_body: FilterReqBody):
    mc = get_milvus_client(request_body.product_origin)
    collection_name = request_body.collection_name
    if not mc.has_collection(collection_name):
        return {"message": f"Collection {collection_name} doesn't exist"}

    filter_query = request_body.filter_query
    output_fields = request_body.output_fields

    response = mc.query(
        collection_name=collection_name,
        filter=f'({filter_query})',
        output_fields=output_fields,
    )

    return {"message": response}


@app.delete('/delete_vectors')
async def delete_vectors(request_body: DeleteReqBody):
    mc = get_milvus_client(request_body.product_origin)
    collection_name = request_body.collection_name
    if not mc.has_collection(collection_name):
        return {"message": f"Collection {collection_name} doesn't exist"}

    response = mc.delete(
        collection_name=collection_name,
        ids=request_body.id
    )

    return {"message": response}


@app.get('/has_collection')
def has_collection(collection_name: str, product_origin: ProductOrigin = ProductOrigin.CHOREO):
    mc = get_milvus_client(product_origin)
    exists = mc.has_collection(collection_name)
    return {
        "collection_exists": exists,
    }


@app.get("/health")
def health():
    """Check the api is running"""
    return {"status": "Running"}
