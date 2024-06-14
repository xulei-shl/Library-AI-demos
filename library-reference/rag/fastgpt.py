import requests

def fastgpt_api(query, api_endpoint, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "stream": False,
        "detail": False,
        "messages": [
            {
                "content": query,
                "role": "user"
            }
        ]
    }
    response = requests.post(api_endpoint, headers=headers, json=data)

    if response.status_code == 200:
        fastgpt_rag_result = response.json()["choices"][0]["message"]["content"]
        return fastgpt_rag_result
    else:
        print("FastGPT API 调用失败")
        return ""