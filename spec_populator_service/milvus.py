from pymilvus import DataType, MilvusClient
import os
from utils import *

api_key = os.getenv('MILVERSE_API_KEY')
url = os.getenv('MILVERSE_URL')
collection_name = os.getenv("COLLECTION_NAME")
create_collection = os.getenv("CREATE_COLLECTION", True)

def upsert_vector_for_onprem(embed, orgID, api: API, tenant):

    mc = MilvusClient(uri=url, token=api_key)
    if create_collection:
        has = mc.has_collection(collection_name)
        if not has:
            schema = MilvusClient.create_schema(
                auto_id=False,
                enable_dynamic_field=False,
            )
            schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=100)
            schema.add_field(field_name="metadata", datatype=DataType.JSON, max_length=2000)
            schema.add_field(field_name="api_type", datatype=DataType.VARCHAR, max_length=100)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
            schema.add_field(field_name="page_content", datatype=DataType.VARCHAR, max_length=10000)
            schema.add_field(field_name="org_id", datatype=DataType.VARCHAR, max_length=512,  is_partition_key=True)
            schema.add_field(field_name="tenant_domain", datatype=DataType.VARCHAR, max_length=512)

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
            "id": orgID + api.id,
            "vector": res,
            "api_type": api.type,
            "org_id": orgID,
            "tenant_domain": tenant
        }
    response = mc.upsert(collection_name=collection_name, data=payload)
    return response


def upsert_vector_for_choreo(embed, record, orgID, api_id, api_name):

    mc = MilvusClient(uri=url, token=url)
    if create_collection:
        has = mc.has_collection(collection_name)
        if not has:

            schema = MilvusClient.create_schema(
                auto_id=False,
                enable_dynamic_field=False,
            )
            schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=100)
            schema.add_field(field_name="api_name", datatype=DataType.VARCHAR, max_length=512)
            schema.add_field(field_name="api_type", datatype=DataType.VARCHAR, max_length=100)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
            schema.add_field(field_name="org_id", datatype=DataType.VARCHAR, max_length=512,  is_partition_key=True)
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
            "id": orgID + api_id,
            "org_id": orgID,
            "vector": res
        }
    response = mc.upsert(collection_name=collection_name, data=payload)
    return response

def delete_vector_for_onprem(uuid, orgID):

    mc = MilvusClient(uri=url, token=api_key)

    res = mc.delete(
        collection_name=collection_name,
        ids= orgID + uuid,
        filter='org_id == "' + orgID + '"'
    )
    return res
