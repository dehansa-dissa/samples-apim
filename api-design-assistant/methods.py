from flask import Flask, request, Response, jsonify
import json
from flask_cors import CORS
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
    chatbot_prompt_template_summarize_openAPI
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

    # prompt = f"""
    # Question: {question}
    # Properties: {properties_str}

    # Identify the missing properties from the question and return sentences with bullet points asking the user to provide values for the missing ones in a very user-friendly manner with some context of each missing property. 
    # If no properties are missing, return 'All properties are present.'
    # """

    missing_values_prompt = missing_values_prompt_template.format(question=question, allproperties=properties_str)
    response = llm.invoke(missing_values_prompt)

    # response = llm.invoke(prompt)
    response_text = response.content.strip()

    # boolean flag - Check if any properties are missing
    isMissingProps = "All properties are present." not in response_text
    return response_text, isMissingProps



# # Process LLM response and generate final payload
# def process_llm_response(question):
#     history_str = memory.buffer
#     prompt_with_history = chatbot_prompt_template_apiUsecase.format(question=question, history=history_str)
    
#     response = llm.invoke(prompt_with_history)
#     answer_text = response.content
#     # memory.save_context({"input": ""}, {"output": answer_text})
#     save_payload('generated_payload.json', answer_text)

#     return answer_text



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
    
    user_input = data.get('text', '')
    # user_input = data.get('user_input', '')
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



# def check_for_modifications(user_input):
#     history_str = memory.buffer if memory else ""

#     identify_modifications_prompt = identify_modifications_prompt_template.format(
#         user_input=user_input, history=history_str
#     )

#     response = llm.invoke(identify_modifications_prompt)
#     response_content = response.content.strip()

#     task_type = None
#     modification_statements = None

#     for line in response_content.split("\n"):
#         if line.lower().startswith("task type:"):
#             task_type = line.split(":", 1)[1].strip().lower()
#         elif line.lower().startswith("modifications:"):
#             modification_statements = line.split(":", 1)[1].strip()

#     # If no modifications found, return "no modifications"
#     if modification_statements.lower() == "no modifications":
#         return "no modifications"

#     if task_type == "swagger":
#         return modify_or_generate_swagger(user_input, user_input)
#     elif task_type == "payload":
#         return process_llm_response(user_input)
    
#     return "Invalid task type or response."


# def check_for_modifications(user_input):
#     prompt_to_check_for_modifications = identify_modifications_prompt.format(user_input=user_input)
#     # response = llm.invoke(prompt_to_check_for_modifications)

#     modification_status = llm.invoke(prompt_to_check_for_modifications)

#     # modification_status = response.content

#     modification_statements = None

#     if modification_status.lower() == "no modifications":
#         modification_statements = None
#         return modification_statements
    
#     modification_statements = modification_status
#     return modification_statements


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
    
    user_input = data.get('text', '').strip()  # user input
    # user_input = data.get('user_input')
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

        # return jsonify({
        #     "backendResponse": api_suggestion,
        #     "state": "AWAITING_CONFIRMATION"
        # }), 200

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

        # return jsonify({
        #     "backendResponse": missing_values_prompt,
        #     "state": "AWAITING_MISSING_PROPERTIES"
        # }), 200

        return {
            "backendResponse": missing_values_prompt,
            "isSuggestions":isSuggestions,
            "state": "AWAITING_MISSING_PROPERTIES"
        }, 200
    
    # Step 4: Generate OpenAPI spec
    elif task_states[task_id]['state'] == "AWAITING_MISSING_PROPERTIES":
        api_type = task_states[task_id].get('api_type')
        final_input = user_input  # User provides missing details here

        # modification_check_result = check_for_modifications(user_input)
        # openapispec = modify_or_generate_swagger(user_input, modification_check_result)

        print(memory.buffer)
        openapispec = generate_spec(api_type, final_input)  # Final API generation

        update_task_state(task_id, "COMPLETE")

        memory.save_context({"input": ""}, {"output": openapispec})
        print(memory.buffer)

        suggestions = generate_suggestions(user_input)
        isSuggestions = True

        return {
            "backendResponse": suggestions,
            "isSuggestions":isSuggestions,
            "code": openapispec,
            "state": "COMPLETE"
        }, 200
    
#       "openapispec": openapispec,
#       "suggestions": suggestions,
#       "isSuggestions":isSuggestions

    return {"error": "Invalid state or input"}, 400



