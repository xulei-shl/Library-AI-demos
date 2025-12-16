import requests
import sys

def call_api(endpoint, payload):
    url = f"http://localhost:8000/api/books/{endpoint}"
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        # 根据 API 定义，优先返回 plain_text 供 LLM 直接读取
        return data.get("context_plain_text") or data
    except Exception as e:
        return f"API Error: {str(e)}"

if __name__ == "__main__":
    mode = sys.argv[1]
    input_text = sys.argv[2]

    if mode == "simple":
        # 调用文本相似度检索
        print(call_api("text-search", {"query": input_text, "response_format": "plain_text"}))
    elif mode == "deep":
        # 调用多子查询检索（接收 Markdown）
        print(call_api("multi-query", {"markdown_text": input_text, "response_format": "plain_text"}))