from config.settings import client, deployment_name
from app.utils.helpers import validate_schema
from app.utils.prompts import fix_schema_prompt
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import time
import json

def generate_structured_output(messages, retry_count=1, retry_delay=1, timeout=60): # configurables
    def call_api():
        return client.chat.completions.create(
            model=deployment_name,
            response_format={"type": "json_object"},
            messages=messages,
            temperature=0.7 # configurable
        )

    last_exception = None
    with ThreadPoolExecutor(max_workers=1) as executor:
        for attempt in range(retry_count):
            future = executor.submit(call_api)
            try:
                response = future.result(timeout=timeout)
                print("response:\n", response.choices[0].message.content, "\n")
                return response.choices[0].message.content
            except TimeoutError:
                print(f"Attempt {attempt + 1} timed out after {timeout} seconds.")
                last_exception = TimeoutError(f"Timeout after {timeout} seconds")
            except Exception as e:
                print(f"Attempt {attempt + 1} failed with error: {e}")
                last_exception = e
            time.sleep(retry_delay)
    print(f"All {retry_count} attempts failed.")
    raise last_exception
    
def fix_schema(response,schema,retry_count = 1):
    retries = 0
    print(f"Validation failed")
    while retry_count > retries:
        print(f"Retrying validation {retries+1}.")
        fix_schema_messages = [{"role": "user", "content": fix_schema_prompt(response)},
                               {"role": "user", "content": f"Use the following schema for the output: '{schema}'"}]
        response = generate_structured_output(fix_schema_messages)
        response_json = json.loads(response)
        if validate_schema(response_json, schema):
            print(f"Validation successful after {retries+1} retries.")
            return response_json
        retries += 1
    return

from app.utils.logger import logger
import json

def get_structured_output_with_validation(prompt_messages, schema):
    try:
        prompt_messages.append({"role": "user", "content": f"Use the following schema for the output: '{schema}'"})
        response = generate_structured_output(prompt_messages)
        response_json = json.loads(response)
        if validate_schema(response_json, schema):
            return response_json
        else: 
            fixed_response = fix_schema(response,schema)
            if fixed_response is None:
                logger.error("Schema validation failed after retries.")
                raise ValueError("Schema validation failed after retries.")
            return fixed_response
    except Exception as e:
        logger.error(f"Unexpected error in get_structured_output_with_validation: {e}")
        raise
        