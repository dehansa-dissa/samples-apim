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