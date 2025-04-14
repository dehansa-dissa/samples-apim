from app.utils.helpers import get_simplified_spec,output_json_schema_generate_mocks,output_json_schema_modify_method,output_json_schema_generate_mocks_sim_resource,validate_schema, batch_paths_by_method_count
from app.utils.ai_client import get_structured_output_with_validation,fix_schema
from app.utils.prompts import generate_mocks_sys_msg,generate_mocks_prompt,modify_method_prompt,modify_method_sys_msg, generate_mocks_sim_resource_prompt
import time
import json

def generate_mock_scripts(open_api_spec, config, batch_size = 15):
    def generate_mock_scripts_at_once(open_api_spec, config):
        simplified_spec = get_simplified_spec(open_api_spec)
        output_json_schema = output_json_schema_generate_mocks(simplified_spec)
        prompt_messages = [{"role": "system", "content": generate_mocks_sys_msg(simplified_spec,config)},
                        {"role": "user", "content": generate_mocks_prompt(config)}]
        response_json = get_structured_output_with_validation(prompt_messages, output_json_schema)
        return response_json

    def generate_mock_scripts_batch_wise(simplified_spec, config, batched_paths):
        paths = simplified_spec.get("paths")
        final_response = {}
        paths_response = {}
        sys_msg = generate_mocks_sys_msg(simplified_spec, config)

        # Generate mockDB first
        def generate_mockDB():
            print("Generating mockDB...")
            prompt_messages = [{"role": "system", "content": sys_msg},
                            {"role": "user", "content": generate_mocks_sim_resource_prompt(config, ["mockDB"])}]
            mockDB_json = get_structured_output_with_validation(prompt_messages,
                                                                output_json_schema_generate_mocks_sim_resource(paths, ["mockDB"]))
            return mockDB_json

        mockDB_json = generate_mockDB()
        if not mockDB_json:
            return

        final_response.update(mockDB_json)

        # Function to process each paths_batch
        def process_resource(paths_batch):
            print(f"Generating mock script for paths: {paths_batch}")
            prompt_messages = [{"role": "system", "content": sys_msg},
                            {"role": "user", "content": generate_mocks_sim_resource_prompt(config, paths_batch, mockDB_json)}]
            response_json = get_structured_output_with_validation(prompt_messages,
                                                                output_json_schema_generate_mocks_sim_resource(paths, paths_batch))
            time.sleep(1)
            paths_response.update(response_json)

        for paths_batch in batched_paths:
            process_resource(paths_batch)


        # Finalize response
        final_response["paths"] = paths_response
        final_output_schema = output_json_schema_generate_mocks(simplified_spec)
        if validate_schema(final_response, final_output_schema):
            return final_response
        else:
            return fix_schema(json.dumps(final_response),final_output_schema)

    simplified_spec = get_simplified_spec(open_api_spec)
    batched_paths = batch_paths_by_method_count(simplified_spec.get("paths"), batch_size)
    print(batched_paths)
    if len(batched_paths) <= 1:
        return generate_mock_scripts_at_once(simplified_spec, config)
    else:
        return generate_mock_scripts_batch_wise(simplified_spec,config,batched_paths)


def modify_method(open_api_spec,script, path, method, instructions):
    simplified_spec = get_simplified_spec(open_api_spec)
    required_method = simplified_spec["paths"][path][method]
    prompt_messages = [{"role": "system", "content": modify_method_sys_msg(method,path,required_method)},
                       {"role": "user", "content": modify_method_prompt(script,instructions)}]
    response_json = get_structured_output_with_validation(prompt_messages,output_json_schema_modify_method())
    return response_json
