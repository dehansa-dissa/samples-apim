import json
import logging
import os
import csv
from time import sleep
import pandas as pd
from pymongo.errors import OperationFailure
from pymongo import MongoClient, ASCENDING
from pymilvus import DataType, MilvusClient, Collection, connections
import time

from utils import pre_process_openapi, get_emb_model, ChoreoAPI

MAX_RETRIES = 3

# Set the following configs as per the environment
MONGODB_HOST = ""
MONGODB_USER = ""
MONGODB_NAME = ""
MONGODB_PASSWORD = ""

# Set the following configs as per the environment
MILVERSE_API_KEY = ""
MILVERSE_URL = ""

# Set the collection name
# in dev it is "DevChoreoMarketplace"
# in prod it is "ProdChoreoMarketplace"
# in stage it is "StagChoreoMarketplace"
collection_name = ""

# Set the output file prefix
# in dev it is "dev_doc_"
# in prod it is "prod_doc_"
# in stage it is "stage_doc_"
output_file_prefix = ""

MONGODB_CONNECTION_URL = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_HOST}/?retryWrites=true&w=majority&connectTimeoutMS=360000"

logging.basicConfig(level=logging.INFO)

milvus_entry_count_from_script = 0


ALL_APIS_FILE = "all_apis.csv"
REST_APIS_FILE = "rest_api_pushed.csv"
CORRUPTED_DOCS_FILE = "corrupted_docs.csv"


def prepare_data(document):
    global milvus_entry_count_from_script
    content = None

    doc_id = str(document.get("_id"))

    org_id = document.get("organizationId")
    api_name = document.get("name")
    api_uuid = document.get("serviceId")
    api_version = document.get("version")

    # To Skip cases where there is no IDLs key in the document
    # In the latest schema, IDLs should be a key in the document
    if 'idls' not in document.keys():
        logging.error("idls key not found in the document for org_id: %s and id: %s", org_id, doc_id)
        return

    idls = document.get('idls')

    if len(idls.keys()) == 0:
        logging.error("No IDLs found in the document for org_id: %s and id: %s", org_id, doc_id)

    if 'content' in idls.keys():
        content = idls.get('content')
    else:
        for idl_key in idls.keys():
            content = idls.get(idl_key).get('content')
            break

    description = document.get('description')
    if not description:
        description = document.get('summary')

    if type(content) is dict:
        content = str(content)
    else:
        content = content

    if content is None:
        logging.error("No spec for org_id: %s and id: %s", org_id, doc_id)
        return

    document = {
        "id": doc_id,
        "org_id": org_id,
        "api_name": api_name,
        "api_type": "REST",
        "api_spec": content,
        "description": description,
        "version": api_version,
        "api_uuid": api_uuid
    }

    return create_record(document)


def create_record(document):
    try:
        record = pre_process_openapi(document["api_spec"])
        record["apim_description"] = document["description"]

        api = ChoreoAPI(
            id=document["id"],
            version=document["version"],
            type=document["api_type"],
            name=document["api_name"],
            spec=record,
            api_uuid=document["api_uuid"]
        )

        embed = get_emb_model()
        res = embed.embed_query(str(api.__dict__))

        milvus_record = {
            "page_content": str(api.spec),
            "metadata": {
                "id": api.id,
                "api_name": api.name,
                "api_version": api.version,
                "api_type": api.type,
                "api_uuid": api.api_uuid
            },
            "id": api.id,
            "api_name": api.name,
            "vector": res,
            "api_type": api.type,
            "org_id": document["org_id"],
        }

        return milvus_record

    except Exception as e:
        logging.error(f"Error processing API: {document['id']}")
        logging.error(e)
        insert_data(CORRUPTED_DOCS_FILE, document["org_id"], document["id"])
        return None


def get_collection_raw_count(mc):
    response = mc.query(
        collection_name=collection_name,
        output_fields=["count(*)"],
    )
    mc.get_collection_stats(collection_name=collection_name)
    return response[0]["count(*)"]


