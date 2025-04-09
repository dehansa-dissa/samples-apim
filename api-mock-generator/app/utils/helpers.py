import json
import jsonref

def clean_openapi_spec(api_definition: dict) -> dict:
    paths = api_definition.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if isinstance(details, dict):
                details.pop("security", None)
                details.pop("x-auth-type", None)
                details.pop("x-throttling-tier", None)
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
    json_schema = {
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

def get_simplified_spec(spec):
    #if string convert to json
    if isinstance(spec, str):
        spec = json.loads(spec)
    try:
        spec = jsonref.replace_refs(spec)  # contains fully resolved specs as a dict
    except Exception as e:
        pass
    spec = clean_openapi_spec(spec)
    return spec

def validate_response(response, output_schema):
    if not isinstance(response, dict):
        return False
    
    for field, sub_schema in output_schema.items():
        if field not in response:
            return False
        
        if isinstance(sub_schema, dict):  # Handle nested structures
            if not isinstance(response[field], dict):
                return False
            if not validate_response(response[field], sub_schema):
                return False
        elif not isinstance(sub_schema, str):
            return False
    
    return True

def output_json_schema_generate_mocks_sim_resource(paths: dict, path: str) -> dict:
    json_schema = {}

    if path not in paths:
        if path == "mockDB":
            json_schema["mockDB"] = "The prepopulated MockDB in the format {collectionName:[...]}"
            return json_schema
        return json_schema

    methods = paths[path]
    json_schema[path] = {}
    for method, details in methods.items():
        if method == 'parameters':
            continue
        json_schema[path][method] = "The Inline Script For the execution of the method "+ method + " on the path " + path

    return json_schema