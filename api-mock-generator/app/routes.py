from flask import Blueprint, request, jsonify
from app.services.ai_operations import generate_mock_scripts_at_once, modify_method, generate_mock_scripts_batch_wise
from app.utils.dev_tools import records_from_spec, rec

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/ai/api-mock/generate-mocks', methods=['POST'])
def generate_mock_scripts_endpoint():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON payload", "details": str(e)}), 400

    open_api_spec = data.get('apiDefinition')
    config = data.get('config')

    resourcewise = True
    if resourcewise:
        mock_scripts = generate_mock_scripts_batch_wise(open_api_spec, config)
    else:
        mock_scripts = generate_mock_scripts_at_once(open_api_spec, config)
    return mock_scripts, 201


@api_blueprint.route('/ai/api-mock/modify-method', methods=['POST'])
def modify_method_endpoint():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON payload", "details": str(e)}), 400

    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    open_api_spec = data.get('apiDefinition')
    config = data.get('config')
    path = config.get('modify').get('path')
    method = config.get('modify').get('method')
    script = config.get('script')
    instructions = config.get('instructions')
    #return {"modified_script": script+ "aaaaaaa"}, 201
    if not (open_api_spec and path and method and script and instructions):
        return jsonify({"error": "Open API Spec, path, method, script, and instructions are required"}), 400

    mock_script = modify_method(open_api_spec,script,path,method, instructions)
    return jsonify(mock_script), 201