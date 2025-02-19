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
from langchain.prompts import PromptTemplate

# prompt which suggests an API type depending on the use case
prompt_template_to_suggest_api_type = """
    Analyze the user input: "{user_input}" and determine:

    1. API Type: Identify the API type based on the following:

    - If explicitly mentioned in the input, use that.
    - If not mentioned, infer it from the use case described.
    - If neither applies, use the API type specified in the most recent previous interactions from the history.

    API types to consider:
    - REST
    - GraphQL
    - WebSocket
    - WebSub (Webhook)
    - Server-Sent Events (SSE)

    Output: Respond with only one word: "REST", "GraphQL", "WebSocket", "WebSub", or "SSE".

    2. API Type Suggestion:
    If another API type fits the use case better, suggest it briefly (under 40 words) with a detailed justification of why the suggested API type would be suitable for the user's given use case. Confirm if the user wants to proceed with the suggestion.

        To help choose the best API type, consider these characteristics:
            - REST: Ideal for CRUD operations, resource management, and stateless communication. Best for web-based apps like e-commerce or CMS.
            - GraphQL: Flexible querying for specific data fields. Great for social platforms or dashboards aggregating data from multiple sources.
            - WebSocket: Real-time, low-latency bidirectional communication. Perfect for chat apps, multiplayer games, or live updates.
            - WebSub (Webhook): Event-driven, asynchronous notifications. Suitable for payment systems or GitHub integrations.
            - SSE: One-way, real-time updates from server to client. Ideal for live scores or stock tickers.

    Return Format: Respond in JSON with two keys:
    - api_type: The determined API type.
    - api_type_suggestion: Either a confirmation of the current API type or a question about changing to a more suitable type.

    STRICT CONDITION: DO NOT specify the language(json) when providing the answer.

    Previous Interactions Context: {history}
"""


# prompt which asks the user for additional context for the relevant API type
missing_values_prompt_template = """ 
    You are a knowledgeable and efficient assistant. Your task is to read and analyze the user's prompts from the *ENTIRE history*: {history} and politely ask the user to provide the values for these properties: {allproperties} for this API type: {api_type} *if they are missing from the history.*

    STRICT INSTRUCTION: ONLY check for the properties {allproperties}. Do NOT look for any other properties.

    STRICT INSTRUCTION: Extract the property values intelligently from the provided history without including them explicitly in the response. Assume the values based on the use case for clarity and conciseness.

    STRICT INSTRUCTION: You MUST display each property name followed by a short description. DO NOT use any symbols apart from the hyphen (-) and the dot (•). USE the below structure to display the properties.

EXAMPLE STRUCTURE: 

It seems that we need to gather some additional information to create your REST API for banking transactions. Here are the properties that are currently missing:

• name - The name or main purpose of the API.

• version - The specific version of the API.

• context - The context or scope in which the API operates.

• endpoint - The base URL for the API.

• http methods - The HTTP methods that will be used (e.g., GET, POST).

• paths - The specific paths for the API endpoints.

Providing these values will help us create a more accurate and tailored API for your needs. Could you please share the required information? Thank you!
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
with open('openapispec.txt', 'r') as file:
    openapispec_file = file.read()

# generates the OpenAPI specification for REST APIs
modify_openapi_template = openapispec_file + """
    You are an intelligent assistant whose task is to generate an accurate OpenAPI 3.0 specification for an API based on the modifications provided by the user: {modification_statements} and the Previous Interactions. You must carefully interpret the user's use case and intelligently create the OpenAPI specification by filling in missing details based on common practices for the use case.
    
    STRICT CONDITION: You MUST prioritize the *user's request: {final_input}* above all else and accurately generate an OpenAPI 3.0 specification that precisely reflects the user's use case.

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

    Your task is to generate :
        - OpenAPI 3.0 specification.
        - An array of HTTP methods and their corresponding paths/resources.
        
    Please ensure to only return the specification or definition as the response.

    Next, review the generated answer and identify the HTTP Methods and its paths mentioned in it and return them seperated by commas.

    Your goal is to return 2 values:
    1. The specification
    2. An array of HTTP Methods with the paths/resources

    You MUST return your response in a JSON format where the overall structure uses JSON keys and values, but the 'generated_spec' value MUST be in YAML format, and 'resources' MUST be an array like this for example ['GET /transactions', 'POST /transactions'].

    Previous Interactions:
    {history}

    Latest Specification:
    {specification}

    Answer:
