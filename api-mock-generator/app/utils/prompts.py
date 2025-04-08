def generate_mocks_prompt(config):
    prompt = """Generate ES3 JavaScript for rhinojs to mock OpenAPI from: the given OpenAPI Specification

Instructions:
- Use mc.getProperty() and mc.getPayloadJSON() for request data.
- Get path params via mc.getProperty('uri.var.{paramName}').
- Get Query Parameters via mc.getProperty('query.param.{paramName}').
- Prepopulate mockDB with 3+ records.
- Always Load and persist mockDB using mc.getProperty('mockDB') and mc.setProperty('mockDB', JSON.stringify(db)).
- Handle all status codes, support JSON/XML.
- Use only loops (never use find, filter, map, reduce, spread like {{...orders.id}}).
- Avoid return; use break to exit loops when needed but ensure required payload and http_sc is set correctly.
- Validate all requests and payloads.
- Assign responses via mc.setProperty() and mc.setPayloadJSON().
- Ensure mock server behaves like a real one.
- Comparisons should use == instead of ===.
- The output must strictly follow the schema given in the example.

- Accept type can be /*/ as well then default to application/json. And always set the accept type
- {{mockDB:" ....", paths:{{/pets:{{get:{{code:" ...."}}}}, /pets/{{petId}}:{{get:{{code:" ...."}}}}}}}}

Expected Output Example:
{{ "mockDB": "{{\\"pets\\":[{{\\"id\\":1,\\"name\\":\\"Whiskers\\"}},{{\\"id\\":2,\\"name\\":\\"Buddy\\"}},{{\\"id\\":3,\\"name\\":\\"Mittens\\"}}]}}", "paths": {{
  "/pets": {{
    "get": {{"code": "var accept = mc.getProperty('AcceptHeader') || 'application/json';\\n
if (accept == null || accept == '/*/') {{ accept = 'application/json'; }}\\n
  mc.setProperty('CONTENT_TYPE', accept);\\n
  var db = JSON.parse(mc.getProperty('mockDB') || '{{}}');\\n
  mc.setPayloadJSON(db.pets || []);\\n
  mc.setProperty('HTTP_SC', '200');\\n
"}},\n
    "post": {{"code": "var accept = mc.getProperty('AcceptHeader') || 'application/json';\\n
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
    "get": {{"code": "var accept = mc.getProperty('AcceptHeader') || 'application/json';\\n
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

def modify_method_prompt(script, instructions):
    return f"""Modify the given ES3 JavaScript script for rhinojs to update the behavior of an existing OpenAPI mock method based on the provided context.

Instructions:
- Update the script to align with the Instructions: '{instructions}'.
- If the context cannot be fully achieved, prioritize returning a functioning and correct script over strictly adhering to the context.
- Ensure the script adheres to the following rules:
  - Use mc.getProperty() and mc.getPayloadJSON() for request data.
  - Access path params via mc.getProperty('uri.var.paramName').
  - Persist changes to mockDB using mc.getProperty('mockDB') and mc.setProperty('mockDB', JSON.stringify(db)).
  - Handle all status codes and support both JSON/XML responses.
  - Use only loops (never use find, filter, map, reduce, or spread like {{...orders.id}}).
  - Avoid return; use break to exit loops when necessary, ensuring payload and http_sc are set correctly.
  - Validate all requests and payloads.
  - Assign responses via mc.setProperty() and mc.setPayloadJSON().
  - Ensure the mock server behaves like a real one.
  - Use == for comparisons instead of ===.
  - Default to application/json for Accept type if /*/ is provided.
- Maintain the structure and logic of the original script while incorporating the new context.

Expected Output Format:
{{ "modified_script": "The modified script" }}

The already existing script is:
{script}

make sure to keep the functionality 100% correct as the first priority

since all of the other endpoint scripts are there dont make changes that will cause runtime errors or db structure changes

Expected Output:
- A modified script that reflects the new context (if possible) and adheres to the above rules.
- If the context cannot be fully achieved, the output must still be a functioning and correct script.
"""

def modify_method_sys_msg(method, path, method_spec):
    return f"Modify the script for the {method.upper()} method at the {path} endpoint based on the OpenAPI Specification part {method_spec}. Ensure the script is functional, secure, and behaves like a real API, while supporting scalability and maintainability."

