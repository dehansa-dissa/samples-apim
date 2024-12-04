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
import requests
import urllib3

# Suppress SSL certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Create new API in Publisher portal by sending generated payload
def publish_api(answer_text, token):
    endpoint_url = "https://localhost:9443/api/am/publisher/v4/apis"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(endpoint_url, headers=headers, data=answer_text, verify=False)
        response.raise_for_status()
        print("Payload successfully sent to the API endpoint.")
        return {"message": "API created successfully"}
    
    except requests.exceptions.RequestException as e:
        print(f"Failed to send payload: {e}")
        return {"error": "Failed to create API"}