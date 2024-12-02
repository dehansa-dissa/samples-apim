from flask import Flask, request, Response, jsonify
import json
from flask_cors import CORS
import re
from prompts import (
    chatbot_prompt_template_swagger,
    chatbot_prompt_template_apiUsecase,
    chatbot_prompt_template_apiPubPortal,
    classification_prompt_template,
    chatbot_prompt_template_modify_swagger,
    # identify_modifications_prompt_template,
    identify_modifications_prompt,
    missing_values_prompt_template,
    chatbot_prompt_template_create_api_confirmation,
    chatbot_prompt_template_generate_suggestions,
    chatbot_prompt_template_summarize_openAPI,
    prompt_template_to_suggest_api_type,
    prompt_template_to_check_confirmation,
    prompt_template_to_generate_spec
)
from api_utils import (
    modify_api,
    fetch_api_details,
    publish_api
)
from config import llm, memory, token, required_API_properties, modify_synonyms, required_properties

app = Flask(__name__)
CORS(app) 

# task_state = {}
swagger_payload = "" 

# Generate new payload for API with modifications
def generate_payload(api_id, api_details, modification_statements):
    api_details_str = "\n".join(f"{key}: {value}" for key, value in api_details.items())
    prompt_with_details = chatbot_prompt_template_apiPubPortal.format(api_details=api_details_str, modification_statements=modification_statements)
    
    response = llm.invoke(prompt_with_details)
    generated_payload = response.content

    save_payload('modifiedPayloadPortal.json', generated_payload)
    modify_api_question(api_id, generated_payload)



def save_payload(filename, content):
    try:
        with open(filename, 'w') as yaml_file:
            yaml_file.write(content)
    except IOError as e:
        print(f"Failed to save payload: {e}")


def display_payload(content):
    for line in content.split('\n'):
        print(line)


# Prompts the user if they would like to create a new API
def modify_api_question(api_id, generated_payload):
    publish_decision = input("Do you want to publish the API to the portal? (yes/no): ").strip().lower()
    
    if publish_decision == "yes":
        modify_api(api_id, generated_payload, token)
    else:
        user_input = input("Enter your API use case or type a synonym of 'modify' to include modifications to the code: ")


# Handle user input to decide on modification type
def handle_modification_type(initial_question):
    action = input("Would you like to modify the existing code or an API on the publisher portal? (code/api): ").strip().lower()
    
    if action == "api":
        api_id = input("Please enter the ID of the API on the publisher portal: ").strip()
        api_details = fetch_api_details(api_id, token)

        if api_details:
            modification_statements = input("Please enter the modification statements: ")
            generate_payload(api_id, api_details, modification_statements)
        return None
    else:
        print("\nModifying the prompt with memory...\n")
        history_str = memory.buffer

        try:
            return f"{history_str}\n\n{initial_question.split(' ', 1)[1].strip()}"
        except IndexError:
            return f"{history_str}"


# Handle missing properties in the question
def handle_missing_properties(question, properties, task_type):
    properties_str = ", ".join(properties)

    missing_values_prompt = missing_values_prompt_template.format(question=question, allproperties=properties_str)
    response = llm.invoke(missing_values_prompt)

    # response = llm.invoke(prompt)
    response_text = response.content.strip()

    # boolean flag - Check if any properties are missing
    isMissingProps = "All properties are present." not in response_text
    return response_text, isMissingProps


def process_llm_response():
    history_str = memory.buffer
    prompt_with_history = chatbot_prompt_template_apiUsecase.format(history=history_str)
    
    response = llm.invoke(prompt_with_history)
    answer_text = response.content
    print("generated payload - " + answer_text)
    # memory.save_context({"input": ""}, {"output": answer_text})    # temporary - pls comment later
    save_payload('generated_payload.json', answer_text)

    return answer_text



