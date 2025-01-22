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
import json
import yaml

# Loads OpenAPI specification from file
def load_openapi_specification_from_file(file):
    if file.filename.endswith('.json'):
        return json.load(file)
    elif file.filename.endswith('.yaml') or file.filename.endswith('.yml'):
        return yaml.safe_load(file)
    else:
        raise ValueError("Unsupported file type. Please upload a .json or a .yaml file.")

# Loads multiple OpenAPI specifications from a single JSON string
def load_openapi_specifications_from_json(data):
    try:
        specs = data.strip().split('}\n{')
        api_specs = []

        for i, spec in enumerate(specs):
            if i > 0:
                spec = '{' + spec
            if i < len(specs) - 1:
                spec += '}'

            parsed_spec = json.loads(spec)
            api_specs.append(parsed_spec)
            api_specs.append(parsed_spec)

        return api_specs
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON string provided.")

# Combines API specifications into a single text representation
def combine_openapi_specs_to_text(api_specs):
    combined_text = ""
    for spec in api_specs:
        combined_text += json.dumps(spec, indent=2) + "\n\n"
    return combined_text