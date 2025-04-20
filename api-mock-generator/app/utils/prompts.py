def generate_mocks_prompt(config):
  prompt = """Generate ES3 JavaScript for rhinojs to mock OpenAPI from: the given OpenAPI Specification

Instructions:
- Use mc.getProperty() and mc.getPayloadJSON() for request data.
- Get path params via mc.getProperty('uri.var.{paramName}').
- Get Query Parameters via mc.getProperty('query.param.{paramName}').
- Prepopulate mockDB with 3+ records.
- Always Load and persist mockDB using mc.getProperty('mockDB') and mc.setProperty('mockDB', JSON.stringify(db)).
- Handle all status codes, support JSON/XML.
- Do not use try catch error andlings
- Do not use break; other than inside loops
- Do not use keywords for var names like name, event etc...
- make sure when reading any variable if it is undefined then handle that error never call a operand without checking if it is defined
- Use only loops (never use find, filter, map, reduce, spread like {{...orders.id}}).
- Avoid return; use break to exit loops when needed but ensure required payload and http_sc is set correctly.
- Validate all requests and payloads.
- Assign responses via mc.setProperty() and mc.setPayloadJSON().
- Ensure mock server behaves like a real one and the implementation is simple.
- Comparisons should use == instead of ===.
- The output must strictly follow the schema given in the example.
- All data (e.g., in queries, params, and mockDB) is treated as strings. For comparisons (e.g., dates or other types), 
ensure the data is parsed into the correct format before comparing (e.g., >=). Handle parsing errors gracefully 
to avoid runtime exceptions.
- Accept type can be /*/ as well then default to application/json. And always set the accept type
- {{mockDB:" ....", paths:{{/pets:{{get:{{code:" ...."}}}}, /pets/{{petId}}:{{get:{{code:" ...."}}}}}}}}

Expected Output Example:
{{ "mockDB": "{{\\"pets\\":[{{\\"id\\":1,\\"name\\":\\"Whiskers\\"}},{{\\"id\\":2,\\"name\\":\\"Buddy\\"}},{{\\"id\\":3,\\"name\\":\\"Mittens\\"}}]}}", "paths": {{
  "/pets": {{
    "get": "var accept = mc.getProperty('AcceptHeader') || 'application/json';\\n
if (accept == null || accept == '/*/') {{ accept = 'application/json'; }}\\n
  mc.setProperty('CONTENT_TYPE', accept);\\n
  var db = JSON.parse(mc.getProperty('mockDB') || '{{}}');\\n
  mc.setPayloadJSON(db.pets || []);\\n
  mc.setProperty('HTTP_SC', '200');\\n
"}},\n
    "post": "var accept = mc.getProperty('AcceptHeader') || 'application/json';\\n
if (accept == null || accept == '/*/') {{ accept = 'application/json'; }}\\n
  mc.setProperty('CONTENT_TYPE', accept);\\n
  var db = JSON.parse(mc.getProperty('mockDB') || '{{}}');\\n
  var body = mc.getPayloadJSON();\\n
  if (body && body.id && body.name) {{\\n
    db.pets = db.pets || [];\\n
    db.pets.push(body);\\n
    mc.setProperty('HTTP_SC', '201');\\n
  }} else {{\\n
    mc.setProperty('HTTP_SC', '400');\\n
    mc.setPayloadJSON({{ message: 'Invalid request, must contain id and name' }});\\n
  mc.setProperty('mockDB', JSON.stringify(db));\\n
"}}\n
  }},\n
  "/pets/{{petId}}": {{
    "get": "var accept = mc.getProperty('AcceptHeader') || 'application/json';\\n
if (accept == null || accept == '/*/') {{ accept = 'application/json'; }}\\n
  mc.setProperty('CONTENT_TYPE', accept);\\n
  var id = parseInt(mc.getProperty('uri.var.petId'), 10);\\n
  var db = JSON.parse(mc.getProperty('mockDB') || '{{}}');\\n
  var pet = null;\\n
  for (var i = 0; i < (db.pets || []).length; i++) {{\\n
    if (db.pets[i].id == id) {{\\n
      pet = db.pets[i];\\n
      break;\\n
    }}\\n
  }}\\n
  mc.setPayloadJSON(pet || {{ message: 'Pet not found' }});\\n
  mc.setProperty('HTTP_SC', pet ? '200' : '404');\\n
"}}\n
  }}\n
}} }}
While making sure the Functionality is 100% correct as the first priority
"""

  if (config.get('instructions')):
    prompt = prompt + f"""
        Try to Do it according to the following Instructions as well:
        {config.get('instructions')}
        """
    
  return prompt