# Publish decision handler
def handle_publish_decision(answer_text):
    publish_decision = input("Do you want to publish the API to the portal? (yes/no): ").strip().lower()
    
    if publish_decision == "yes":
        publish_api(answer_text, token)
    else:
        user_input = input("Enter your API use case or type a synonym of 'modify' to include modifications to the code: ")


# summarize openAPI spec to be added to memory
def summarize_openAPI(openAPI):
    prompt_with_history = chatbot_prompt_template_summarize_openAPI.format(openAPI=openAPI)

    response = llm.invoke(prompt_with_history)
    summary = response.content
    memory.save_context({"input": f"Human prompt: {summary}"}, {"output": ""})

    return summary


# Generate or modify a Swagger definition based on memory and user input
def modify_or_generate_swagger(question, modification_statements=None):
    history_str = memory.buffer
    if modification_statements:
        prompt_with_history = chatbot_prompt_template_modify_swagger.format(history=history_str, modification_statements=modification_statements)
    else:
        prompt_with_history = chatbot_prompt_template_swagger.format(question=question)

    response = llm.invoke(prompt_with_history)
    answer_text = response.content

    summarize_openAPI(answer_text)

    # memory.save_context({"input": ""}, {"output": answer_text})
    save_payload('modified_swagger.json', answer_text)

    return answer_text


# Function to generate a Payload
def generate_API(question):
    initial_question = question.strip()
    modified_question = None

    if any(initial_question.lower().startswith(synonym) for synonym in modify_synonyms):
        modified_question = handle_modification_type(initial_question)
        if modified_question is None:
            return {"error": "API modification was required."}

    question = handle_missing_properties(modified_question or initial_question, required_API_properties)
    answer_text = process_llm_response(question)

    return answer_text


def swagger_or_payload(task_type,question):
    if task_type == "not classified":
        task_type = ask_user_for_task_type()

    if task_type == "swagger":
        response = modify_or_generate_swagger(question)
            
    elif task_type == "payload":
        response = process_llm_response(question)

    else:
        return ({"error": "Unable to classify the request. Please try again."}), 400

    return response


# Method to validate user input
def validate_user_input(data):
    if not data:
        return {"error": "User input is required"}, 400
    
    # user_input = data.get('text', '')
    user_input = data.get('user_input', '')
    if not user_input:
        return {"error": "Text field is required"}, 400

    return None, 200  # No errors



# Method to check for missing properties
def find_missing_properties(task_type, user_input):
    if task_type == "swagger":
        response = handle_missing_properties(user_input, required_properties)

    elif task_type == "payload":
        response = handle_missing_properties(user_input, required_API_properties)
    else:
        response = "None"
        
    return response


# Function to classify the user's input using the LLM
def classify_user_input(user_input):
    classification_prompt = classification_prompt_template.format(user_input=user_input)
    response = llm.invoke(classification_prompt)
    
    task_type = response.content.strip().lower()
    return task_type


# Function to ask the user if they want to generate Swagger or API if it's unclear
def ask_user_for_task_type():
    while True:
        task_type = input("Do you want to generate a Swagger file or an API? (swagger/payload): ").strip().lower()
        if task_type in ["swagger", "payload"]:
            return task_type
        else:
            return ({"error": "Invalid input. Please enter 'swagger' or 'payload'."}), 400



# Function to generate a Swagger file
def generate_swagger_file(question):
    prompt_for_swagger = chatbot_prompt_template_swagger.format(question=question)
    response = llm.invoke(prompt_for_swagger)
    
    swagger_content = response.content

    save_payload('generated_swagger.json', swagger_content)

    return {
        "swagger_definition": swagger_content
    }



def check_for_modifications(user_input):
    prompt_to_check_for_modifications = identify_modifications_prompt.format(user_input=user_input)
    response = llm.invoke(prompt_to_check_for_modifications)

    modification_status = response.content.lower()
    # modification_status = response.content.strip()
    
    modification_statements = None

    if modification_status == "no modifications":
        modification_statements = None
    else:
        modification_statements = modification_status

    return modification_statements



