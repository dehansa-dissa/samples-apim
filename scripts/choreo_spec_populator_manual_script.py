import logging
import os
import csv
from time import sleep
import pandas as pd
import requests
from pymongo.errors import OperationFailure
from pymongo import MongoClient, ASCENDING
import time

MAX_RETRIES = 3

# Set the following configs as per the environment
# URL of the service
SPEC_POPULATOR_URL = 'http://localhost:8000/add_vector/'
MONGODB_HOST = ""
MONGODB_USER = ""
MONGODB_NAME = ""
MONGODB_PASSWORD = ""

MONGODB_CONNECTION_URL = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASSWORD}@{MONGODB_HOST}/?retryWrites=true&w=majority&connectTimeoutMS=360000"

logging.basicConfig(level=logging.INFO)


def upsert_vector_for_choreo(params, request_body, doc_id):
    sleep(0.5)
    response = requests.post(SPEC_POPULATOR_URL + doc_id, json=request_body, params=params)
    return response


def push_rest_apis(document):
    content = None

    doc_id = str(document.get("_id"))

    org_id = document.get("organizationId")
    api_name = document.get("name")
    api_uuid = document.get("serviceId")
    api_version = document.get("version")

    params = {
        "orgID": org_id,
    }

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

    request_body = {
        "api_name": api_name,
        "api_type": "REST",
        "api_spec": content,
        "description": description,
        "version": api_version,
        "api_uuid": api_uuid
    }

    response = upsert_vector_for_choreo(params, request_body, doc_id)
    logging.info("Response status code: %s", response.status_code)
    if response.status_code == 500:
        insert_data("corrupted_docs.csv", org_id, doc_id)
        logging.info("Failed to push REST API for org_id: %s and id: %s", org_id, doc_id)
        with open(f'corrupted_files/{doc_id}.txt', 'w') as file:
            file.write(content)
    elif response.status_code == 200:
        insert_data("rest_api_pushed.csv", org_id, doc_id)
        logging.info("Pushed REST API for org_id: %s and id: %s", org_id, doc_id)
    else:
        logging.error("Failed to push REST API for org_id: %s and id: %s", org_id, doc_id)
        logging.error("Response: %s", response.json())


def insert_data(file_name, org_id, doc_id):
    file_exists = os.path.isfile(file_name)

    with open(file_name, mode='a') as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(['org_id', 'doc_id'])  # writing the headers

        writer.writerow([org_id, doc_id])


def check_file_exists(file_name):
    return os.path.isfile(file_name)


if __name__ == '__main__':
    document_count = 0
    rest_document_count = 0

    csv_exists = check_file_exists("rest_api_pushed.csv")
    if csv_exists:
        data_df = pd.read_csv("rest_api_pushed.csv")

    corrupted_csv_exists = check_file_exists("corrupted_docs.csv")
    if corrupted_csv_exists:
        corrupted_df = pd.read_csv("corrupted_docs.csv")

    if not os.path.exists('corrupted_files'):
        os.makedirs('corrupted_files')

    client = MongoClient(MONGODB_CONNECTION_URL)
    db = client[MONGODB_NAME]
    collection = db['resources']

    for tries in range(MAX_RETRIES):
        try:
            with client.start_session() as session:
                session.start_transaction()
                cursor = collection.find({}, no_cursor_timeout=True, session=session).sort("createdTime", ASCENDING)

                refresh_timestamp = time.time()

                number_of_documents = collection.count_documents({}, session=session)
                while document_count <= number_of_documents:
                    logging.info("Total number of documents: %s", number_of_documents)
                    if (time.time() - refresh_timestamp) > 300:  # 300 seconds = 5 minutes
                        number_of_documents = collection.count_documents({}, session=session)
                        logging.info("Refreshing session")
                        session.end_session()
                        session = client.start_session()
                        session.start_transaction()
                        cursor = collection.find({}, no_cursor_timeout=True, session=session).sort("createdTime", ASCENDING)
                        refresh_timestamp = time.time()

                    try:
                        document = next(cursor)
                        document_count += 1  # Increment the counter for each document

                        logging.info("Processing document %s", document_count)

                        if csv_exists:
                            org_id = document.get("organizationId")
                            doc_id = str(document.get("_id"))
                            if data_df[(data_df['org_id'] == org_id) & (data_df['doc_id'] == doc_id)].shape[0] > 0:
                                logging.info("Skipping org_id: %s and id: %s", org_id, doc_id)
                                continue

                        if corrupted_csv_exists:
                            org_id = document.get("organizationId")
                            doc_id = str(document.get("_id"))
                            if corrupted_df[(corrupted_df['org_id'] == org_id) & (corrupted_df['doc_id'] == doc_id)].shape[
                                0] > 0:
                                logging.info("Skipping org_id: %s and id: %s", org_id, doc_id)
                                continue

                        if doc_type := document.get("serviceType"):
                            if doc_type == "REST":
                                rest_document_count += 1  # Increment the counter for each REST document
                                push_rest_apis(document)
                                tries = 0
                            else:
                                # logging.info("Skipping org_id: %s and id: %s", org_id, doc_id)
                                logging.info("Document type is - %s", doc_type)
                        # process document here
                    except StopIteration:
                        break

                session.commit_transaction()
                # Break the loop after processing all the documents
                break
        except OperationFailure as e:
            logging.exception("Error occurred while processing documents", exc_info=e)
            continue
    else:
        logging.error("Failed to commit transaction after %s retries", MAX_RETRIES)

    logging.info("Total document count - %s", document_count)  # Print the total number of documents
    logging.info("Rest document count - %s", rest_document_count)