"""

chatbot_prompt_template_modify_openapi = PromptTemplate(
    input_variables=["final_input", "history", "specification", "modification_statements"], 
    template=modify_openapi_template
)


# reads example schema definition for context
with open('graphqlschemadefinition.txt', 'r') as file:
    graphqlfile = file.read().replace("{", "{{").replace("}", "}}")

# generates the schema definition for GraphQL APIs
graphql_template = graphqlfile + """
    You are an intelligent assistant whose task is to generate an accurate Schema definition for a GraphQL API based on the modifications provided by the user: {modification_statements} and the Previous Interactions. You must carefully interpret the user's use case and intelligently create the Schema Definition by filling in missing details based on common practices for the use case.

    STRICT CONDITION: You MUST prioritize the *user's request: {final_input}* above all else and accurately generate a Schema definition for a GraphQL API that precisely reflects the user's use case.
    STRICT CONDITION: DO NOT specify the language (yaml) when providing the answer.
    STRICT CONDITION: You MUST only use the properties provided in the example structure above. DO NOT make up new properties when doing modifications.
    STRICT CONDITION: DO NOT specify the extracted modification statements

    STRICT CONDITIONS:
    1. Thoroughly understand the user's use case (e.g., "banking transactions," "book search," "user management"). Based on this understanding, you must generate the appropriate:
    - Titles for the API and its operations
    - Paths for each endpoint
    - Parameters for requests (both in path and query)
    
    2. Include detailed schemas for request and response objects using industry-standard field types (e.g., string, integer, boolean, date-time).
    
    3. Your task is to ONLY provide the generated Schema definition in YAML format and must match the structure of the example Schema definition file.

    4. STRICTLY ensure the following:
    - You MUST include the user's modification statements such as: {modification_statements} to generate an accurate Schema definition based on the relevant information from the 'Human prompt' in the Previous Interactions.
    - If needed, intelligently assume missing details based on common API practices for the use case.

    5. Do not include any URLs (including redirect URLs) or external references in your response.

    Your task is to generate 2 values:
        - Schema definition for a GraphQL API.
        - Set the array of resources to ['No resources'].

    Please ensure to only return the definition as the response.

    You MUST return your response in a JSON format where the overall structure uses JSON keys and values, but the 'generated_spec' value MUST be in YAML format, and 'resources' MUST be ['No resources'].

    STRICT CONDITION: DO NOT specify the extracted modification statements
    
    Previous Interactions:
    {history}

    Latest Specification:
    {specification}

    Answer:
"""

chatbot_prompt_template_graphql = PromptTemplate(
    input_variables=["final_input", "history", "specification", "modification_statements"], 
    template=graphql_template
)


# generates the async definition for Async APIs
prompt_template_to_generate_spec = """
    You are an assistant that generates responses for {api_type} APIs based on the user's input: "{final_input}", the conversation history: "{history}" and latest specification: {specification}.
    Please create the AsyncAPI Definition, filling in any missing details using best practices for the selected API type.

    STRICT CONDITION: You MUST prioritize the *user's request: {final_input}* above all else and accurately generate an AsyncAPI Definition that precisely reflects the user's use case.

    STRICT CONDITION: DO NOT specify the language (yaml or json) when providing the answer.
    IMPORTANT: You MUST include the modification statements: {modification_statements} when generating the response.
    STRICT CONDITION: DO NOT specify the extracted modification statements.
     
    For WebSocket, WebSub, SSE APis:
        - Generate the corresponding AsyncAPI Definition.
        - Set the array of resources to ['No resources'].

    Please ensure to only return the AsyncAPI definition as the response.

    Your goal is to return 2 values:
    1. The specification
    2. An array stating ['No resources']

    You MUST return your response in a JSON format where the overall structure uses JSON keys and values, but the 'generated_spec' value MUST be in YAML format, and 'resources' MUST be ['No resources'].