def generate_suggestions(user_input):
    history_str = memory.buffer
    prompt = chatbot_prompt_template_generate_suggestions.format(user_input=user_input, history=history_str)
    response = llm.invoke(prompt)

    suggestions = response.content.strip().lower()
    return suggestions





# In-memory storage for task progress and state management
task_states = {}

# Helper function to update task state
def update_task_state(task_id, state, message=""):
    task_states[task_id] = {"state": state, "message": message}



@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    
    # user_input = data.get('text', '').strip()  # user input
    user_input = data.get('user_input')
    task_id = data.get('task_id', '')
    
    error_response, status_code = validate_user_input(data)    # validate input
    if error_response:
        return error_response, status_code

    if not task_id:
        return {"error": "Task ID is required"}, 400
    
    memory.save_context({"input": f"Human prompt: {user_input}"}, {"output": ""})               # save user input in memory

    # Step 1: Check or suggest API type
    if task_id not in task_states or task_states[task_id]['state'] == "START":
        api_suggestion = suggest_api_type(user_input)  # LLM prompt to suggest API type
        update_task_state(task_id, "AWAITING_CONFIRMATION", api_suggestion)

        isSuggestions = False

        return {
            "backendResponse": api_suggestion,
            "isSuggestions":isSuggestions,
            "state": "AWAITING_CONFIRMATION"
        }, 200

    # Step 2: Confirm or select API type
    elif task_states[task_id]['state'] == "AWAITING_CONFIRMATION":
        confirmed_api_type = check_confirmation(user_input)  # Check if user confirms or selects a different API type
        task_states[task_id]['api_type'] = confirmed_api_type  # Store selected API type
        memory.save_context({"input": f"Create this type of API: {confirmed_api_type}"}, {"output": ""})    
        update_task_state(task_id, "CHECKING_MISSING_PROPERTIES", confirmed_api_type)

    # Step 3: Check for missing properties
    # elif task_states[task_id]['state'] == "CHECKING_MISSING_PROPERTIES":
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
        final_input = user_input  # User provides missing details here


        modification_check_result = check_for_modifications(final_input)

        # openapispec = generate_spec(api_type, final_input, modification_check_result) 
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
        final_input = user_input  # User provides missing details here

        modification_check_result = check_for_modifications(final_input)

        openapispec,paths = generate_spec(api_type, final_input, modification_check_result) 

        print("after modification: " + openapispec)

        # update_task_state(task_id, "COMPLETE")
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


# function to invoke the LLM to suggest a type of API for the given use case or confirm usage of API type
def suggest_api_type(user_input):
    prompt_to_suggest_api_type = prompt_template_to_suggest_api_type.format(user_input=user_input)
    response = llm.invoke(prompt_to_suggest_api_type)
    api_type = response.content
    return api_type



# function to invoke the LLM if the user has confirmed api type or provided an alternative API type
def check_confirmation(user_input):
    history_str = memory.buffer

    prompt_to_check_confirmation = prompt_template_to_check_confirmation.format(user_input=user_input, history=history_str)
    response = llm.invoke(prompt_to_check_confirmation)

    api_type = response.content
    return api_type



# function to invoke the LLM to ask the user for the missing properties
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


def generate_spec(api_type, final_input, modification_statements=None):
    history_str = memory.buffer
    
    # Always include modification_statements, using None if not provided
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


def try_publish_api(generated_payload, retries=1):
    result = publish_api(generated_payload, token)

    # If there's an error in creating the API, retry the process
    if "error" in result and retries > 0:
        print(f"Error occurred: {result['error']}. Retrying...")
        # Generate a new payload by calling process_llm_response again
        new_generated_payload = process_llm_response()
        return try_publish_api(new_generated_payload, retries - 1)
    
    return result


@app.route('/createapiinportal', methods=['POST'])
def createapiinportal():
    generated_payload = process_llm_response() 
    result = try_publish_api(generated_payload)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)