from langchain.prompts import PromptTemplate

classification_prompt_template = """
You are an intelligent assistant. Analyze the following user input and classify it as either a request to generate a 'payload' or a 'swagger definition'. 
If the user input contains 'API', classify it as 'payload'. 
If the user input contains 'swagger', classify it as 'swagger'. 
If the user input does not contain 'API' or 'swagger', classify it as 'not classified'. 
User input: {user_input}
Please respond with only one word: 'payload' or 'swagger' or 'not classified'.
"""



# missing_values_prompt_template = """ 
#     Please read and analyze the user's input: {question}. Your task is to identify if any of the following properties are missing from it: {allproperties}.

#     STRICT INSTRUCTION: ONLY check for the properties {allproperties}." Do NOT look for any other properties.

#     If any of these properties are missing, you must ask the user to provide the necessary values in a VERY concise manner. 

#     If no properties are missing, return 'All properties are present.'

#     For clarification:
#     - "name" refers to the name or main purpose.
#     - "version" indicates the specific version.
#     - "paths" refer to the endpoints.
# """
# Include helpful context for each missing property, so the user understands exactly what information you need.

missing_values_prompt_template = """ 
    You are an intelligent assistant and your task is to read and analyze the ENTIRE history: {history} and identify if for this API type:{api_type} if the following properties are missing from it: {allproperties}.

    STRICT INSTRUCTION: ONLY check for the properties {allproperties}. Do NOT look for any other properties.

    If any of these properties are missing, you must ask the user to provide the necessary values in a VERY concise manner. 

    For clarification:
    - "name" refers to the name or main purpose.
    - "version" indicates the specific version.
    - "paths" refer to the endpoints.

"""



# identify_modifications_prompt_template = """
# You are an intelligent assistant tasked with analyzing the following user input: {user_input}

# If the input contains a synonym of 'modify' (e.g., 'edit', 'update', 'change') or refers to making modifications WITHOUT mentioning 'create', you MUST identify and extract the modification-related statements from the input {user_input}.
# If no such modifications are mentioned, return 'no modifications.'

# Next, review the Previous Interactions to determine if the user is referring to a Swagger or Payload.
# If the user is referring to something which contains 'API', or 'payload' classify it as 'payload'. 
# If theuser is referring to something which contains 'swagger', classify it as 'swagger'. 
# Previous Interactions: {history}

# Your goal is to accurately determine two things based on this analysis:
# 1. The type of task the user is referring to (either 'swagger' or 'payload').
# 2. The extracted modification statements (or 'no modifications' if none are present).

# Return your response in the following format:
# Task Type: <task_type>
# Modifications: <modifications>

# """


identify_modifications_prompt_template = """
You are an intelligent assistant tasked with analyzing the following user input: {user_input}

If the input contains a synonym of 'modify' (e.g., 'add', 'edit', 'update', 'change') or refers to making modifications WITHOUT mentioning 'create', you MUST identify and extract the modification-related statements from the input {user_input}.
If no such modifications are mentioned, return 'no modifications'

Your goal is to accurately determine the extracted modification statements (or 'no modifications' if none are present).

Answer:
"""

identify_modifications_prompt = PromptTemplate(
    input_variables=["user_input"], 
    template=identify_modifications_prompt_template
)




with open('Modified_API-Create-With-AI-Code/swaggerYaml.txt', 'r') as file:
    swagger_file = file.read()

# Prompt to generate a swagger file
chatbot_template_swagger = swagger_file + """  
    You are an intelligent assistant whose task is to generate an accurate OpenAPI 3.0 specification for an API based on the input provided by the user: {question}. You must carefully interpret the user's use case: {question}, and intelligently create the OpenAPI specification by filling in missing details based on common practices for the use case.

    STRICT CONDITION: DO NOT specify the language (yaml) when providing the answer.
    STRICT CONDITION: DO NOT make up new properties. You MUST only use the properties provided in the structure above.
    STRICT CONDITION: DO NOT specify the extracted modification statements

    STRICT CONDITIONS:
    1. Thoroughly understand the user's use case : {question}. Based on this understanding, you must generate the appropriate:
    - Titles for the API and its operations
    - Paths for each endpoint
    - Parameters for requests (both in path and query)
    - Request bodies and their structures
    - Responses with appropriate HTTP status codes and return values for:
        - 200 (Success)
        - 400 (Bad Request)
        - 500 (Internal Server Error)
    - Use HTTP methods like GET, PUT, POST, DELETE and PATCH as relevant to the use case.
    
    2. Include detailed schemas for request and response objects using industry-standard field types (e.g., string, integer, boolean, date-time).
    
    3. Your task is to ONLY provide the generated OpenAPI specification in YAML format and must match the structure of the example OpenAPI 3.0 specification file.
    
    4. STRICTLY ensure the following:
    - Always include response codes **200, 400, and 500** in every operation.
    - If needed, intelligently assume missing details based on common API practices for the use case.

    5. Do not include any URLs (including redirect URLs) or external references in your response.

"""


