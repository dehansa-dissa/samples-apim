import logging

from pymilvus import DataType
import jwt
from jwt.exceptions import ExpiredSignatureError, DecodeError


def get_field_values(field):
    is_primary = False
    is_partition_key = False

    if field.get('is_primary'):
        is_primary = field.get('is_primary')

    if field.get('is_partition_key'):
        is_partition_key = field.get('is_partition_key')

    field_type = DataType[field.get('datatype')]

    return is_primary, is_partition_key, field_type


def authenticate_org(access_token, org_id):
    try:
        # Decode the token
        decoded_dict = jwt.decode(access_token, options={"verify_signature": False})

        # Check the orgid
        if decoded_dict.get('organization').get('uuid') != org_id:
            logging.error("Invalid org-id")
            return "Invalid org-id"

        return True

    except DecodeError:
        # The token is invalid
        logging.exception("Invalid token")
        return "Invalid token"


def extract_required_content(results):
    output = []
    if type(results) is list:
        for result in results:
            entity = result.get('entity')
            # create a dictionary with the required fields
            test = {
                "page_content": entity.get('text'),
                "metadata": {
                    "ChoreoMetadata": entity.get('ChoreoMetadata'),
                    "pk": result.get('pk')
                }
            }
            output.append(test)

    return output

