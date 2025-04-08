from app.utils.helpers import get_simplified_spec,output_json_schema_generate_mocks,output_json_schema_modify_method, validate_response
from app.utils.ai_client import generate_structured_output
from app.utils.prompts import generate_mocks_sys_msg,generate_mocks_prompt,modify_method_prompt,modify_method_sys_msg, fix_schema_prompt
from app.utils.dev_tools import rec,Consts
from datetime import datetime
import json

def generate_mock_scripts(open_api_spec, config):
    time = datetime.now()
    simplified_spec = get_simplified_spec(open_api_spec)
    rec.add(Consts.length_of_cleaned_spec, len(str(simplified_spec)))
    output_json_schema = output_json_schema_generate_mocks(simplified_spec)
    rec.add(Consts.length_of_output_schema, len(json.dumps(output_json_schema)))
    user_msg = generate_mocks_prompt(config)
    rec.add(Consts.user_msg_length, len(user_msg))
    sys_msg = generate_mocks_sys_msg(simplified_spec,config)
    rec.add(Consts.sys_msg_length, len(sys_msg))
    mock_scripts = generate_structured_output(sys_msg,user_msg, output_json_schema)
    rec.add(Consts.response_length, len(mock_scripts))
    response_json = json.loads(mock_scripts)
    rec.add(Consts.response_time, (datetime.now()-time).microseconds)
    print(response_json)
    if (not validate_response(response_json, output_json_schema)):
        rec.add(Consts.is_response_schema_valid_1, False)
        user_msg = fix_schema_prompt(mock_scripts)
        mock_scripts = generate_structured_output(sys_msg, None, output_json_schema)
        response_json = json.loads(mock_scripts)
        if (not validate_response(response_json, output_json_schema)):
            rec.add(Consts.is_response_schema_valid_2, False)
            return
        rec.add(Consts.is_response_schema_valid_2, True)
        rec.add(Consts.deployment_success, True)
        return
    rec.add(Consts.is_response_schema_valid_1, True)
    rec.add(Consts.deployment_success, True)
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
