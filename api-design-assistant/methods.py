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
from prompts import (
    prompt_template_to_suggest_api_type,
    prompt_template_to_check_confirmation,
    missing_values_prompt_template,
    prompt_template_to_generate_spec,
    identify_modifications_prompt,
    chatbot_prompt_template_summarize_openAPI,
    chatbot_prompt_template_generate_suggestions,
    chatbot_prompt_template_apiUsecase
)
from api_utils import publish_api
from config import llm, memory, token, required_properties

app = Flask(__name__)
CORS(app)

# In-memory storage for task progress and state management
task_states = {}

# Updates task state
def update_task_state(task_id, state, message=""):
    task_states[task_id] = {"state": state, "message": message}


# Validates user input
def validate_user_input(data):
    if not data:
        return {"error": "User input is required"}, 400
    user_input = data.get('user_input', '')
    if not user_input:
        return {"error": "Text field is required"}, 400
    return None, 200


# Invokes LLM to suggest a type of API for the given use case or confirm usage of API type
def suggest_api_type(user_input):
    prompt_to_suggest_api_type = prompt_template_to_suggest_api_type.format(user_input=user_input)
    response = llm.invoke(prompt_to_suggest_api_type)
    api_type = response.content
    return api_type


# Invokes LLM if the user has confirmed api type or provided an alternative API type
def check_confirmation(user_input):
    history_str = memory.buffer
    prompt_to_check_confirmation = prompt_template_to_check_confirmation.format(user_input=user_input, history=history_str)
    response = llm.invoke(prompt_to_check_confirmation)
    api_type = response.content
    return api_type


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
    print(missing_values)
    return missing_values


# Invokes LLM to generate the spec according to API type and provided information
def generate_spec(api_type, final_input, modification_statements=None):
    history_str = memory.buffer
    
    prompt_with_history = prompt_template_to_generate_spec.format(
        api_type=api_type, 
        final_input=final_input, 
        history=history_str, 
        modification_statements=modification_statements
    )
    
    response = llm.invoke(prompt_with_history)
    answer_text = response.content.strip()
    
    # Initialize variables
    generated_spec = None
    resources = None
    
    # Split the response into lines
    lines = answer_text.split('\n')
    
    # Find the resources
    for line in lines:
        if line.lower().startswith('resources:'):
            # Extract resources, removing the 'resources:' prefix and splitting by comma
            resources = [resource.strip() for resource in line.split(':', 1)[1].split(',')]
            break
    
    # If no resources found by parsing, try extracting from the spec
    if not resources:
        try:
            # Attempt to extract resources from paths in the spec
            import yaml
            spec_dict = yaml.safe_load(answer_text)
            resources = list(spec_dict.get('paths', {}).keys())
        except Exception as e:
            print(f"Error extracting resources: {e}")
            resources = None
    
    # Extract the generated spec (everything between 'openapi:' start and 'resources:' line)
    spec_lines = []
    in_spec = False
    for line in lines:
        if line.lower().startswith('openapi:'):
            in_spec = True
        
        if in_spec:
            if line.lower().startswith('resources:'):
                break
            spec_lines.append(line)
    
    # Join the spec lines
    generated_spec = '\n'.join(spec_lines).strip()
    
    # Optional: print and summarize (keep existing functionality)
    if generated_spec:
        print("generated_spec "+generated_spec)
        summarize_openAPI(generated_spec)
    
    return generated_spec, resources


# Invokes LLM to summarize spec to be added to memory
def summarize_openAPI(openAPI):
    prompt_with_history = chatbot_prompt_template_summarize_openAPI.format(openAPI=openAPI)
    response = llm.invoke(prompt_with_history)
    summary = response.content
    memory.save_context({"input": f"Human prompt: {summary}"}, {"output": ""})
    return summary


# Invokes LLM to generate suggestions for more modifications
def generate_suggestions(user_input):
    history_str = memory.buffer
    prompt = chatbot_prompt_template_generate_suggestions.format(user_input=user_input, history=history_str)
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