def generate_mocks_sys_msg(spec: dict, config: str) -> str:
  return f"Design a scalable, secure, and well-documented mock API for testing for the OpenAPI Specification {spec}, ensuring ease of use and maintenance."

def fix_schema_prompt(response):
  return f"""
  The given response has a schema issue. Please fix the schema to ensure it is valid and adheres to the Schema Given below.
  Dont change the functionality of the code
  The response is:
  {response}
    """

def modify_method_prompt(script, instructions, is_default_script):
  prompt = f"""Modify the given ES3 JavaScript script for rhinojs to update the behavior of an existing OpenAPI mock method based on the provided context.
Instructions:
- Update the script to align with the Instructions: '{instructions}'.
- If the instructions cannot be fully achieved, prioritize returning a functioning and correct script over strictly adhering to the context.
"""
  if (not is_default_script):
    prompt = prompt + """
- Ensure the script adheres to the following rules:
  - Use mc.getProperty() and mc.getPayloadJSON() for request data.
  - Access path params via mc.getProperty('uri.var.{paramName}').
  - Get Query Parameters via mc.getProperty('query.param.{paramName}').
  - Persist changes to mockDB using mc.getProperty('mockDB') and mc.setProperty('mockDB', JSON.stringify(db)).
  - Handle all status codes and support both JSON/XML responses.
  - Use only loops (never use find, filter, map, reduce, or spread like {{...orders.id}}).
  - Avoid return; use break to exit loops when necessary, ensuring payload and http_sc are set correctly.
  - Validate all requests and payloads.
  - Assign responses via mc.setProperty() and mc.setPayloadJSON().
  - Ensure the mock server behaves like a real one.
  - Use == for comparisons instead of ===.
  - Default to application/json for Accept type if /*/ is provided.
  - Maintain the structure and logic of the original script while incorporating the new instructions.
"""
    prompt = prompt + f"""
Expected Output Format:
{{ "modified_script": "The modified script" }}

The already existing script is:
{script}

make sure to keep the functionality 100% correct as the first priority

since all of the other endpoint scripts are already there, dont make changes that will cause runtime errors or db structure changes

Expected Output:
- A modified script that reflects the new instructions (if possible) and adheres to the above rules.
- If the instructions cannot be fully achieved, the output must still be a functioning and correct script.
- Modification to the structure of the code should be minimal and only be done to achive the instructions
"""
    return prompt
  else:
    prompt = prompt + """
- Ensure the script adheres to the following rules:
  - Only Change the contents in the response or response codes don't change any other structures.
  - Maintain the structure and logic of the original script while incorporating the new instructions.
"""
    prompt = prompt + f"""
Expected Output Format:
{{ "modified_script": "The modified script" }}

The already existing script is:
{script}

make sure to keep the functionality 100% correct as the first priority

dont make changes that will cause runtime errors

Expected Output:
- A modified script that reflects the new instructions (if possible) and adheres to the above rules.
- If the instructions cannot be fully achieved, the output must still be a functioning and correct script.
- Modification to the structure of the code should be minimal and only be done to achive the instructions
"""
    return prompt 

def modify_method_sys_msg(method, path, method_spec):
  return f"Modify the script for the {method.upper()} method at the {path} endpoint based on the OpenAPI Specification part {method_spec}. Ensure the script is functional, secure, and behaves like a real API, while supporting scalability and maintainability."