def upsert_bulk_vector_for_choreo(data):
    global milvus_entry_count_from_script
    connections.connect(uri=MILVERSE_URL, token=MILVERSE_API_KEY)
    collection = Collection(name=collection_name)
    entry_count_initial = collection.query(expr="", output_fields=["count(*)"])[0]["count(*)"]
    logging.info("Entry count from script: %s", milvus_entry_count_from_script)
    logging.info("Initial entry count: %s", entry_count_initial)
    res = collection.upsert(data)
    logging.info("Success count: %s", res.succ_count)
    logging.info("Upsert count: %s", res.upsert_count)
    sleep(10)
    entry_count_final = collection.query(expr="", output_fields=["count(*)"])[0]["count(*)"]
    logging.info("Final entry count: %s", entry_count_final)
    milvus_entry_count_from_script += len(data)
    if milvus_entry_count_from_script - entry_count_final > 100:
        logging.error("Failed to insert all the records")
        exit()
    # tasks = utility.do_bulk_insert(
    #     collection_name=collection_name,
    #     is_row_based=True,
    #     files=[file_name]
    # )
    connections.disconnect(alias="default")
    connections.remove_connection(alias="default")


def insert_data(file_name, org_id, doc_id):
    file_exists = os.path.isfile(file_name)

    with open(file_name, mode='a') as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(['org_id', 'doc_id'])  # writing the headers

        writer.writerow([org_id, doc_id])


def write_list_dict_to_csv(file_name, data):
    file_exists = os.path.isfile(file_name)
    with open(file_name, mode='a') as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(['org_id', 'doc_id'])

        for row in data:
            writer.writerow(row.values())


def check_file_exists(file_name):
    return os.path.isfile(file_name)


def create_collection(collection_name):
    logging.info("Creating collection %s", collection_name)
    mc = MilvusClient(uri=MILVERSE_URL, token=MILVERSE_API_KEY)
    has = mc.has_collection(collection_name)
    if not has:
        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
        )
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=65000)
        schema.add_field(field_name="metadata", datatype=DataType.JSON, max_length=65000)
        schema.add_field(field_name="api_type", datatype=DataType.VARCHAR, max_length=65000)
        schema.add_field(field_name="api_name", datatype=DataType.VARCHAR, max_length=65000)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
        schema.add_field(field_name="page_content", datatype=DataType.VARCHAR, max_length=65000)
        schema.add_field(field_name="org_id", datatype=DataType.VARCHAR, max_length=65000, is_partition_key=True)

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

    mc.close()


def write_json_to_file(file_name, data):
    proper_dict = {"rows": data}
    # final_json = json.dumps(proper_dict)
    with open(file_name, "w") as file:
        json.dump(proper_dict, file)

    file.close()


