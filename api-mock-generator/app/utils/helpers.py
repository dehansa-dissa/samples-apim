import json
import jsonref
import traceback
from app.utils.logger import logger

def clean_openapi_spec(api_definition: dict, use_previous_scripts) -> dict:
    """
    Clean the OpenAPI specification by removing unnecessary fields.

    Args:
        api_definition (dict): The OpenAPI specification as a dictionary.
        use_previous_scripts (bool): Flag to determine if previous scripts should be retained.

    Returns:
        dict: Cleaned OpenAPI specification with sensitive or unnecessary fields removed.
    """
    paths = api_definition.get("paths", {}) # sanitize newlines etc/ cleanin in carbon
    for path, methods in paths.items():
        for method, details in methods.items():
            if isinstance(details, dict):
                details.pop("security", None)
                details.pop("x-auth-type", None)
                details.pop("x-throttling-tier", None)
                if not use_previous_scripts:
                    details.pop("x-mediation-script", None)
                details.pop("x-wso2-application-security", None)
                details.pop("externalDocs", None)

    components = api_definition.get("components", {})
    components.pop("securitySchemes", None)

    cleaned_swagger = {
        "paths": paths
    }
    return cleaned_swagger

def output_json_schema_generate_mocks(api_definition: dict) -> dict:
    """
    Generate a JSON schema template for mock generation based on the API definition.

    Args:
        api_definition (dict): The OpenAPI specification as a dictionary.

    Returns:
        dict: JSON schema template describing mockDB and inline scripts for each path and method.
    """
    json_schema = { # use mockDataSet
        "mockDB": "The prepopulated MockDB in the format {collectionName:[...]}",
        "paths": {}
    }

    paths = api_definition.get("paths", {})
    for path, methods in paths.items():
        json_schema["paths"][path] = {}
        for method, details in methods.items():
            if method == 'parameters':
                continue
            json_schema["paths"][path][method] = "The Inline Script For the execution of the method "+ method + " on the path " + path

    return json_schema

def output_json_schema_modify_method() -> dict:
    """
    Generate a JSON schema template for the modify method operation.

    Returns:
        dict: JSON schema template with a modified_script field.
    """
    return {
        "modified_script": "The modified script..." 
    }

def output_json_schema_generate_mocks_sim_resource(paths: dict, paths_batch: list) -> dict:
    """
    Generate a JSON schema template for mock generation for a batch of paths.

    Args:
        paths (dict): Dictionary of API paths and their methods.
        paths_batch (list): List of paths to include in the batch.

    Returns:
        dict: JSON schema template for the specified batch of paths.
    """
    json_schema = {}
    if len(paths_batch) == 1 and paths_batch[0] == 'mockDB':
        json_schema["mockDB"] = "The prepopulated MockDB in the format {collectionName:[...]}"
        return json_schema

    if len(paths_batch) >= 1:
        for path in paths_batch:
            json_schema[path] = {}
            for method in paths[path]:
                if method == 'parameters':
                    continue
                json_schema[path][method] = "The Inline Script For the execution of the method "+ method + " on the path " + path
    
    return json_schema

def batch_paths_by_method_count(paths: dict, batch_size: int) -> list[list[str]]:
    """
    Batch API paths by the count of methods to limit batch size.

    Args:
        paths (dict): Dictionary of API paths and their methods.
        batch_size (int): Maximum number of methods per batch.

    Returns:
        list[list[str]]: List of batches, each batch is a list of path strings.
    """
    batches = []
    current_batch = []
    op_count = 0

    for path, methods in paths.items():
        method_count = len(methods)

        if op_count + method_count > batch_size:
            if current_batch:
                batches.append(current_batch)
            current_batch = [path]
            op_count = method_count
        else:
            current_batch.append(path)
            op_count += method_count

    if current_batch:
        batches.append(current_batch)

    return batches

def get_simplified_spec(spec, use_previous_scripts = False):
    """
    Simplify and clean an OpenAPI specification, resolving JSON references.

    Args:
        spec (str or dict): The OpenAPI specification as a JSON string or dictionary.
        use_previous_scripts (bool, optional): Flag to retain previous scripts. Defaults to False.

    Returns:
        dict: Simplified and cleaned OpenAPI specification.

    Raises:
        ValueError: If JSON decoding fails.
        RuntimeError: If JSON reference processing fails.
    """
    #if string convert to json
    if isinstance(spec, str):
        try:
            spec = json.loads(spec)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to decode JSON spec: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    try:
        spec = jsonref.replace_refs(spec)  # contains fully resolved specs as a dict
    except Exception as e:
        tb = traceback.format_exc()
        error_msg = f"Error processing JSON references: {e}\\nTraceback:\\n{tb}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    spec = clean_openapi_spec(spec, use_previous_scripts)
    return spec

def validate_schema(response, output_schema):
    """
    Recursively validate if a response matches the output schema.

    Args:
        response (any): The response object to validate.
        output_schema (any): The expected schema to validate against.

    Returns:
        bool: True if the response matches the schema, False otherwise.
    """
    if not isinstance(response, dict):
        if isinstance(response, str) and isinstance(output_schema, str):
            return True
        return False

    response_keys = set(response.keys())
    schema_keys = set(output_schema.keys())

    if response_keys != schema_keys or len(response.keys()) != len(output_schema.keys()):
        return False

    for key in response_keys:
        if not validate_schema(response[key], output_schema[key]):
            return False

    return True