def generate_mocks_sim_resource_prompt(config, paths_batch, mockDB=None):
  if len(paths_batch) == 1 and paths_batch[0] == "mockDB":
    # Generate prompt specifically for mockDB
    prompt = """Generate ES3 JavaScript for rhinojs to create and manage a mockDB.

Instructions:
- Prepopulate mockDB with 3+ records to match the given openAPI spec.
- Always Load and persist mockDB using mc.getProperty('mockDB') and mc.setProperty('mockDB', JSON.stringify(db)).
- Ensure mockDB is structured as a JSON object and supports CRUD operations.
- Validate the data structure and ensure it is consistent.
- All data in mockDB are treated as strings.

Expected Output Example:
{{ "mockDB": "{{\\"pets\\":[{{\\"id\\":1,\\"name\\":\\"Whiskers\\"}},{{\\"id\\":2,\\"name\\":\\"Buddy\\"}},{{\\"id\\":3,\\"name\\":\\"Mittens\\"}}]}}" }}
"""
    return prompt

    # Default behavior for generating scripts for a specific path
  
  prompt = f"""Generate ES3 JavaScript for rhinojs to mock OpenAPI strictly only for: {paths_batch}

Instructions:
- Use mc.getProperty() and mc.getPayloadJSON() for request data.
- Get path params via mc.getProperty('uri.var.{{paramName}}').
- Get Query Parameters via mc.getProperty('query.param.{{paramName}}').
- Prepopulate mockDB with 3+ records.
- Always Load and persist mockDB using mc.getProperty('mockDB') and mc.setProperty('mockDB', JSON.stringify(db)).
- Handle all status codes, support JSON/XML.
- Do not use try catch error andlings
- Do not use break; other than inside loops
- Do not use keywords for var names like name, event etc...
- make sure when reading any variable if it is undefined then handle that error never call a operand without checking if it is defined
- Use only loops (never use find, filter, map, reduce, spread like {{...orders.id}}).
- Avoid return; use break to exit loops when needed but ensure required payload and http_sc is set correctly.
- Validate all requests and payloads.
- Generate scripts only for all the methods available in the respective paths and keep the implementation simple
"""
  prompt = prompt + f"""
- Make sure the script handles the data in {mockDB} which is the current mockDB correctly with correct structure.
- Assign responses via mc.setProperty() and mc.setPayloadJSON().
- Ensure mock server behaves like a real one.
- Comparisons should use == instead of ===.
- The output must strictly follow the schema given in the example.
- All data (e.g., in queries, params, and mockDB) is treated as strings. For comparisons (e.g., dates or other types), 
ensure the data is parsed into the correct format before comparing (e.g., >=). Handle parsing errors gracefully 
to avoid runtime exceptions.
- Accept type can be /*/ as well then default to application/json. And always set the accept type.
- Generate scripts for all methods (e.g., GET, POST, PUT, DELETE) that are defined in the given path.

Expected Output Example:
{{ "/pets": {{"post": "var accept = mc.getProperty('AcceptHeader') || 'application/json';\\n
if (accept == null || accept == '/*/') {{ accept = 'application/json'; }}\\n
  mc.setProperty('CONTENT_TYPE', accept);\\n
  var db = JSON.parse(mc.getProperty('mockDB') || '{{}}');\\n
  var body = mc.getPayloadJSON();\\n
  if (body && body.id && body.name) {{\\n
    db.pets = db.pets || [];\\n
    db.pets.push(body);\\n
    mc.setProperty('HTTP_SC', '201');\\n
  }} else {{\\n
    mc.setProperty('HTTP_SC', '400');\\n
    mc.setPayloadJSON({{ message: 'Invalid request, must contain id and name' }});\\n
  mc.setProperty('mockDB', JSON.stringify(db));\\n
"}}\n
  "/pets/{{petId}}": {{
    "get": "var accept = mc.getProperty('AcceptHeader') || 'application/json';\\n
if (accept == null || accept == '/*/') {{ accept = 'application/json'; }}\\n
  mc.setProperty('CONTENT_TYPE', accept);\\n
  var id = parseInt(mc.getProperty('uri.var.petId'), 10);\\n
  var db = JSON.parse(mc.getProperty('mockDB') || '{{}}');\\n
  var pet = null;\\n
  for (var i = 0; i < (db.pets || []).length; i++) {{\\n
    if (db.pets[i].id == id) {{\\n
      pet = db.pets[i];\\n
      break;\\n
    }}\\n
  }}\\n
  mc.setPayloadJSON(pet || {{ message: 'Pet not found' }});\\n
  mc.setProperty('HTTP_SC', pet ? '200' : '404');\\n
"}}\n
  }}\n
}}
While making sure the Functionality is 100% correct as the first priority
"""

  if config.get('instructions'):
    prompt = prompt + f"""
      Try to Do it according to the following Instructions as well:
      {config.get('instructions')}
      """ 
  return prompt
