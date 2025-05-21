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
from flask import Flask, request
from flask_cors import CORS
import json
import yaml
from prompts import (
    prompt_template_to_validate_query,
    check_for_general_questions_prompt,
    answer_general_questions_prompt,
    prompt_template_to_generate_spec,
    chatbot_prompt_template_generate_suggestions,
    identify_modifications_prompt,
    prompt_template_to_suggest_api_type,
    missing_values_prompt_template,
    chatbot_prompt_template_apiUsecase,
    chatbot_prompt_template_modify_openapi,
    chatbot_prompt_template_graphql
)
from config import r, llm, required_properties

app = Flask(__name__)
CORS(app)


# Validates user input
def validate_user_input(data):
    if data is None:
        return {"error": "Request body must be in JSON format."}, 415
    
    if 'text' not in data:
        return {"error": "Invalid request. The 'text' field is missing or incorrectly named."}, 400
    if not data.get('text', '').strip():
        return {"error": "Please provide the details of the API you would like to create."}, 400

    if 'sessionId' not in data or not data['sessionId']:
        return {"error": "Invalid request. The 'sessionId' field is missing or incorrectly named."}, 400
    if not data.get('sessionId', '').strip():
        return {"error": "Please enter a Session ID."}, 400

    return None, 200


# Retrieves data stored in Redis for a given task ID
def get_task_data(session_id):
    task_data = r.get(session_id)
    return json.loads(task_data) if task_data else {"state": "START", "chat_history": [], "specification": "", "api_type": "", "paths":['No resources']}


# Updates data stored in Redis for a given task ID  
def update_task_data(session_id, state=None, chat_history=None, specification=None, api_type=None, paths=None):
    task_data = get_task_data(session_id)
    
    if state:
        task_data["state"] = state
    if chat_history is not None:
        task_data["chat_history"] = chat_history
    if specification is not None:
        task_data["specification"] = specification
    if api_type is not None:
        task_data["api_type"] = api_type
    if paths is not None:
        task_data["paths"] = paths
    
    r.setex(session_id, 900, json.dumps(task_data))


# Invokes LLM to check user's query's validity'
def validate_query_content(user_input, chat_history):
    prompt_to_validate_query = prompt_template_to_validate_query.format(user_input=user_input, chat_history=chat_history)
    llm_response = llm.invoke(prompt_to_validate_query)
    response = llm_response.content.strip()

    if response == "None":
        response = None

    return response


# Invokes LLM to suggest a type of API for the given use case
def suggest_api_type(user_input, chat_history):   
    prompt_to_suggest_api_type = prompt_template_to_suggest_api_type.format(user_input=user_input, history=chat_history)
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
def generate_missing_values_prompt(api_type, chat_history):
    properties = required_properties.get(api_type, [])

    # If the api_type is not found, fallback to a default list
    if not properties:
        properties = ["name", "version"]

    properties_str = ", ".join(properties)

    missing_values_prompt = missing_values_prompt_template.format(api_type=api_type, history=chat_history, allproperties=properties_str)
    response = llm.invoke(missing_values_prompt)
    missing_values = response.content.strip()

    return missing_values


# Invokes LLM to generate the spec according to API type and provided information
def generate_spec(api_type, final_input, chat_history, specification=None, modification_statements=None, yaml_validation_error = None):
    if api_type == "REST":
        prompt_with_history = chatbot_prompt_template_modify_openapi.format(final_input=final_input, history=chat_history, specification = specification, modification_statements=modification_statements, yaml_validation_error=yaml_validation_error)

    elif api_type == "GraphQL":
        prompt_with_history = chatbot_prompt_template_graphql.format(final_input=final_input, history=chat_history, specification = specification, modification_statements=modification_statements)

    else:
        prompt_with_history = prompt_template_to_generate_spec.format(
            api_type=api_type, 
            final_input=final_input, 
            history=chat_history, 
            specification = specification,
            modification_statements=modification_statements,
            yaml_validation_error=yaml_validation_error
        )
    
    response = llm.invoke(prompt_with_history)
    answer_text = response.content.strip()

    try:
        data = json.loads(answer_text)
        generated_spec = data.get("generated_spec", "")
        resources = data.get("resources", [])

        if api_type != "GraphQL":
            try:
                yaml.safe_load(generated_spec)
            except yaml.YAMLError as e:
                generate_spec(api_type, final_input, chat_history, specification, modification_statements, e)

        return generated_spec, resources
    
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return None


# Invokes LLM to generate suggestions for more modifications
def generate_suggestions(api_type, chat_history):
    prompt = chatbot_prompt_template_generate_suggestions.format(api_type=api_type, history=chat_history)
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


# Invokes LLM to check user's query for any general questions or modifications
def check_question_or_task(user_input, chat_history, specification):
    prompt_to_check_for_generalQuestions = check_for_general_questions_prompt.format(user_input=user_input, chat_history=chat_history, specification=specification)
    response = llm.invoke(prompt_to_check_for_generalQuestions)
    question_or_task_data = response.content.strip()

    question_or_task = json.loads(question_or_task_data)
    answer_general_question = None
    if question_or_task.get('answer') == "None":
        answer_general_question = None
    else:
        answer_general_question = question_or_task.get('answer')

    general_task = None
    if question_or_task.get('task_assigned') == "None":
        general_task = None
    else:
        general_task = question_or_task.get('task_assigned')

    return answer_general_question, general_task


