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

MERGE_SPECS_TEMPLATE = """
{specs_text}

You are given either two or more API specifications. Your task is to merge these specifications into a single specification. 
You will also have to add a prefix to each of the paths in the merged specification. 

For example, this is the server url of an api : https://localhost:8243/pizzashack/1.0.0 , where pizzashack is the api context, and 1.0.0 is the api version. 
You will have to extract the context and the version (pizzashack/1.0.0) and this will be considered as the prefix to include in front of each path. 

The prefix MUST be extracted from the server url of each api and added to their respective paths in the merged api. 
You MUST give a suitable title and a brief description for the merged api. The server url of the merged api shall consist of the part before the api context.
DO NOT include 'Merged api' as the title or description.

STRICT CONDITION: DO NOT specify the language (json) when providing the answer.
"""

def create_merge_prompt(specs_text):
    return PromptTemplate(
        input_variables=["specs_text"],
        template=MERGE_SPECS_TEMPLATE
    )