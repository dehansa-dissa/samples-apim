from config.settings import client, deployment_name
from app.utils.helpers import validate_schema
from app.utils.prompts import fix_schema_prompt
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from app.utils.logger import logger
import time
import json

from app.utils.constants import RETRY_COUNT, RETRY_DELAY, TIMEOUT, TEMPERATURE

def generate_structured_output(messages, retry_count=RETRY_COUNT, retry_delay=RETRY_DELAY, timeout=TIMEOUT):
    """
    Generate structured output from the AI client with retries and timeout.

    Args:
        messages (list): List of message dicts to send to the AI client.
        retry_count (int, optional): Number of retry attempts. Defaults to RETRY_COUNT.
        retry_delay (int, optional): Delay between retries in seconds. Defaults to RETRY_DELAY.
        timeout (int, optional): Timeout for each attempt in seconds. Defaults to TIMEOUT.

    Returns:
        str: The content of the AI client's response.

    Raises:
        TimeoutError: If all retry attempts time out.
        Exception: For other errors during API calls.
    """
    def call_api():
        return client.chat.completions.create(
            model=deployment_name,
            response_format={"type": "json_object"},
            messages=messages,
            temperature=TEMPERATURE
        )

    last_exception = None
    with ThreadPoolExecutor(max_workers=1) as executor:
        for attempt in range(retry_count):
            future = executor.submit(call_api)
            try:
                response = future.result(timeout=timeout)
                return response.choices[0].message.content
            except TimeoutError:
                logger.warning(f"Attempt {attempt + 1} timed out after {timeout} seconds.")
                last_exception = TimeoutError(f"Timeout after {timeout} seconds")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed with error: {e}")
                last_exception = e
            time.sleep(retry_delay)
    logger.error(f"All {retry_count} attempts failed.")
    raise last_exception
    
def fix_schema(response,schema,retry_count = 1):
    """
    Attempt to fix a response to match a given schema by retrying with prompts.

    Args:
        response (str): The response string to fix.
        schema (str): The JSON schema to validate against.
        retry_count (int, optional): Number of retry attempts. Defaults to 1.

    Returns:
        dict or None: The fixed response as a JSON dict if successful, else None.
    """
    retries = 0
    logger.warning(f"Validation failed")
    while retry_count > retries:
        logger.info(f"Retrying validation {retries+1}.")
        fix_schema_messages = [{"role": "user", "content": fix_schema_prompt(response)},
                               {"role": "user", "content": f"Use the following schema for the output: '{schema}'"}]
        response = generate_structured_output(fix_schema_messages)
        response_json = json.loads(response)
        if validate_schema(response_json, schema):
            logger.info(f"Validation successful after {retries+1} retries.")
            return response_json
        retries += 1
    return

from app.utils.logger import logger
import json

def get_structured_output_with_validation(prompt_messages, schema):
    """
    Generate structured output from the AI client and validate against a schema.

    Args:
        prompt_messages (list): List of prompt message dicts.
        schema (str): JSON schema string to validate the response.

    Returns:
        dict: Validated JSON response.

    Raises:
        ValueError: If schema validation fails after retries.
        Exception: For other unexpected errors.
    """
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
