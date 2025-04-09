from app.utils.helpers import get_simplified_spec,output_json_schema_generate_mocks,output_json_schema_modify_method,output_json_schema_generate_mocks_sim_resource,validate_response
from app.utils.ai_client import generate_structured_output
from app.utils.prompts import generate_mocks_sys_msg,generate_mocks_prompt,modify_method_prompt,modify_method_sys_msg, fix_schema_prompt, generate_mocks_sim_resource_prompt
from app.utils.dev_tools import rec,Consts
from datetime import datetime
import concurrent.futures

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
        # retry 
        print("Retrying...")
        user_msg = fix_schema_prompt(mock_scripts)
        mock_scripts = generate_structured_output(None, user_msg, output_json_schema)
        response_json = json.loads(mock_scripts)
        if (not validate_response(response_json, output_json_schema)):
            rec.add(Consts.is_response_schema_valid_2, False)
            return
        rec.add(Consts.is_response_schema_valid_2, True)
        rec.add(Consts.deployment_success, True)
        return response_json
    rec.add(Consts.is_response_schema_valid_1, True)
    rec.add(Consts.deployment_success, True)
    return response_json

def generate_mock_scripts_sim_resource(open_api_spec, config):
    paths = get_simplified_spec(open_api_spec).get("paths")
    final_response = {}
    paths_response = {}
    sys_msg = generate_mocks_sys_msg(paths, config)
    mockDB_output_json_schema = output_json_schema_generate_mocks_sim_resource(paths, "mockDB")
    user_msg = generate_mocks_sim_resource_prompt(config, "mockDB")
    print("generating mockDB...")
    mockDB = generate_structured_output(sys_msg, user_msg, mockDB_output_json_schema)
    mockDB_json = json.loads(mockDB)
    if not validate_response(mockDB_json, mockDB_output_json_schema):
        rec.add(Consts.is_response_schema_valid_1, False)
        # retry 
        print("Retrying...")
        user_msg = fix_schema_prompt(mockDB)
        mockDB = generate_structured_output(None, user_msg, mockDB)
        mockDB_json = json.loads(mockDB)
        if (not validate_response(mockDB_json, mockDB)):
            rec.add(Consts.is_response_schema_valid_2, False)
            return
        rec.add(Consts.is_response_schema_valid_2, True)
    
    final_response.update(mockDB_json)

    def process_resource(path, methods):
        output_json_schema = output_json_schema_generate_mocks_sim_resource(paths, path)
        user_msg = generate_mocks_sim_resource_prompt(config, path, mockDB)
        print(f"Generating mock script for path: {path}", output_json_schema)
        mock_script = generate_structured_output(sys_msg,user_msg, output_json_schema)
        response_json = json.loads(mock_script)
        if (not validate_response(response_json, output_json_schema)):
            rec.add(Consts.is_response_schema_valid_1, False)
            # retry 
            print("Retrying...", mock_script)
            user_msg = fix_schema_prompt(mock_script)
            mock_script = generate_structured_output(None, user_msg, output_json_schema)
            response_json = json.loads(mock_script)
            if (not validate_response(response_json, output_json_schema)):
                rec.add(Consts.is_response_schema_valid_2, False)
                return
            rec.add(Consts.is_response_schema_valid_2, True)
            paths_response.update(response_json)
            return
        paths_response.update(response_json)

    
    # Use ThreadPoolExecutor to process resources simultaneously
    #with concurrent.futures.ThreadPoolExecutor() as executor:
        #futures = [executor.submit(process_resource, path, methods) for path, methods in paths.items()]
        
        # Optionally, wait for all tasks to complete
        #concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

    for path, methods in paths.items():
        process_resource(path, methods)

    final_response["paths"] = paths_response
    return final_response
    

def modify_method(open_api_spec,script, path, method, instructions):
    simplified_spec = get_simplified_spec(open_api_spec)
    required_method = simplified_spec["paths"][path][method]
    output_json_schema = output_json_schema_modify_method()
    user_msg = modify_method_prompt(script,instructions)
    sys_msg = modify_method_sys_msg(method,path,required_method)
    mock_script = generate_structured_output(sys_msg,user_msg, output_json_schema)
    response_json = json.loads(mock_script)
    return response_json