# Mock functions (these would interact with the LLM)
def suggest_api_type(user_input):
    prompt = f"""
    Analyze the following user input: "{user_input}" and identify the most suitable API type for the use case.
    IMPORTANT: If the input already specifies an API type, return a response to ask the user to confirm it. 
    IMPORTANT: Otherwise, in less than 10 words, suggest the most appropriate type based on the functionality the user is describing and user user if they could confirm it so it can be created.

    Choose from one of the following API types: 
    - REST API
    - GraphQL API
    - WebSocket
    - WebSub (Webhook)
    - Server-Sent Events (SSE)
    
    To choose the best API type, it is important to match the API is characteristics with the specific needs of your use case:

    - REST APIs are ideal for CRUD operations, managing resources, and stateless communication. They work well in web-based apps like e-commerce or content management systems where simple HTTP methods are sufficient.

    - GraphQL excels when clients need flexibility in data querying, allowing them to request specific fields and avoid over-fetching or under-fetching. It's great for social media platforms or dashboards aggregating data from multiple sources.

    - WebSocket is designed for real-time, bidirectional communication with low latency. It's perfect for scenarios like chat apps, multiplayer gaming, or live financial updates, where both the client and server need to exchange data frequently.

    - WebSub (Webhook) fits event-driven architectures where asynchronous notifications are required. It is commonly used in payment systems or GitHub integrations, notifying third-party services when events occur.

    - Server-Sent Events (SSE) provide real-time, one-way communication from server to client, making them ideal for continuous updates like live sports scores or stock tickers, where the client does not need to send data back.

    """
    response = llm.invoke(prompt)
    api_type = response.content
    return api_type


def check_confirmation(user_input):
    history_str = memory.buffer
    
    prompt = f"""
    Analyze the following user input: "{user_input}" and determine whether the user has:
    1. Confirmed the suggested API type with an affirmation response, or
    2. Selected a different API type from the following options:
       - REST API
       - GraphQL API
       - WebSocket
       - WebSub (Webhook)
       - Server-Sent Events (SSE)
    
     
    IF the user has confirmed the suggested API type, refer to the MOST RECENT PREVIOUS INTERACTIONS: {history_str} respond with ONE WORD answer with the appropriate type of API ("REST", "GraphQL", "WebSocket", "WebSub", "SSE")
    IF the user has chosen a different API type, respond with ONE WORD answer with the appropriate type of API ("REST", "GraphQL", "WebSocket", "WebSub", "SSE")

    Respond with ONE WORD answer with the appropriate type of API ("REST", "GraphQL", "WebSocket", "WebSub", "SSE").
    """

    response = llm.invoke(prompt)
    api_type = response.content
    return api_type



def generate_missing_values_prompt(api_type):
    history_str = memory.buffer

    # properties = required_properties.get(api_type, ["name", "version", "paths"])
    properties = required_properties.get(api_type, [])

    # If the api_type is not found, fallback to a default list
    if not properties:
        properties = ["name", "version", "paths"]  # Default properties if API type is unknown


    properties_str = ", ".join(properties)

    missing_values_prompt = missing_values_prompt_template.format(api_type=api_type, history=history_str, allproperties=properties_str)
    response = llm.invoke(missing_values_prompt)
    missing_values = response.content.strip()

    return missing_values



def generate_spec(api_type, final_input):
    history_str = memory.buffer
    
    # prompt = f"""
    # You are an intelligent assistant whose task is to generate an accurate response for a {api_type} API based on the input provided by the user: {final_input} and the ENTIRE history: {history_str}
    # You must intelligently create the response by filling in missing details based on common practices for the use case.

    # STRICT CONDITION: DO NOT specify the language(yaml) when providing the answer.

    # STRICT CONDITION: depending on the API TYPE, you must create ONLY ONE of the following responses:
    #     - Create an OpenAPI 3.0 specification for a REST API.
    #     - Create a Schema Definition for a GraphQL API.
    #     - Create an AsyncAPI Definition for a WebSocket API.
    #     - Create an AsyncAPI Definitionn for a WebSub (WebHook) API.
    #     - Create an AsyncAPI Definition for a Server Sent Events (SSE) API.
    
    # """

    prompt = f"""
    You are an assistant that generates responses for {api_type} APIs based on the user's input: "{final_input}" and the conversation history: "{history_str}".
    Please create the necessary API specification, filling in any missing details using best practices for the selected API type.

    Guidelines:
    - Do not mention the format (e.g., YAML or JSON) in your response.
    - Depending on the API type, provide one of the following:
        - OpenAPI 3.0 specification for a REST API.
        - Schema Definition for a GraphQL API.
        - AsyncAPI Definition for a WebSocket API.
        - AsyncAPI Definition for a WebSub (Webhook) API.
        - AsyncAPI Definition for a Server-Sent Events (SSE) API.
    
    Please ensure that the response follows best practices for the specified API type.

    Please ensure to only return the specification or definition as the response.
    """ 

    response = llm.invoke(prompt)
    openapi_spec = response.content
    return openapi_spec





