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
from langchain.prompts import PromptTemplate

merge_specs_prompt = """

Api Specifications :
{specs_text}

Api Names and their respective contexts:
{api_contexts}

PRIMARY OBJECTIVES: 
1. Merge the provided API specifications into a single cohesive specification.
2. Prefix all resource paths with their corresponding API context and version.
3. Create an appropriate title and description for the merged API.
4. The server URL of the merged API should always be given as :
    servers:
    - url: https://localhost:8243
    - url: http://localhost:8280

CRITICAL REQUIREMENTS:
- EVERY endpoint path MUST be prefixed with its corresponding API context and version.
- Preserve the EXACT case sensitivity of all identifiers (paths, parameters, schemas, etc.).
- Maintain all security definitions, schemas, and other components.
- Resolve any conflicts between duplicate operations or schemas.
- Ensure the output is valid OpenAPI/Swagger specification.

STRICT CONSTRAINTS:
- DO NOT modify the original API contexts or versions in any way.
- DO NOT use generic titles like "Merged API" - create a meaningful title that reflects the combined functionality.
- DO NOT include any markdown code block formatting or language indicators in your response.
- DO NOT include any explanations or comments outside the specification.
- DO NOT include any text before or after the specification.

OUTPUT FORMAT
Provide ONLY the complete merged OpenAPI specification as valid JSON without any surrounding text, explanations, or markdown formatting.
"""

def create_merge_specs_prompt(specs_text, api_contexts):
    return PromptTemplate(
        input_variables=["specs_text", "api_contexts"],
        template=merge_specs_prompt
    )