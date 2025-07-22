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
    extract_method_info,
    format_methods_for_llm,
    summarize_api_specification,
    map_methods_to_endpoints,
    generate_code_response ,
    extract_imports_from_sdk
)
from prompts import create_merge_specs_prompt
from llm import create_llm

app = Flask(__name__)

openai.api_type = API_TYPE
openai.api_version = API_VERSION
openai.api_key = API_KEY
openai.azure_endpoint = AZURE_ENDPOINT

@app.route("/test", methods=["GET"])
def test():
    return jsonify({"status": "Flask server is running"})

# Flask route to handle the merging of OpenAPI specifications that accepts file uploads or a raw JSON string
@app.route("/merge-openapi-specs", methods=["POST"])
def merge_openapi_specs():
    try:
        if request.is_json:
            json_payload = request.get_json()            
            if "specifications" in json_payload:
                specifications = json_payload["specifications"]
            else:
                return jsonify({"error": "No specifications provided in JSON payload"}), 400
            
            if "contexts" in json_payload:
                api_contexts = json_payload["contexts"]
            else:
                api_contexts = None
        else:
            specifications = request.get_data(as_text=True)
            if not specifications:
                return jsonify({"error": "No JSON string provided"}), 400
            
        prompt_template = create_merge_specs_prompt(specifications, api_contexts)
        llm = create_llm()
        llm_chain = prompt_template | llm
        response = llm_chain.invoke({'specs_text': specifications, 'api_contexts': api_contexts})
        answer_text = response.content

        return Response(
            answer_text,
            content_type='application/json'
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
# Flask route to generate application code based on use case and language
@app.route('/generate-application-code', methods=['POST'])
def process_java_file():
    try:
        # Extract JSON data from request body
        data = request.get_json()
        use_case = data.get("useCase", "")
        methods_file = data.get("sdkMethodsFile", "")
        api_spec = data.get("APISpecification", "")
        language = data.get("language", "")

        # Extract and format SDK method names and its associated comments
        methods = extract_method_info(methods_file, language)
        formatted_methods = format_methods_for_llm(methods)

        # Extract relevant endpoints from spec based on usecase and map relevant SDK methods to endpoints
        summarized_spec = summarize_api_specification(use_case, api_spec)
        extracted_methods = map_methods_to_endpoints(summarized_spec, formatted_methods)

        extracted_imports = extract_imports_from_sdk(methods_file, language)

        # Generate final code based on use case and language
        application_code = generate_code_response(use_case, summarized_spec, extracted_methods, language, extracted_imports)

        if application_code == "The provided use case is invalid":
            error_response = {
                "status": "error",
                "error": application_code
            }
            return jsonify(error_response), 400

        return Response(
            application_code,
            content_type='application/json'
        )

    except Exception as e:
        error_response = {
            "status": "error",
            "message": "Failed to generate application code",
            "error": str(e)
        }
        return jsonify(error_response), 500
    
if __name__ == "__main__":
    app.run(debug=True, port=5001)