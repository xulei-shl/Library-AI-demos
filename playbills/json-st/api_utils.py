import requests

API_KEY = "sk-tlshpwtcuxxqqcuuauiahlmfhfwfyncyyxvlkgbqpypaehfb"
BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
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
    url = "http://data1.library.sh.cn/persons/data"
    params = {
        "fname": fname,
        "key": "b0ba31b119f11c9d2bbe045d1cca4f3844d19f82",
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