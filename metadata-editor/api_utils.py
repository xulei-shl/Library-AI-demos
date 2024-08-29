import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("siliconflow_API_KEY")
BASE_URL = os.getenv("siliconflow_API_URL")
model = "THUDM/glm-4-9b-chat"

def call_api(text):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": text}],
        "stream": False
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {API_KEY}"
    }

    response = requests.post(BASE_URL, json=payload, headers=headers)
    # response.raise_for_status()
    result = response.json()["choices"][0]["message"]["content"]
    print(result)
    return result
def get_person_uri(fname):
    url = os.getenv("SHL_Person_API")
    key = os.getenv("SHL_Person_URL")
    params = {
        "fname": fname,
        "key": key,
        "pageth": 1,
        "pageSize": 10
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    auth = ("username", "password")  # 替换为实际的身份验证信息

    response = requests.get(url, params=params, headers=headers, auth=auth)

    if response.status_code == 200:
        data = response.json()
        if data['result'] == '0' and data['data']:
            return data['data'][0]['uri']
        else:
            return None
    else:
        print("Request failed with status code:", response.status_code)
        return None