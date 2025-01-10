"""
 Copyright (c) 2024, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.

  This software is the property of WSO2 LLC. and its suppliers, if any.
  Dissemination of any information or reproduction of any material contained
  herein is strictly forbidden, unless permitted by WSO2 in accordance with
  the WSO2 Commercial License available at http://wso2.com/licenses.
  For specific language governing the permissions and limitations under
  this license, please see the license as well as any agreement you’ve
  entered into with WSO2 governing the purchase of this software and any
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from prompts import (
    prompt_template_to_generate_spec,
    chatbot_prompt_template_summarize_code,
    chatbot_prompt_template_generate_suggestions,
    identify_modifications_prompt,
    prompt_template_to_suggest_api_type,
    missing_values_prompt_template,
    chatbot_prompt_template_apiUsecase,
    chatbot_prompt_template_modify_openapi,
    chatbot_prompt_template_graphql
)
from api_utils import publish_api
from config import llm, memory, token, required_properties

app = Flask(__name__)
CORS(app)

task_id = None

# In-memory storage for task progress and state management
task_states = {}


# Updates task state
def update_task_state(new_task_id, state, message="", api_type=None):
    global task_id  # Declare task_id as global to update it
    task_id = new_task_id
    if task_id not in task_states:
        task_states[task_id] = {}
    task_states[task_id]["state"] = state
    task_states[task_id]["message"] = message
    if api_type:
        task_states[task_id]["api_type"] = api_type


# Validates user input
def validate_user_input(data):
    user_input = data.get('text', '')
    if not user_input:
        return {"error": "Hello! Please provide the details of the API you would like to create."}, 400
    return None, 200


# Invokes LLM to suggest a type of API for the given use case
def suggest_api_type(user_input):
    history_str = memory.buffer
    
    prompt_to_suggest_api_type = prompt_template_to_suggest_api_type.format(user_input=user_input, history=history_str)
    response = llm.invoke(prompt_to_suggest_api_type)
    answer_text = response.content.strip()

    try:
        data = json.loads(answer_text)
        api_type = data.get("api_type", "")
        api_type_suggestion = data.get("api_type_suggestion", "")

        return api_type, api_type_suggestion
    
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return None


# Invokes LLM to ask the user for the missing properties
def generate_missing_values_prompt(api_type):
    history_str = memory.buffer

    properties = required_properties.get(api_type, [])

    # If the api_type is not found, fallback to a default list
    if not properties:
        properties = ["name", "version"]

    properties_str = ", ".join(properties)

    missing_values_prompt = missing_values_prompt_template.format(api_type=api_type, history=history_str, allproperties=properties_str)
    response = llm.invoke(missing_values_prompt)
    missing_values = response.content.strip()

    return missing_values


# summarize openAPI spec to be added to memory
def summarize_code(gen_spec):
    prompt_with_history = chatbot_prompt_template_summarize_code.format(gen_spec=gen_spec)
    response = llm.invoke(prompt_with_history)
    summary = response.content
    memory.save_context({"input": f"Human prompt: {summary}"}, {"output": ""})

    return summary


# Invokes LLM to generate the spec according to API type and provided information
def generate_spec(api_type, final_input, modification_statements=None):
    history_str = memory.buffer
    
    if api_type == "REST":
        prompt_with_history = chatbot_prompt_template_modify_openapi.format(history=history_str, modification_statements=modification_statements)

    elif api_type == "GraphQL":
        prompt_with_history = chatbot_prompt_template_graphql.format(history=history_str, modification_statements=modification_statements)

    else:
        prompt_with_history = prompt_template_to_generate_spec.format(
            api_type=api_type, 
            final_input=final_input, 
            history=history_str, 
            modification_statements=modification_statements
        )
    
    response = llm.invoke(prompt_with_history)
    answer_text = response.content.strip()

    try:
        data = json.loads(answer_text)
        generated_spec = data.get("generated_spec", "")
        resources = data.get("resources", [])

        summarize_code(generated_spec)

        return generated_spec, resources
    
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return None


# Invokes LLM to generate suggestions for more modifications
def generate_suggestions(api_type):
    history_str = memory.buffer
    prompt = chatbot_prompt_template_generate_suggestions.format(api_type=api_type, history=history_str)
    response = llm.invoke(prompt)

    suggestions = response.content.strip().lower()
    return suggestions


# Invokes LLM to check user's query for any modification statements
def check_for_modifications(user_input):
    prompt_to_check_for_modifications = identify_modifications_prompt.format(user_input=user_input)
    response = llm.invoke(prompt_to_check_for_modifications)
    modification_status = response.content.lower()
    
    modification_statements = None
    if modification_status == "no modifications":
        modification_statements = None
    else:
        modification_statements = modification_status

    return modification_statements


# Method to read the payload example text file
def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# Invoke LLM to generate the payload for the API
def generate_payload(api_type):
    if not isinstance(api_type, str):
        api_type = str(api_type)

    if api_type.upper() == "REST":
        file_path = 'api-design-assistant/restPayloadExample.txt'

    elif api_type == "GraphQL":
        file_path = 'api-design-assistant/graphqlPayloadExample.txt'

    elif api_type == "WebSocket":
        file_path = 'api-design-assistant/websocketPayloadExample.txt'

    elif api_type == "WebSub":
        file_path = 'api-design-assistant/websubPayloadExample.txt'

    elif api_type == "SSE":
        # file_path = 'api-design-assistant/ssePayloadExample.txt'
        file_path = 'api-design-assistant/restPayloadExample.txt'

    content = read_file(file_path)

    history_str = memory.buffer
    prompt_with_history = chatbot_prompt_template_apiUsecase.format(history=history_str, api_type=api_type, content=content)
    response = llm.invoke(prompt_with_history)
    gen_payload = response.content

    save_payload('generated_payload.json', gen_payload)
    return gen_payload


# Saves payload as a file
def save_payload(filename, content):
    try:
        with open(filename, 'w') as yaml_file:
            yaml_file.write(content)
    except IOError as e:
        print(f"Failed to save payload: {e}")


# Displays payload in the console
def display_payload(content):
    for line in content.split('\n'):
        print(line)


# Method to send payload to publisher portal to create API
def try_publish_api(generated_payload, api_type, retries=1):
    result = publish_api(generated_payload, token)

    # If there's an error in creating the API, retry the process
    if "error" in result and retries > 0:
        print(f"Error occurred: {result['error']}. Retrying...")
        new_generated_payload = generate_payload(api_type)
        return try_publish_api(new_generated_payload, retries - 1)
    
    return result


# Endpoint which calls relevant methods for generating the specifications based on the states
@app.route('/api-design', methods=['POST'])
def generate():
    data = request.get_json()
    
    user_input = data.get('text', '').strip()
    task_id = data.get('task_id', '')
    
    error_response, status_code = validate_user_input(data)
    if error_response:
        return error_response, status_code

    if not task_id:
        return {"error": "Task ID is required"}, 400
    
    memory.save_context({"input": f"Human prompt: {user_input}"}, {"output": ""})

    if task_id not in task_states or task_states[task_id]['state'] == "START":
        api_type, api_type_suggestion = suggest_api_type(user_input)

        update_task_state(task_id, "IN_PROGRESS", api_type, api_type=api_type)
        memory.save_context({"input": f"Create this type of API: {api_type}"}, {"output": ""})

        modification_check_result = None
        openapispec, paths = generate_spec(api_type, user_input, modification_check_result)

        update_task_state(task_id, "COMPLETE")
        suggestions = generate_suggestions(api_type)
        isSuggestions = True
        missing_values_prompt = generate_missing_values_prompt(api_type)

        return {
            "backendResponse": suggestions,
            "isSuggestions": isSuggestions,
            "typeOfApi": api_type,
            "code": openapispec,
            "paths": paths,
            "apiTypeSuggestion": api_type_suggestion,
            "missingValues": missing_values_prompt,
            "state": "COMPLETE"
        }, 200

    elif task_states[task_id].get('state') == "COMPLETE":
        api_type = task_states[task_id].get('api_type')
        memory.save_context({"input": f"Create this type of API: {api_type}"}, {"output": ""})

        api_type, api_type_suggestion = suggest_api_type(user_input)

        update_task_state(task_id, "COMPLETE", api_type, api_type=api_type)
        memory.save_context({"input": f"Create this type of API: {api_type}"}, {"output": ""})

        modification_check_result = check_for_modifications(user_input)
        openapispec, paths = generate_spec(api_type, user_input, modification_check_result)

        suggestions = generate_suggestions(api_type)
        isSuggestions = True
        missing_values_prompt = generate_missing_values_prompt(api_type)

        return {
            "backendResponse": suggestions,
            "isSuggestions": isSuggestions,
            "typeOfApi": api_type,
            "code": openapispec,
            "paths": paths,
            "apiTypeSuggestion": api_type_suggestion,
            "missingValues": missing_values_prompt,
            "state": "COMPLETE"
        }, 200
    
    return {"error": "Invalid state or input"}, 400


# Endpoint which calls relevant methods for creating the API in the Publisher Portal
@app.route('/create-api', methods=['POST'])
def createapiinportal():
    global task_id  # Use the global task_id
    if task_id is None or task_id not in task_states:
        return jsonify({"error": "Invalid task_id or task_id not set"}), 400
    
    api_type = task_states[task_id].get('api_type')
    if not api_type:
        return jsonify({"error": "api_type not found for the task"}), 400
    
    generated_payload = generate_payload(api_type) 
    result = try_publish_api(generated_payload, api_type)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