# Invokes LLM to answer user's general question
def form_answer_general_question(user_input, chat_history, specification):
    prompt_to_answer_general_questions = answer_general_questions_prompt.format(user_input=user_input, chat_history=chat_history, specification=specification)
    response = llm.invoke(prompt_to_answer_general_questions)
    answer_to_question = response.content.strip()
    return answer_to_question


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
def generate_payload(api_type, chat_history, specification):
    if not isinstance(api_type, str):
        api_type = str(api_type)

    if api_type.upper() == "REST":
        file_path = 'restPayloadExample.txt'

    elif api_type == "GraphQL":
        file_path = 'graphqlPayloadExample.txt'

    elif api_type == "WebSocket":
        file_path = 'websocketPayloadExample.txt'

    elif api_type == "WebSub":
        file_path = 'websubPayloadExample.txt'

    elif api_type == "SSE":
        # file_path = 'ssePayloadExample.txt'
        file_path = 'restPayloadExample.txt'

    content = read_file(file_path)

    prompt_with_history = chatbot_prompt_template_apiUsecase.format(history=chat_history, specification=specification, api_type=api_type, content=content)
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


# Endpoint which calls relevant methods for generating the specifications based on the states
@app.route('/chat', methods=['POST'])
def generate():
    data = request.get_json(silent=True)
    
    error_response, status_code = validate_user_input(data)
    if status_code != 200:
        return error_response, status_code
    
    user_input = data.get('text', '').strip()
    session_id = data.get('sessionId', '')
    
    task_data = get_task_data(session_id)
    api_type = task_data.get("api_type", "")
    specification = task_data["specification"]
    paths = task_data["paths"]
    chat_history = task_data["chat_history"]
    
    update_task_data(session_id, chat_history=chat_history)

    response = validate_query_content(user_input, chat_history)
    if response is not None:
        chat_history.append({"user_input": user_input})
        chat_history.append({"response to above user_input": response})

        if specification == "":
            return {
                "backendResponse": None,
                "isSuggestions": False,
                "typeOfApi": '',
                "code": '',
                "paths": ['No Resources'],
                "apiTypeSuggestion": response,
                "missingValues": None,
                "state": None
            }, 200
        else:
            return {
                "backendResponse": None,
                "isSuggestions": False,
                "typeOfApi": api_type,
                "code": specification,
                "paths": paths,
                "apiTypeSuggestion": response,
                "missingValues": None,
                "state": "COMPLETE"
            }, 200
    
    if task_data['state'] == "START":
        api_type, api_type_suggestion = suggest_api_type(user_input, chat_history)
        chat_history.append({"user_input": user_input})
        chat_history.append({"API TYPE": f"Create this type of API: {api_type}"})
        update_task_data(session_id, chat_history=chat_history, state="IN_PROGRESS", api_type=api_type)

        specification, paths = generate_spec(api_type, user_input, chat_history, None, None, None)
        update_task_data(session_id, chat_history=chat_history, state="COMPLETE", specification=specification, paths=paths)
        
        return {
            "backendResponse": None,                                                 # set to None so it does not display suggestions on UI
            "isSuggestions": False,                                                  # set to False so it does not display suggestions on UI
            "typeOfApi": api_type,
            "code": specification,
            "paths": paths,
            "apiTypeSuggestion": api_type_suggestion,
            "missingValues": None,                                                   # set to None so it does not display two chat bubble on the UI
            "state": "COMPLETE"
        }, 200
    
    elif task_data['state'] == "COMPLETE":
        answer_general_question, general_task = check_question_or_task(user_input, chat_history, specification)

        response = {
            "backendResponse": None,
            "isSuggestions": False,
            "typeOfApi": api_type,
            "code": specification,
            "paths": paths,
            "missingValues": None,
            "state": "COMPLETE"
        }
        
        if general_task is not None:
            chat_history.append({"API TYPE": f"Create this type of API: {api_type}"})
            api_type, api_type_suggestion = suggest_api_type(user_input, chat_history)

            chat_history.append({"user_input": user_input})
            chat_history.append({"API TYPE": f"Create this type of API: {api_type}"})
            update_task_data(session_id, chat_history=chat_history, api_type=api_type)
            
            modification_check_result = check_for_modifications(user_input)
            specification, paths = generate_spec(api_type, user_input, chat_history, specification, modification_check_result, None)
            update_task_data(session_id, specification=specification, paths=paths)
            
            response["apiTypeSuggestion"] = (
                answer_general_question
                if answer_general_question
                else api_type_suggestion
            )
            
        if answer_general_question is not None:
            answer_to_question = form_answer_general_question(user_input, chat_history, specification)
            chat_history.append(answer_to_question)
       
            response["apiTypeSuggestion"] = answer_to_question
            
        response["typeOfApi"] = api_type
        response["code"] = specification
        response["paths"] = paths
        
        return response, 200
    
    return {"error": "Invalid state or input"}, 400


# Endpoint which calls relevant methods for creating the API payload
@app.route('/generate-api-payload', methods=['POST'])
def createapiinportal():
    data = request.get_json()
    session_id = str(data.get('sessionId', ''))

    task_data = get_task_data(session_id)
    api_type = task_data["api_type"]
    chat_history = task_data["chat_history"]
    specification = task_data["specification"]

    generated_payload = generate_payload(api_type, chat_history, specification)

    return json.loads(generated_payload)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
