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
import re
from typing import List, Dict
from llm import chat
from prompts import create_summarization_prompt, create_method_mapping_prompt, create_code_gen_prompt, get_language_specific_content

# Extract method information and associated comments from Java or JavaScript source code
def extract_method_info(content: str, language: str) -> List[Dict]:
    methods = []
    
    if language.lower() == "java":
        javadoc_pattern = r'/\*\*(.*?)\*/'
        method_pattern = r'public\s+(?:.*?)\s+(\w+?(?:Get|Put|Post|Delete|Patch)(?:Call|WithHttpInfo|Async)?)\s*\([^)]*\)'
        
        # Find all matches with their positions
        current_pos = 0
        while current_pos < len(content):
            javadoc_match = re.search(javadoc_pattern, content[current_pos:], re.DOTALL)
            if not javadoc_match:
                break
                
            javadoc = javadoc_match.group(1)
            # Clean up Javadoc
            javadoc = re.sub(r'\s*\*\s*', ' ', javadoc).strip()

            current_pos += javadoc_match.end()
            
            # Look for method declaration after Javadoc
            method_match = re.search(method_pattern, content[current_pos:])
            if method_match:
                method_name = method_match.group(1)
                # Check if method name ends with one of the expected patterns
                if any(method_name.endswith(suffix) for suffix in [
                    'GetCall', 'Get', 'GetWithHttpInfo', 'GetAsync',
                    'PutCall', 'Put', 'PutWithHttpInfo', 'PutAsync',
                    'PostCall', 'Post', 'PostWithHttpInfo', 'PostAsync',
                    'DeleteCall', 'Delete', 'DeleteWithHttpInfo', 'DeleteAsync',
                    'PatchCall', 'Patch', 'PatchWithHttpInfo', 'PatchAsync'
                ]):
                    methods.append({
                        'methodName': method_name,
                        'comments': javadoc
                    })
                current_pos += method_match.end()
            else:
                current_pos += 1
                
    elif language.lower() == "javascript":
        jsdoc_pattern = r'/\*\*(.*?)\*/'
        method_pattern = r'(\w+(?:Get|Put|Post|Delete|Patch)?)\s*\([^)]*\)\s*{'
        
        # Find all matches with their positions
        current_pos = 0
        while current_pos < len(content):
            jsdoc_match = re.search(jsdoc_pattern, content[current_pos:], re.DOTALL)
            if not jsdoc_match:
                break
                
            jsdoc = jsdoc_match.group(1)
            # Clean up JSDoc
            jsdoc = re.sub(r'\s*\*\s*', ' ', jsdoc).strip()

            current_pos += jsdoc_match.end()
            
            # Look for method declaration after JSDoc
            method_match = re.search(method_pattern, content[current_pos:])
            if method_match:
                method_name = method_match.group(1)
                # For JS, filter constructor and other non-API methods
                if (method_name != 'constructor' and 
                    not method_name.startswith('_') and 
                    not method_name.endswith('Callback')):
                    methods.append({
                        'methodName': method_name,
                        'comments': jsdoc
                    })
                current_pos += method_match.end()
            else:
                current_pos += 1
    else:
        raise ValueError(f"Unsupported language: {language}")
        
    return methods

# Format the extracted method information in a clear, structured way for LLM usage
def format_methods_for_llm(methods: List[Dict]) -> str:
    if not methods:
        return "No methods found."
    
    formatted_output = "# SDK METHODS \n\n"
    
    # Group methods by HTTP verb for better organization
    http_verbs = ["Get", "Post", "Put", "Delete", "Patch"]
    
    for verb in http_verbs:
        verb_methods = [m for m in methods if verb.lower() in m['methodName'].lower()]
        if not verb_methods:
            continue
            
        formatted_output += f"## {verb.upper()} Methods\n\n"
        
        for method in verb_methods:
            formatted_output += f" `{method['methodName']}`\n\n"
            formatted_comments = method['comments'].replace('\n', '\n> ').strip()
            formatted_output += f" {formatted_comments}\n\n"
            
        formatted_output += "---\n\n"
    
    return formatted_output

# Generate a summarized version of the API specification based on use case
def summarize_api_specification(use_case, api_spec):

    prompt_template = create_summarization_prompt()
    
    prompt = prompt_template.format(
        use_case=use_case,
        merged_spec=api_spec,
    )
    
    summary_response = chat.invoke(prompt)
    return summary_response.content

# Match relevant SDK methods to the API endpoints
def map_methods_to_endpoints(summarized_spec, formatted_methods):

    prompt_template = create_method_mapping_prompt()
    
    prompt = prompt_template.format(
        summarized_spec=summarized_spec,
        formatted_methods=formatted_methods
    )
    
    response = chat.invoke(prompt)
    return response.content

# Generate application code based on use case and language
def generate_code_response(user_input, merged_spec, sdk_methods, language):
    lang_content = get_language_specific_content(language)

    prompt_template = create_code_gen_prompt()

    prompt = prompt_template.format(
        question=user_input, 
        merged_spec = merged_spec,
        sdk_methods=sdk_methods,
        language=language,
        example_code=lang_content["example_code"],
        language_specific_instructions=lang_content["language_specific_instructions"]
    )

    response = chat.invoke(prompt)
    return response.content