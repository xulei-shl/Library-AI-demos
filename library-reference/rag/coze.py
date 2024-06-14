import requests

def coze_api(query, bot_id, api_key):
    url = 'https://api.coze.com/open_api/v2/chat'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'api.coze.com',
        'Connection': 'keep-alive'
    }
    data = {
        "conversation_id": "123",
        "bot_id": bot_id,
        "user": "123333333",
        "query": query,
        "stream": False
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            content_json = response.json()
            try:
                return content_json['messages'][0]['content']
            except (KeyError, IndexError):
                return None
        else:
            print("Coze API 调用失败")
            return None
    except Exception as e:
        print(f"发生异常: {e}")
        return None