# Invokes LLM to generates the payload for API creation based on user's query
def process_llm_response():
    history_str = memory.buffer
    prompt_with_history = chatbot_prompt_template_apiUsecase.format(history=history_str)
    response = llm.invoke(prompt_with_history)
    answer_text = response.content

    print("generated payload - " + answer_text)
    save_payload('generated_payload.json', answer_text)
    return answer_text


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


# Method to send the payload to the API call
def try_publish_api(generated_payload, retries=1):
    result = publish_api(generated_payload, token)

    # If there's an error in creating the API, retry the process
    if "error" in result and retries > 0:
        print(f"Error occurred: {result['error']}. Retrying...")
        new_generated_payload = process_llm_response()
        return try_publish_api(new_generated_payload, retries - 1)
    
    return result


# Endpoint which calls relevant methods based on the states
@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    user_input = data.get('user_input')
    task_id = data.get('task_id', '')
    
    error_response, status_code = validate_user_input(data)
    if error_response:
        return error_response, status_code

    if not task_id:
        return {"error": "Task ID is required"}, 400
    
    memory.save_context({"input": f"Human prompt: {user_input}"}, {"output": ""})

    # Step 1: Check or suggest API type
    if task_id not in task_states or task_states[task_id]['state'] == "START":
        api_suggestion = suggest_api_type(user_input)
        update_task_state(task_id, "AWAITING_CONFIRMATION", api_suggestion)
        isSuggestions = False

        return {
            "backendResponse": api_suggestion,
            "isSuggestions":isSuggestions,
            "state": "AWAITING_CONFIRMATION"
        }, 200

    # Step 2: Confirm or select API type
    elif task_states[task_id]['state'] == "AWAITING_CONFIRMATION":
        confirmed_api_type = check_confirmation(user_input) 
        task_states[task_id]['api_type'] = confirmed_api_type
        memory.save_context({"input": f"Create this type of API: {confirmed_api_type}"}, {"output": ""})    
        update_task_state(task_id, "CHECKING_MISSING_PROPERTIES", confirmed_api_type)

        # Step 3: Check for missing properties
        api_type = task_states[task_id].get('message')
        missing_values_prompt = generate_missing_values_prompt(api_type)
        update_task_state(task_id, "AWAITING_MISSING_PROPERTIES", missing_values_prompt)
        isSuggestions = False

        return {
            "backendResponse": missing_values_prompt,
            "isSuggestions":isSuggestions,
            "state": "AWAITING_MISSING_PROPERTIES"
        }, 200
    
    # Step 4: Generate OpenAPI spec
    elif task_states[task_id]['state'] == "AWAITING_MISSING_PROPERTIES":
        api_type = task_states[task_id].get('api_type')
        final_input = user_input

        modification_check_result = check_for_modifications(final_input)
        openapispec,paths = generate_spec(api_type, final_input, modification_check_result) 

        update_task_state(task_id, "COMPLETE")
        memory.save_context({"input": ""}, {"output": openapispec})
        print(memory.buffer)

        suggestions = generate_suggestions(user_input)
        isSuggestions = True

        return {
            "backendResponse": suggestions,
            "isSuggestions":isSuggestions,
            "code": openapispec,
            "paths":paths,
            "state": "COMPLETE"
        }, 200

    # Step 4: Generate OpenAPI spec
    elif task_states[task_id]['state'] == "COMPLETE":
        api_type = task_states[task_id].get('api_type')
        final_input = user_input

        modification_check_result = check_for_modifications(final_input)
        openapispec,paths = generate_spec(api_type, final_input, modification_check_result) 
        print("after modification: " + openapispec)

        memory.save_context({"input": ""}, {"output": openapispec})
        print(memory.buffer)
        suggestions = generate_suggestions(user_input)
        isSuggestions = True

        return {
            "backendResponse": suggestions,
            "isSuggestions":isSuggestions,
            "code": openapispec,
            "paths":paths,
            "state": "COMPLETE"
        }, 200
    
    return {"error": "Invalid state or input"}, 400

# Endpoint which creates the API in the Publisher Portal
@app.route('/createapiinportal', methods=['POST'])
def createapiinportal():
    generated_payload = process_llm_response() 
    result = try_publish_api(generated_payload)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)