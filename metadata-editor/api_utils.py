import os
from dotenv import load_dotenv
import requests
from openai import OpenAI 
import json

# Load environment variables from .env file
load_dotenv()

siliconflow_API_KEY = os.getenv("siliconflow_API_KEY")
siliconflow_BASE_URL = os.getenv("siliconflow_API_URL")
siliconflow_model = "THUDM/glm-4-9b-chat"

Dify_API_KEY = os.getenv("Dify_API_KEY")
Dify_API_URL = os.getenv("Dify_API_URL")

zhipu_API_KEY = os.getenv("zhipu_API_KEY")
zhipu_API_URL = os.getenv("zhipu_API_URL")


def llm_requstion(text, api_key, api_url, model):
    client = OpenAI(
        api_key=api_key,
        base_url=api_url
    ) 
    response = client.chat.completions.create(
        model=model,  
        messages=[{"role": "user", "content": text}],  # Corrected syntax
        top_p=0.7,
        temperature=0.9
    )
    result = response.choices[0].message.content
    print(response.choices[0].message.content)
    return result


def siliconflow_llm_requstion(text):
    payload = {
        "model": siliconflow_model,
        "messages": [{"role": "user", "content": text}],
        "stream": False
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {siliconflow_API_KEY}"
    }

    response = requests.post(siliconflow_BASE_URL, json=payload, headers=headers)
    # response.raise_for_status()
    result = response.json()["choices"][0]["message"]["content"]
    #print(result)
    return result

def dify_request(query, api_key, api_url):
    url = api_url

    headers = {
        "Authorization": f'Bearer {api_key}',
        "Content-Type": "application/json"
    }

    data = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "abc-123"
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = response.json()
        answer = response_json.get('answer', 'No answer found')
        print(answer)
        return answer
    else:
        print(f"Request failed with status code {response.status_code}")
        return None

def dify_new_request(query, dify_api_key):
    url = "https://api.dify.ai/v1/chat-messages"

    headers = {
        "Authorization": f'Bearer {dify_api_key}',
        "Content-Type": "application/json"
    }

    data = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "abc-123"
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = response.json()
        answer = response_json.get('answer', 'No answer found')
        print(answer)
        return answer
    else:
        print(f"Request failed with status code {response.status_code}")
        return None


def get_person_uri(fname, page=1):
    url = os.getenv("SHL_Person_URL")
    key = os.getenv("SHL_Person_API")
    params = {
        "fname": fname,
        "key": key,
        "pageth": page,
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
        print(data)
        if data['result'] == '0' and data['data']:
            return data
        else:
            return None
    else:
        print("Request failed with status code:", response.status_code)
        return None
    
if __name__ == "__main__":
    query = "谁是吴春华"
    #dify_request(query)
    zhipu_llm_requstion(query)