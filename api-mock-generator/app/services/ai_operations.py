from app.utils.helpers import get_simplified_spec,output_json_schema_generate_mocks,output_json_schema_modify_method, validate_response
from app.utils.ai_client import generate_text, generate_structured_output
from app.utils.prompts import generate_mocks_sys_msg,generate_mocks_prompt,modify_method_prompt,modify_method_sys_msg

import json

def generate_mock_scripts(open_api_spec, config):
    simplified_spec = get_simplified_spec(open_api_spec)
    output_json_schema = output_json_schema_generate_mocks(simplified_spec)
    user_msg = generate_mocks_prompt(config)
    sys_msg = generate_mocks_sys_msg(simplified_spec,config)
    mock_scripts = generate_structured_output(sys_msg,user_msg, output_json_schema)
    response_json = json.loads(mock_scripts)
    print(response_json)
    if (not validate_response(response_json, output_json_schema)):
        return
    return response_json

def modify_method(open_api_spec,script, path, method, instructions):
    simplified_spec = get_simplified_spec(open_api_spec)
    required_method = simplified_spec["paths"][path][method]
    output_json_schema = output_json_schema_modify_method()
    user_msg = modify_method_prompt(script,instructions)
    sys_msg = modify_method_sys_msg(method,path,required_method)
    mock_script = generate_structured_output(sys_msg,user_msg, output_json_schema)
    response_json = json.loads(mock_script)
    return response_json