# ----------------------------------------------------------- B E S T  V E R S I O N -------------------------------------------------------------------

# @app.route('/generate', methods=['POST'])
# def generate():
#     data = request.get_json()

#     user_input = data.get('text', '').strip()                                                   # user input
#     # user_input = data.get('user_input')
#     task_id = data.get('task_id', '')

#     error_response, status_code = validate_user_input(data)                                     # validate input
#     if error_response:
#         return error_response, status_code

#     if not task_id:
#         return {"error": "Task ID is required"}, 400
        
#     memory.save_context({"input": f"Human prompt: {user_input}"}, {"output": ""})               # save user input in memory

#     modification_check_result = check_for_modifications(user_input)
#     openapispec = modify_or_generate_swagger(user_input, modification_check_result)

#     suggestions = generate_suggestions(user_input)
#     isSuggestions = True

#     print(memory.buffer)
    
#     return {
#         "openapispec": openapispec,
#         "suggestions": suggestions,
#         "isSuggestions":isSuggestions
#     }, 200

# ---------------------------------------------------------------------------------------------------------------------------------------------------



# @app.route('/generate', methods=['POST'])
# def generate():
#     global payload_response_from_llm

#     data = request.get_json()

#     # user_input = data.get('text', '').strip()
#     user_input = data.get('user_input')
#     if user_input == "yes":
#         publish_api(payload_response_from_llm, token)
#         create_api_success = "API has been successfully created in the Publisher Portal!"
#         return Response(create_api_success, content_type='text/plain')

#     error_response, status_code = validate_user_input(data)
#     if error_response:
#         return error_response, status_code

#     user_input = data.get('user_input')
#     # user_input = data.get('text', '').strip()  
#     task_id = data.get('task_id', '')
    
#     if not task_id:
#         return {"error": "Task ID is required"}, 400
        
#     memory.save_context({"input": f"Human prompt: {user_input}"}, {"output": ""})

#     # Check if task is already in progress
#     if task_state.get(task_id, {}).get('state') == 'in progress':
#         task_state[task_id]['state'] = 'complete'
        
#         task_type = task_state[task_id].get('task_type')
#         if task_type == "swagger":
#             swagger_payload = modify_or_generate_swagger(user_input)
#             return Response(swagger_payload, content_type='text/plain')
#         elif task_type == "payload":
#             payload_response_from_llm = process_llm_response(user_input)
#             # payload_response = f"{payload_response_from_llm}\nWould you like to create this API? (yes/no)"
#             return Response(payload_response_from_llm, content_type='text/plain')

#     modification_check_result = check_for_modifications(user_input)
    
#     if modification_check_result == "no modifications":
#         task_type = classify_user_input(user_input)
#         if task_type == "swagger":
#             missing_properties_prompt, is_missing_props = handle_missing_properties(user_input, required_properties, task_type)
#         elif task_type == "payload":
#             missing_properties_prompt, is_missing_props = handle_missing_properties(user_input, required_API_properties, task_type)
#         else:
#             return {"error": "Invalid task type"}, 400

#         if is_missing_props:
#             task_state[task_id] = {'state': 'in progress', 'task_type': task_type}
#             return Response(missing_properties_prompt, content_type='text/plain')

#         response = swagger_or_payload(task_type, user_input)

#     else:
#         response = modification_check_result
#     return Response(response, content_type='text/plain')





# @app.route('/createapiinportal', methods=['POST'])
# def createapiinportal():
#     # data = request.get_json()

#     # # user_input = data.get('text', '').strip()
#     # user_input = data.get('user_input')

#     # if not user_input:
#     #     return jsonify({"error": "No input provided"}), 400
#     #     # return Response({"error": "No input provided"}, content_type='text/plain')

#     global swagger_payload

#     generated_payload = process_llm_response(swagger_payload)                    # to create API in portal
#     result = publish_api(generated_payload, token)

#     return jsonify(result)
#     # return Response(result, content_type='text/plain')


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