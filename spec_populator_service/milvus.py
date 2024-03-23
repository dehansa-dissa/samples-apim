from pymilvus import DataType, MilvusClient
import os
from utils import *

api_key = os.getenv('MILVERSE_API_KEY')
url = os.getenv('MILVERSE_URL')

def upsert_vector_for_onprem(embed, collection, api: API, tenant):

    mc = MilvusClient(uri=url, token=api_key)
    collection_name = collection + "__apim__"

    has = mc.has_collection(collection_name)
    if not has:
        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
        )
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=100)
        schema.add_field(field_name="metadata", datatype=DataType.JSON, max_length=2000)
        schema.add_field(field_name="api_type", datatype=DataType.VARCHAR, max_length=100)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
        schema.add_field(field_name="page_content", datatype=DataType.VARCHAR, max_length=10000)
        schema.add_field(field_name="tenant_domain", datatype=DataType.VARCHAR, max_length=512,  is_partition_key=True)

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
    res = embed.embed_query(str(api.__dict__))
    payload={
            "page_content": str(api.spec),
            "metadata": {
                "id": api.id,
                "api_name": api.name,
                "api_version": api.version,
                "api_type": api.type
            },
            "id": api.id,
            "vector": res,
            "api_type": api.type,
            "tenant_domain": tenant
        }
    response = mc.upsert(collection_name=collection_name, data=payload)
    return response


def upsert_vector_for_choreo(embed, record, collection, api_id, api_name):

    mc = MilvusClient(uri=url, token=url)
    collection_name = collection + "__choreo__"

    has = mc.has_collection(collection_name)
    if not has:

        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
        )
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=100)
        schema.add_field(field_name="api_name", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="api_type", datatype=DataType.VARCHAR, max_length=100)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
        schema.add_field(field_name="page_content", datatype=DataType.VARCHAR, max_length=10000)

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
        
    res = embed.embed_query(str(record))
    payload={
            "page_content": str(record),
            "api_name": api_name,
            "id": api_id,
            "vector": res
        }
    response = mc.upsert(collection_name=collection_name, data=payload)
    return response

def delete_vector_for_onprem(uuid, collection):

    collection = collection + "__apim__"
    mc = MilvusClient(uri=url, token=api_key)

    res = mc.delete(
        collection_name=collection,
        ids=uuid
    )
    return res
