import requests
import urllib3

# Suppress SSL certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# create new API on portal
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
        return {"error": f"Failed to create API: {e}"}

# modify API in portal with payload  # 2b62c7cc-0fa3-48c6-8ff8-ff9b2ef4cc3d
def modify_api(api_id, answer_text, token):
    print(f"Modifying API with ID: {api_id}")
    endpoint_url = f"https://127.0.0.1:9443/api/am/publisher/v4/apis/{api_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        put_response = requests.put(endpoint_url, headers=headers, data=answer_text, verify=False)
        put_response.raise_for_status()
        print(f"API with ID {api_id} successfully updated.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to update API with ID {api_id}: {e}")



# retrieve api.yaml file of API in portal  # 2b62c7cc-0fa3-48c6-8ff8-ff9b2ef4cc3d
def fetch_api_details(api_id, token):
    print(f"Retrieving API with ID: {api_id}")
    endpoint_url = f"https://127.0.0.1:9443/api/am/publisher/v4/apis/{api_id}"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    try:
        response = requests.get(endpoint_url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch API details: {e}")
        return None

