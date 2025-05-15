from app.utils.helpers import get_simplified_spec,output_json_schema_generate_mocks,output_json_schema_modify_method,output_json_schema_generate_mocks_sim_resource,validate_schema, batch_paths_by_method_count
from app.utils.ai_client import get_structured_output_with_validation,fix_schema
from app.utils.prompts import generate_mocks_sys_msg,generate_mocks_prompt,modify_method_prompt,modify_method_sys_msg, generate_mocks_batch_prompt
import time
import json

from app.utils.logger import logger
import json

from app.utils.constants import BATCH_SIZE, PROCESS_RESOURCE_DELAY

def generate_mock_scripts(open_api_spec, config, batch_size = BATCH_SIZE): # add configurable
    try:
        def generate_mock_scripts_at_once(simplified_spec, config):
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
                prompt_messages = [{"role": "system", "content": sys_msg},
                                {"role": "user", "content": generate_mocks_batch_prompt(config, ["mockDB"])}]
                mockDB_json = get_structured_output_with_validation(prompt_messages,
                                                                    output_json_schema_generate_mocks_sim_resource(paths, ["mockDB"]))
                if not mockDB_json:
                    logger.error("Failed to generate mockDB.")
                    raise ValueError("Failed to generate mockDB.")
                return mockDB_json

            mockDB_json = generate_mockDB()
            final_response.update(mockDB_json)

            # Function to process each paths_batch
            def process_resource(paths_batch):
                prompt_messages = [{"role": "system", "content": sys_msg},
                                {"role": "user", "content": generate_mocks_batch_prompt(config, paths_batch, mockDB_json)}]
                response_json = get_structured_output_with_validation(prompt_messages,
                                                                    output_json_schema_generate_mocks_sim_resource(paths, paths_batch))
                paths_response.update(response_json)

            for paths_batch in batched_paths:
                process_resource(paths_batch)
                time.sleep(PROCESS_RESOURCE_DELAY)

            # Finalize response
            final_response["paths"] = paths_response
            final_output_schema = output_json_schema_generate_mocks(simplified_spec)
            if validate_schema(final_response, final_output_schema):
                return final_response
            else:
                fixed_response = fix_schema(json.dumps(final_response),final_output_schema)
                if fixed_response is None:
                    logger.error("Schema validation failed after retries.")
                    raise ValueError("Schema validation failed after retries.")
                return fixed_response

        simplified_spec = get_simplified_spec(open_api_spec, config.get("usePreviousScripts", False))
        batched_paths = batch_paths_by_method_count(simplified_spec.get("paths"), batch_size)
        if len(batched_paths) <= 1:
            return generate_mock_scripts_at_once(simplified_spec, config)
        else:
            return generate_mock_scripts_batch_wise(simplified_spec,config,batched_paths)
    except Exception as e:
        logger.error(f"Error in generate_mock_scripts: {e}")
        raise

def modify_method(open_api_spec,script, path, method, instructions, is_default_script = False):
    try:
        simplified_spec = get_simplified_spec(open_api_spec)
        try:
            required_method = simplified_spec["paths"][path][method]
        except KeyError as e:
            logger.error(f"Key error accessing simplified_spec paths: missing key {e} for path '{path}' and method '{method}'")
            raise KeyError(f"Missing key {e} in simplified_spec paths for path '{path}' and method '{method}'")
        prompt_messages = [{"role": "system", "content": modify_method_sys_msg(method,path,required_method)},
                           {"role": "user", "content": modify_method_prompt(script,instructions, is_default_script)}]
        response_json = get_structured_output_with_validation(prompt_messages,output_json_schema_modify_method())
        if not response_json or "modified_script" not in response_json:
            logger.error("Invalid response received from get_structured_output_with_validation in modify_method")
            raise ValueError("Invalid response received from modify_method operation")
        return response_json
    except Exception as e:
        logger.error(f"Error in modify_method: {e}")
        raise