chatbot_prompt_template_swagger = PromptTemplate(
    input_variables=["question"], 
    template=chatbot_template_swagger
)





modify_swagger_template = swagger_file + """
    You are an intelligent assistant whose task is to generate an accurate OpenAPI 3.0 specification for an API based on the modifications provided by the user: {modification_statements} and the Previous Interactions. You must carefully interpret the user's use case and intelligently create the OpenAPI specification by filling in missing details based on common practices for the use case.

    STRICT CONDITION: DO NOT specify the language (yaml) when providing the answer.
    STRICT CONDITION: You MUST only use the properties provided in the example structure above. DO NOT make up new properties when doing modifications.
    STRICT CONDITION: DO NOT specify the extracted modification statements

    STRICT CONDITIONS:
    1. Thoroughly understand the user's use case (e.g., "banking transactions," "book search," "user management"). Based on this understanding, you must generate the appropriate:
    - Titles for the API and its operations
    - Paths for each endpoint
    - Parameters for requests (both in path and query)
    - Request bodies and their structures
    - Responses with appropriate HTTP status codes and return values for:
        - 200 (Success)
        - 400 (Bad Request)
        - 500 (Internal Server Error)
    - Use HTTP methods like GET, PUT, POST, DELETE and PATCH as relevant to the use case.
    
    2. Include detailed schemas for request and response objects using industry-standard field types (e.g., string, integer, boolean, date-time).
    
    3. Your task is to ONLY provide the generated OpenAPI specification in YAML format and must match the structure of the example OpenAPI 3.0 specification file.

    4. STRICTLY ensure the following:
    - You MUST include the user's modification statements such as: {modification_statements} to generate an accurate OpenAPI specification based on the relevant information from the 'Human prompt' in the Previous Interactions.
    - Always include response codes **200, 400, and 500** in every operation.
    - If needed, intelligently assume missing details based on common API practices for the use case.

    5. Do not include any URLs (including redirect URLs) or external references in your response.

    Previous Interactions:
    {history}

    Answer:
"""

chatbot_prompt_template_modify_swagger = PromptTemplate(
    input_variables=["history", "modification_statements"], 
    template=modify_swagger_template
)

# STRICT CONDITION: Focus on areas such as security schemes, response caching, CORS configuration, rate limiting, and any other appropriate keys, but only if they are directly applicable to the context of the input. 
    




# Prompt to generate a summary of the swagger file
prompt_template_summarize_openAPI = swagger_file + """  
    You are an intelligent assistant whose task is to generate an accurate summarization of this OpenAPI specification - {openAPI}
    STRICT CONDITION: You must carefully read the OpenAPI specification and intelligently summarize it and provide the following information:
        - all the paths (GET, POST, PUT, DELETE, PATCH)
        - all the components

    Answer:
"""


chatbot_prompt_template_summarize_openAPI = PromptTemplate(
    input_variables=["openAPI"], 
    template=prompt_template_summarize_openAPI
)






with open('Modified_API-Create-With-AI-Code/suggestionJSONformat.txt', 'r') as file:
    payload_file = file.read().replace("{", "{{").replace("}", "}}")


generate_suggestions = """
    Based on the following input: {user_input} and Previous Interactions, analyze the context and suggest only the most relevant and suitable improvements to the OpenAPI specification. 
    STRICT CONDITIONS: Focus on areas such as : set access control to RESTRICTED,  so only certain publishers and creators can view or modify the API, set security schemes to mutual SSL, enable response caching, enable CORS configuration, set throttling policy to Application User, set transport to https, websub subscription configuration (e.g:- signing algorithm, secret, and signature headers), enable subscriber verification, enable schema validation , set visible roles to Admin Role.
    but ONLY if they are directly applicable to the context of the input: {user_input}. 

    STRICT CONDITION: YOU MUST NOT specify the language (json) when providing the answer.

    EXTREMELY STRICT CONDITION: If the user input includes "Modify this API to include the following features as well", you MUST NOT suggest those values as they were already selected by the user.
    STRICT CONDITION: You MUST provide a MAXIMUM of 5 suggestions.

    IMPORTANT: You MUST provide the answer in JSON format as the above example shows with a number as the main key for each suggestion and the title to contain the suggestion and a description to describe why this use case '{user_input}' could benefit from this suggestion.
    
    STRICT CONDITION: The 'title' key should contain a value with a maximum of 4 words, and the 'description' key should contain a value with between 15 to 20 words.
    STRICT CONDITION: Words such as 'API' or 'CORS' MUST be in UPPER CASE. 

    Previous Interactions:
    {history}
"""

