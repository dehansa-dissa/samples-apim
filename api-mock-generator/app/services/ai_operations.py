from app.utils.helpers import get_simplified_spec,output_json_schema_generate_mocks,output_json_schema_modify_method,output_json_schema_generate_mocks_sim_resource,validate_response
from app.utils.ai_client import generate_structured_output
from app.utils.prompts import generate_mocks_sys_msg,generate_mocks_prompt,modify_method_prompt,modify_method_sys_msg, fix_schema_prompt, generate_mocks_sim_resource_prompt
from app.utils.dev_tools import rec,Consts
import time
import concurrent.futures

import json

def generate_mock_scripts(open_api_spec, config):
    start_time = time.perf_counter()
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
    response_time_ms = int((time.perf_counter() - start_time) * 1000)
    rec.add(Consts.response_time, response_time_ms)
    return response_json

def generate_mock_scripts_sim_resource(open_api_spec, config, sim=False):
    start_time = time.perf_counter()
    simplified_spec = get_simplified_spec(open_api_spec)
    rec.add(Consts.length_of_cleaned_spec, len(str(simplified_spec)))

    paths = simplified_spec.get("paths")
    final_response = {}
    paths_response = {}
    sys_msg = generate_mocks_sys_msg(simplified_spec, config)
    user_msg_len = 0
    sys_msg_len = len(sys_msg)

    # Generate mockDB first
    def generate_mockDB():
        print("Generating mockDB...")
        mockDB_output_json_schema = output_json_schema_generate_mocks_sim_resource(paths, "mockDB")
        user_msg = generate_mocks_sim_resource_prompt(config, "mockDB")
        nonlocal user_msg_len
        user_msg_len += len(user_msg)

        mockDB = generate_structured_output(sys_msg, user_msg, mockDB_output_json_schema)
        mockDB_json = json.loads(mockDB)

        if not validate_response(mockDB_json, mockDB_output_json_schema):
            rec.add(Consts.is_response_schema_valid_1, False)
            print("Retrying mockDB generation...")
            user_msg = fix_schema_prompt(mockDB)
            mockDB = generate_structured_output(None, user_msg, mockDB_output_json_schema)
            mockDB_json = json.loads(mockDB)

            if not validate_response(mockDB_json, mockDB_output_json_schema):
                rec.add(Consts.is_response_schema_valid_2, False)
                return None
            rec.add(Consts.is_response_schema_valid_2, True)

        return mockDB_json

    mockDB_json = generate_mockDB()
    if not mockDB_json:
        return

    final_response.update(mockDB_json)

    # Function to process each resource
    def process_resource(path, methods):
        print(f"Generating mock script for path: {path}")
        output_json_schema = output_json_schema_generate_mocks_sim_resource(paths, path)
        user_msg = generate_mocks_sim_resource_prompt(config, path, mockDB_json)
        nonlocal user_msg_len, sys_msg_len
        user_msg_len += len(user_msg)
        sys_msg_len += len(sys_msg)

        mock_script = generate_structured_output(sys_msg, user_msg, output_json_schema)
        response_json = json.loads(mock_script)

        if not validate_response(response_json, output_json_schema):
            rec.add(Consts.is_response_schema_valid_1, False)
            print(f"Retrying for path: {path}")
            user_msg = fix_schema_prompt(mock_script)
            mock_script = generate_structured_output(None, user_msg, output_json_schema)
            response_json = json.loads(mock_script)

            if not validate_response(response_json, output_json_schema):
                rec.add(Consts.is_response_schema_valid_2, False)
                return
            rec.add(Consts.is_response_schema_valid_2, True)

        paths_response.update(response_json)

    # Process paths
    if sim:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_resource, path, methods) for path, methods in paths.items()]
            concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)
    else:
        for path, methods in paths.items():
            process_resource(path, methods)

    # Finalize response
    final_response["paths"] = paths_response
    rec.add(Consts.length_of_output_schema, len(json.dumps(final_response)))
    rec.add(Consts.response_length, len(json.dumps(final_response)))
    rec.add(Consts.user_msg_length, user_msg_len)
    rec.add(Consts.sys_msg_length, sys_msg_len)

    if not validate_response(final_response, output_json_schema_generate_mocks(simplified_spec)):
        rec.add(Consts.is_response_schema_valid_1, False)
        print("Retrying final response generation...")
        user_msg = fix_schema_prompt(final_response)
        final_response = generate_structured_output(None, user_msg, output_json_schema_generate_mocks(simplified_spec))
        response_json = json.loads(final_response)

        if not validate_response(response_json, output_json_schema_generate_mocks(simplified_spec)):
            rec.add(Consts.is_response_schema_valid_2, False)
            return
        rec.add(Consts.is_response_schema_valid_2, True)

    rec.add(Consts.is_response_schema_valid_1, True)
    rec.add(Consts.deployment_success, True)
    response_time_ms = int((time.perf_counter() - start_time) * 1000)
    rec.add(Consts.response_time, response_time_ms)
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
