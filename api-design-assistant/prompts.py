from langchain.prompts import PromptTemplate

# prompt which suggests an API type depending on the use case
prompt_template_to_suggest_api_type = """
    Analyze the following user input: "{user_input}" and identify the most suitable API type for the use case.
    IMPORTANT: If the input already specifies an API type, return a response to ask the user to confirm it. 
    IMPORTANT: Otherwise, in less than 10 words, suggest the most appropriate type based on the functionality the user is describing with the justification and ask user if they could proceed with that API type.

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

# prompt which asks the user to confirm the API type before proceeding with the next steps
prompt_template_to_check_confirmation = """
    Analyze the following user input: "{user_input}" and determine whether the user has:
    1. Confirmed the suggested API type with an affirmation response, or
    2. Selected a different API type from the following options:
       - REST API
       - GraphQL API
       - WebSocket
       - WebSub (Webhook)
       - Server-Sent Events (SSE)
    
    IF the user has confirmed the suggested API type, refer to the MOST RECENT PREVIOUS INTERACTIONS: {history} respond with ONE WORD answer with the appropriate type of API ("REST", "GraphQL", "WebSocket", "WebSub", "SSE")
    IF the user has chosen a different API type, respond with ONE WORD answer with the appropriate type of API ("REST", "GraphQL", "WebSocket", "WebSub", "SSE")

    Respond with ONE WORD answer with the appropriate type of API ("REST", "GraphQL", "WebSocket", "WebSub", "SSE").
"""

# prompt which asks the user for additional context for the relevant API type
missing_values_prompt_template = """ 
    You are an intelligent assistant and your task is to read and analyze the ENTIRE history: {history} and identify if for this API type:{api_type} if the following properties are missing from it: {allproperties}.

    STRICT INSTRUCTION: ONLY check for the properties {allproperties}. Do NOT look for any other properties.

    STRICT INSTRUCTION: Your task is to ask the user to provide the values of the properties that are missing. 
    STRICT INSTRUCTION: You MUST display each property name followed by a short description. DO NOT use any symbols apart from the hyphen (-). USE the below structure to display the properties.
    STRUCTURE: 
    - name: The name or main purpose of the API.
    - version: The specific version of the API.

    For clarification:
    - "name" refers to the name or main purpose.
    - "version" indicates the specific version.
    - "paths" refer to the endpoints.

"""

# prompt which generates the specification
prompt_template_to_generate_spec = """
    You are an assistant that generates responses for {api_type} APIs based on the user's input: "{final_input}" and the conversation history: "{history}".
    Please create the necessary API specification, filling in any missing details using best practices for the selected API type.

    STRICT CONDITION: DO NOT specify the language(yaml) when providing the answer.
    IMPORTANT: You MUST include the modification statements: {modification_statements} when generating the response.
    STRICT CONDITION: DO NOT specify the extracted modification statements

    Guidelines:
    - Do not mention the format (e.g., YAML or JSON) in your response.
    - Depending on the API type, provide one of the following:
        - OpenAPI 3.0 specification for a REST API.
        - Schema Definition for a GraphQL API.
        - AsyncAPI Definition for a WebSocket API.
        - AsyncAPI Definition for a WebSub (Webhook) API.
        - AsyncAPI Definition for a Server-Sent Events (SSE) API.
    
    Please ensure to only return the specification or definition as the response.

    Next, review the generated answer and identify the HTTP Methods and its paths mentioned in it and return them seperated by commas.

    Your goal is to return 2 values:
    1. The specification
    2. The HTTP Methods with the paths

    Return your response in the following format:
    generated spec: <generated_spec>
    resources: <paths>

"""

# prompt which checks if there are any modification statements in the user's query
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


# reads example openapi spec for context
with open('api-design-assistant/openapispec.txt', 'r') as file:
    swagger_file = file.read()

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


# reads JSON structure of the suggestions for context
with open('api-design-assistant/suggestionJSONformat.txt', 'r') as file:
    payload_file = file.read().replace("{", "{{").replace("}", "}}")

# prompt generates suggestions based on user's query
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

# reads example payload structure for context
with open('api-design-assistant/payloadExample.txt', 'r') as file:
    payload_file = file.read().replace("{", "{{").replace("}", "}}")

chatbot_template_apiUsecase = payload_file + """           
You are a highly skilled and intelligent assistant, specializing in generating a payload based on the Previous Interactions.

Your task is to take the details from the ENTIRE history of Previous Interactions and intelligently generate the payload containing exactly 60 properties and their respective values, following the structure provided.

STRICT CONDITION: DO NOT specify the language (yaml) when providing the answer.
STRICT CONDITION: The name of the API MUST NOT be 'hello API'. Instead it must be a name you intelligently create based on the ENTIRE history of Previous Interactions.
STRICT CONDITION: DO NOT make up new properties. You MUST only use the properties provided in the structure above.
STRICT CONDITION: If in the history of Previous Interactions it states to SET ACCESS CONTROL, then you MUST update accessControl's value to "RESTRICTED"

EXTREMELY STRICT CONDITION: You MUST include all the modifications provided in the ENTIRE history of Previous Interactions. If needed, intelligently assume missing details based on common API practices for the use case.

EXTREMELY STRICT CONDITION: chnage the value of the "type" property to "HTTP" for REST APIs, "GRAPHQL" for GraphQL APIs, "WS" for WebSocket APIs, "WEBSUB" for Websub/ Webhook APIs and "SSE" for Server-Sent Events (SSE) APIs.

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

# Prompt to gmodify the swagger file
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