def populate_milvus():
    global milvus_entry_count_from_script
    document_count = 0
    rest_document_count = 0

    output_json_count = 0

    csv_exists = check_file_exists(REST_APIS_FILE)
    if csv_exists:
        data_df = pd.read_csv(REST_APIS_FILE)

    all_csv_exists = check_file_exists(ALL_APIS_FILE)
    if all_csv_exists:
        data_df = pd.read_csv(ALL_APIS_FILE)

    corrupted_csv_exists = check_file_exists(CORRUPTED_DOCS_FILE)
    if corrupted_csv_exists:
        corrupted_df = pd.read_csv(CORRUPTED_DOCS_FILE)

    if not os.path.exists('corrupted_files'):
        os.makedirs('corrupted_files')

    client = MongoClient(MONGODB_CONNECTION_URL)
    db = client[MONGODB_NAME]
    collection = db['resources']
    tries = 0
    record_list = []
    info_list = []

    for tries in range(MAX_RETRIES):
        try:
            with client.start_session() as session:
                session.start_transaction()
                cursor = collection.find({}, no_cursor_timeout=True, session=session, allow_disk_use=True).sort(
                    "createdTime", ASCENDING)

                refresh_timestamp = time.time()

                number_of_documents = collection.count_documents({}, session=session)
                while document_count <= number_of_documents:
                    logging.info("Total number of documents: %s", number_of_documents)
                    if (time.time() - refresh_timestamp) > 300:  # 300 seconds = 5 minutes
                        logging.info("Refreshing session")
                        session.end_session()
                        session = client.start_session()
                        session.start_transaction()
                        cursor = collection.find({}, no_cursor_timeout=True, session=session, allow_disk_use=True).sort("createdTime",
                                                                                                   ASCENDING)
                        number_of_documents = collection.count_documents({}, session=session)
                        refresh_timestamp = time.time()

                    try:
                        document = next(cursor)
                        document_count += 1  # Increment the counter for each document

                        logging.info("Processing document %s", document_count)

                        org_id = document.get("organizationId")
                        doc_id = str(document.get("_id"))

                        insert_data(ALL_APIS_FILE, org_id, doc_id)
                        logging.info("Processing org_id: %s and id: %s", org_id, doc_id)

                        if csv_exists:
                            if data_df[(data_df['org_id'] == org_id) & (data_df['doc_id'] == doc_id)].shape[0] > 0:
                                logging.info("Skipping org_id: %s and id: %s", org_id, doc_id)
                                milvus_entry_count_from_script += 1
                                logging.info("Milvus entry count from script: %s", milvus_entry_count_from_script)
                                continue

                        if corrupted_csv_exists:
                            if \
                                    corrupted_df[
                                        (corrupted_df['org_id'] == org_id) & (corrupted_df['doc_id'] == doc_id)].shape[
                                        0] > 0:
                                logging.info("Skipping org_id: %s and id: %s", org_id, doc_id)
                                continue

                        if all_csv_exists:
                            if data_df[(data_df['org_id'] == org_id) & (data_df['doc_id'] == doc_id)].shape[0] > 0:
                                logging.info("Already processes org_id: %s and id: %s", org_id, doc_id)
                                continue

                        if doc_type := document.get("serviceType"):
                            if doc_type == "REST":
                                rest_document_count += 1  # Increment the counter for each REST document
                                milvus_data_raw = prepare_data(document)
                                if milvus_data_raw:
                                    record_list.append(milvus_data_raw)
                                    info_list.append({"org_id": org_id, "doc_id": doc_id})
                                    logging.info("Record count: %s", len(record_list))
                                    if len(record_list) == 1000:
                                        logging.info("writing 1000 record to file")
                                        write_json_to_file(output_file_prefix+str(output_json_count)+".json", record_list)
                                        # upsert_bulk_vector_for_choreo(record_list)
                                        write_list_dict_to_csv(REST_APIS_FILE, info_list)
                                        record_list = []
                                        info_list = []
                                        output_json_count += 1
                                        # break
                                tries = 0
                            else:
                                # logging.info("Skipping org_id: %s and id: %s", org_id, doc_id)
                                logging.info("Document type is - %s", doc_type)
                        # process document here
                    except StopIteration as e:
                        logging.exception("Error occurred while processing documents", exc_info=e)
                        tries += 1
                        break

                    if document_count == (number_of_documents + 1):
                        number_of_documents = collection.count_documents({}, session=session)

                session.commit_transaction()
                # Break the loop after processing all the documents
                break

        except OperationFailure as e:
            logging.exception("Error occurred while processing documents", exc_info=e)
            continue
    else:
        logging.error("Failed to commit transaction after %s retries", tries)

    write_json_to_file(output_file_prefix+str(output_json_count)+".json", record_list)
    logging.info("Total document count - %s", document_count)  # Print the total number of documents
    logging.info("Rest document count - %s", rest_document_count)


if __name__ == '__main__':
    create_collection(collection_name)
    populate_milvus()
