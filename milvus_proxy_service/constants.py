"""
 Copyright (c) 2024, WSO2 LLC. (http://www.wso2.com). All Rights Reserved.

  This software is the property of WSO2 LLC. and its suppliers, if any.
  Dissemination of any information or reproduction of any material contained
  herein is strictly forbidden, unless permitted by WSO2 in accordance with
  the WSO2 Commercial License available at http://wso2.com/licenses.
  For specific language governing the permissions and limitations under
  this license, please see the license as well as any agreement you’ve
  entered into with WSO2 governing the purchase of this software and any
"""

LOG_LEVEL = "LOG_LEVEL"
CHOREO_MILVUS_URL = "MILVERSE_URL"
CHOREO_MILVUS_API_KEY = "MILVERSE_API_KEY"
DEVANT_MILVUS_URL = "DEVANT_MILVUS_URL"
DEVANT_MILVUS_API_KEY = "DEVANT_MILVUS_API_KEY"

# This list is added to exclude the info level http logs from FastAPI
EXCLUDED_ENDPOINTS = ["/search", "/doc_search", "/create_collection", "/upsert_vector", "/filter_data",
                      "/delete_vectors", "/health"]