"""


# reads JSON structure of the suggestions for context
with open('suggestionJSONformat.txt', 'r') as file:
    payload_file = file.read().replace("{", "{{").replace("}", "}}")

# prompt generates suggestions based on user's query
generate_suggestions = """
    Based on the Previous Interactions, analyze the context and suggest only the most relevant and suitable improvements to the specification. 
    
    STRICT CONDITION: DO NOT specify the language (json) when providing the answer.

    STRICT CONDITION: You MUST ONLY do ONE of the following depending on API type: {api_type},
        If API type: {api_type}, is REST or GraphQL, you MUST ONLY focus on areas such as : set access control to RESTRICTED,  so only certain publishers and creators can view or modify the API, set security schemes to mutual SSL, enable response caching, enable CORS configuration, set throttling policy to Application User, set transport to https, websub subscription configuration (e.g:- signing algorithm, secret, and signature headers), enable subscriber verification, enable schema validation , set visible roles to Admin Role.

        If API type: {api_type}, is "WS" or "WebSocket", you MUST ONLY focus on areas such as : renable rate limiting, set access control to RESTRICTED,  so only certain publishers and creators can view or modify the API, enable schema validation , set visible roles to Admin Role.

        If API type: {api_type}, is "WebSub" or "WEBSUB", you MUST ONLY focus on areas such as : set access control to RESTRICTED,  so only certain publishers and creators can view or modify the API, set security schemes to mutual SSL, enable CORS configuration, set throttling policy to Application User, set transport to https, websub subscription configuration (e.g:- signing algorithm, secret, and signature headers), enable subscriber verification, enable schema validation , set visible roles to Admin Role.

        If API type: {api_type}, is "SSE", you MUST ONLY focus on areas such as : set access control to RESTRICTED,  so only certain publishers and creators can view or modify the API, set security schemes to mutual SSL, enable CORS configuration, set transport to https, enable schema validation.

    STRICT CONDITION: YOU MUST NOT specify the language (json) when providing the answer.

    EXTREMELY STRICT CONDITION: If the user input includes "Modify this API to include the following features as well", you MUST NOT suggest those values as they were already selected by the user.
    STRICT CONDITION: You MUST provide a MAXIMUM of 5 suggestions.

    IMPORTANT: You MUST provide the answer in JSON format as the above example shows with a number as the main key for each suggestion and the title to contain the suggestion and a description to describe why this use case could benefit from this suggestion.
    
    STRICT CONDITION: The 'title' key should contain a value with a maximum of 4 words, and the 'description' key should contain a value with between 15 to 20 words.
    STRICT CONDITION: Words such as 'API' or 'CORS' MUST be in UPPER CASE. 

    Previous Interactions:
    {history}
"""

chatbot_prompt_template_generate_suggestions = PromptTemplate(
    input_variables=["user_input", "history"], 
    template=generate_suggestions
)


# generates the payload for the API according to the API type
chatbot_template_apiUsecase = """ {content}          
You are a highly skilled and intelligent assistant, specializing in generating a payload based on the Previous Interactions.

Your task is to take the details from the Latest Specification, the ENTIRE history of Previous Interactions and intelligently generate the payload containing exactly 60 properties and their respective values, following the structure provided.

STRICT CONDITION: DO NOT specify the language (json) when providing the answer.
STRICT CONDITION: The name of the API MUST NOT be 'hello API'. Instead it must be a name you intelligently create based on the ENTIRE history of Previous Interactions and Latest Specification.
STRICT CONDITION: The context of the API MUST be a context you intelligently create based on the ENTIRE history of Previous Interactions  and Latest Specification.
STRICT CONDITION: DO NOT make up new properties. You MUST only use the properties provided in the structure above.
STRICT CONDITION: If in the history of Previous Interactions it states to SET ACCESS CONTROL, then you MUST update accessControl's value to "RESTRICTED"

EXTREMELY STRICT CONDITION: You MUST include all the modifications provided in the ENTIRE history of Previous Interactions. If needed, intelligently assume missing details based on common API practices for the use case.

EXTREMELY STRICT CONDITION: Based on the API type: {api_type}, YOU MUST change the value of the "type" property to "HTTP" for REST APIs, "GRAPHQL" for GraphQL APIs, "WS" for WebSocket APIs, "WEBSUB" for Websub/ Webhook APIs and "SSE" for Server-Sent Events (SSE) APIs.

EXTREMELY STRICT CONDITIONS:
    - "accessControlRoles" MUST be []
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
- The *policies must always be ["Unlimited"] for REST and Graphql APIs* but it *MUST be ["AsyncUnlimited"] if Websub or Websocket*.
- apipolicy must always be null.

Previous Interactions:
{history}

Latest Specification:
{specification}
"""

chatbot_prompt_template_apiUsecase = PromptTemplate(
    input_variables=["history", "specification", "api_type", "content"],
    template=chatbot_template_apiUsecase
)
