from flask import Blueprint, request, jsonify
from app.services.ai_operations import generate_mock_scripts, modify_method
from app.utils.dev_tools import records_from_spec, rec

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/ai/api-mock/generate-mocks', methods=['POST'])
def generate_mock_scripts_endpoint():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON payload", "details": str(e)}), 400

    open_api_spec = data.get('swagger')
    config = data.get('config')
    mock_scripts = generate_mock_scripts(open_api_spec, config)
    return mock_scripts, 201


@api_blueprint.route('/ai/api-mock/modify-method', methods=['POST'])
def modify_method_endpoint():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON payload", "details": str(e)}), 400

    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400

    open_api_spec = data.get('swagger')
    config = data.get('config')
    path = config.get('modify').get('path')
    method = config.get('modify').get('method')
    is_default_script = config.get('modify').get('defaultScript')
    script = config.get('script')
    instructions = config.get('instructions')
    if not (open_api_spec and path and method and script and instructions):
        return jsonify({"error": "Open API Spec, path, method, script, and instructions are required"}), 400

    mock_script = modify_method(open_api_spec,script,path,method, instructions, is_default_script)
    return jsonify(mock_script), 201