chatbot_prompt_template_generate_suggestions = PromptTemplate(
    input_variables=["user_input", "history"], 
    template=generate_suggestions
)






with open('Modified_API-Create-With-AI-Code/payloadExample.txt', 'r') as file:
    payload_file = file.read().replace("{", "{{").replace("}", "}}")

chatbot_template_apiUsecase = payload_file + """           
You are a highly skilled and intelligent assistant, specializing in generating a payload based on the Previous Interactions.

Your task is to take the details from the ENTIRE history of Previous Interactions and intelligently generate the payload containing exactly 60 properties and their respective values, following the structure provided.

STRICT CONDITION: DO NOT specify the language (yaml) when providing the answer.
STRICT CONDITION: The name of the API MUST NOT be 'hello API'. Instead it must be a name you intelligently create based on the ENTIRE history of Previous Interactions.
STRICT CONDITION: DO NOT make up new properties. You MUST only use the properties provided in the structure above.
STRICT CONDITION: If in the history of Previous Interactions it states to SET ACCESS CONTROL, then you MUST update accessControl's value to "RESTRICTED"

EXTREMELY STRICT CONDITION: You MUST include all the modifications provided in the ENTIRE history of Previous Interactions. If needed, intelligently assume missing details based on common API practices for the use case.

EXTREMELY STRICT CONDITIONS:
    - "accessControlRoles" MUST be ["admin"] if access control is enabled in the Previous Interactions
    - "visibleRoles" MUST be ["admin"], if visible roles are set in the Previous Interactions
    - "maxTps" MUST be null
    - "apiThrottlingPolicy" MUST be null
    - "categories" MUST be []
    - "scopes" MUST be []

STRICT CONDITIONS: Thoroughly understand the Previous Interactions. Based on this understanding, you must generate the appropriate:
    - Name for the API and its operations
    - Paths for each endpoint
    - Parameters for requests (both in path and query)

STRICT CONDITIONS:
- You MUST ALWAYS provide exactly 59 properties and their respective values in the payload file, no more, no less.
- You MUST read and incorporate all the details provided in the input to generate or modify the payload, especially when modifying previous responses.
- The policies must always be ["Unlimited"] but apipolicy must always be null.

Previous Interactions:
{history}

"""


chatbot_prompt_template_apiUsecase = PromptTemplate(
    input_variables=["history"], 
    template=chatbot_template_apiUsecase
)




create_api_confirmation = """
You are a simple and intelligent assistant.

IMPORTANT: Your task is to determine if the User Input: {user_input} contains any of the following:
            1. A synonym of 'yes'
            2. Any form of positive confirmation
            If any of these conditions are met, return 'yes'. Otherwise, return 'no'.

Answer:
"""

chatbot_prompt_template_create_api_confirmation = PromptTemplate(
    input_variables=["user_input"], 
    template=create_api_confirmation
)

# IMPORTANT: Your task is to identify if the User Input: {user_input} contains a synonym of 'yes' OR any positive confirmation OR any statement which is similar to 'create this api'. If it does, you MUST return 'yes' else return 'no'.


# Prompt to generate a payload based on fetched API details
chatbot_template_apiPubPortal = payload_file + """           
You are a highly skilled assistant, specializing in generating payloads based on existing API details and specific modification instructions. Your task is to generate a payload containing exactly 59 properties and their respective values, following the EXACT structure and syntax provided.

IMPORTANT: All properties should follow the structure and syntax provided in the example. Do not allow duplicate properties.

STRICT CONDITIONS:
- You MUST ALWAYS provide exactly 59 properties and their respective values in the payload file, no more, no less.
- You CANNOT change the structure or syntax when generating the code and MUST ALWAYS follow the payload structure provided.
- You MUST read and incorporate all the modifications provided in the input to generate the new payload.
- If the human question is not valid English text, return it exactly as it is without any modifications.

Here are the details of the API to be modified:
{api_details}

And here are the modification statements provided by the user:
{modification_statements}
"""

chatbot_prompt_template_apiPubPortal = PromptTemplate(
    input_variables=["api_details", "modification_statements"], 
    template=chatbot_template_apiPubPortal
)