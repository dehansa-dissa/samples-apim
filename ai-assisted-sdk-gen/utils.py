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
        # This single regex finds a Javadoc block and the public method declaration that immediately follows it.
        # It's designed to be more general and capture any valid method name.
        # - Group 1 (.*?): Captures the content inside the Javadoc block.
        # - Group 2 ([\w\d_]+): Captures the method name. This is the key change.
        pattern = re.compile(
            r'/\*\*(.*?)\*/\s*public\s+(?:.*?)\s+([\w\d_]+)\s*\([^)]*\)',
            re.DOTALL  # re.DOTALL allows '.' to match newlines, which is crucial for the Javadoc block.
        )

        # Find all non-overlapping matches of the pattern in the string.
        matches = re.findall(pattern, content)

        for match in matches:
            javadoc, method_name = match
            # Clean up Javadoc
            javadoc = re.sub(r'\s*\*\s*', ' ', javadoc).strip()
            methods.append({
                'methodName': method_name,
                'comments': javadoc
            })
                
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

def extract_imports_from_sdk(content: str, language: str) -> List[str]:
    """
    Extract import statements from the SDK methods file content
    """
    imports = []
    
    if language.lower() == "java":
        # Java import pattern
        import_pattern = r'import\s+([a-zA-Z0-9._*]+);'
        matches = re.findall(import_pattern, content)
        imports = [f"import {match};" for match in matches]

        default_api_import = extract_default_api_import_from_sdk(content, language)
        if default_api_import:
            imports.append(default_api_import)
        
    elif language.lower() == "javascript":
        # JavaScript require/import patterns
        require_pattern = r'(?:const|var|let)\s+.*?=\s+require\([\'"]([^\'"]+)[\'"]\)'
        import_pattern = r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]'
        
        require_matches = re.findall(require_pattern, content)
        import_matches = re.findall(import_pattern, content)
        
        imports.extend([f"const ... = require('{match}');" for match in require_matches])
        imports.extend([f"import ... from '{match}';" for match in import_matches])

        default_api_import = extract_default_api_import_from_sdk(content, language)
        if default_api_import:
            imports.append(default_api_import)

    # Remove duplicates while preserving order
    seen = set()
    unique_imports = []
    for imp in imports:
        if imp not in seen:
            seen.add(imp)
            unique_imports.append(imp)
    
    return unique_imports

def extract_default_api_import_from_sdk(content: str, language: str) -> str:
    """
    Extract DefaultApi class import location from the SDK content itself
    """
    if language.lower() == "java":
        # Look for package declaration in the DefaultApi class file
        package_pattern = r'package\s+([a-zA-Z0-9._]+);'
        package_match = re.search(package_pattern, content)
        
        if package_match:
            package_name = package_match.group(1)
            return f"import {package_name}.DefaultApi;"
        
        # Fallback: Look for existing DefaultApi import in the content
        default_api_import_pattern = r'import\s+([a-zA-Z0-9._]+\.DefaultApi);'
        import_match = re.search(default_api_import_pattern, content)
        if import_match:
            return f"import {import_match.group(1)};"
        
    elif language.lower() == "javascript":
        if 'module.exports' in content and 'DefaultApi' in content:
            # CommonJS pattern
            return "const DefaultApi = require('./api/DefaultApi');"
        elif 'export' in content and 'DefaultApi' in content:
            # ES6 module pattern
            return "import DefaultApi from './api/DefaultApi';"

# Generate application code based on use case and language
def generate_code_response(user_input, merged_spec, sdk_methods, language, extracted_imports):
    lang_content = get_language_specific_content(language)

    prompt_template = create_code_gen_prompt()

    prompt = prompt_template.format(
        question=user_input, 
        merged_spec = merged_spec,
        sdk_methods=sdk_methods,
        language=language,
        example_code=lang_content["example_code"],
        language_specific_instructions=lang_content["language_specific_instructions"],
        sdk_imports="\n".join(extracted_imports)
    )

    response = chat.invoke(prompt)
    return response.content