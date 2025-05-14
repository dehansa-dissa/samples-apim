import json
import jsonref
import traceback
from app.utils.logger import logger

def clean_openapi_spec(api_definition: dict, use_previous_scripts) -> dict:
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
    return {
        "modified_script": "The modified script..." 
    }

def output_json_schema_generate_mocks_sim_resource(paths: dict, paths_batch: list) -> dict:
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
