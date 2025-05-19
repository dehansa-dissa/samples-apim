"""
 Copyright (c) 2025, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.

  This software is the property of WSO2 LLC. and its suppliers, if any.
  Dissemination of any information or reproduction of any material contained
  herein is strictly forbidden, unless permitted by WSO2 in accordance with
  the WSO2 Commercial License available at http://wso2.com/licenses.
  For specific language governing the permissions and limitations under
  this license, please see the license as well as any agreement you’ve
  entered into with WSO2 governing the purchase of this software and any
"""
import openai
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from config import API_TYPE, API_VERSION, API_KEY, AZURE_ENDPOINT
from utils import (
    load_openapi_specifications_from_json,
    combine_openapi_specs_to_text
)
from prompts import create_merge_specs_prompt
from llm import create_llm

app = Flask(__name__)
CORS(app)

openai.api_type = API_TYPE
openai.api_version = API_VERSION
openai.api_key = API_KEY
openai.azure_endpoint = AZURE_ENDPOINT

# Flask route to handle the merging of OpenAPI specifications that accepts file uploads or a raw JSON string
@app.route("/merge-openapi-specs", methods=["POST"])
def merge_openapi_specs():
    api_specifications = []
    
    # Handle case where the JSON string is provided in the request body
    try:
        # Check if the request body is a valid JSON in the expected structure
        if request.is_json:
            json_payload = request.get_json()
            
            # Extract specifications
            if "specifications" in json_payload:
                json_data = json_payload["specifications"]

                # Parse and load specifications from the JSON data
                specs = load_openapi_specifications_from_json(json_data)
                api_specifications.extend(specs)
            else:
                return jsonify({"error": "No specifications provided in JSON payload"}), 400
            
            # Extract contexts
            if "contexts" in json_payload:
                api_contexts = json_payload["contexts"]
        else:
            json_data = request.get_data(as_text=True)
            if not json_data:
                return jsonify({"error": "No JSON string provided"}), 400
                
            # Parse and load specifications from the JSON string
            specs = load_openapi_specifications_from_json(json_data)
            api_specifications.extend(specs)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # Combine the loaded OpenAPI specifications into a single text representation
    combined_api_specs_text = combine_openapi_specs_to_text(api_specifications)

    prompt_template = create_merge_specs_prompt(combined_api_specs_text, api_contexts)
    llm = create_llm()
    llm_chain = prompt_template | llm

    response = llm_chain.invoke({'specs_text': combined_api_specs_text, 'api_contexts': api_contexts})
    answer_text = response.content

    return Response(answer_text, content_type='text/plain')

if __name__ == "__main__":
    app.run(debug=True)