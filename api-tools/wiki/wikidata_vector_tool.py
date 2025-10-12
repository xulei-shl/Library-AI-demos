import requests
import json
import urllib.parse

def query_wikidata_vector_db(query_text, lang="en", k=10, rerank=False, return_vectors=False, api_secret=None):
    """
    查询Wikidata向量数据库
    
    参数:
        query_text (str): 查询字符串
        lang (str): 查询语言，默认为"en"
        k (int): 返回结果数量，默认为10
        rerank (bool): 是否重新排序结果，默认为False
        return_vectors (bool): 是否返回向量嵌入，默认为False
        api_secret (str): API密钥，默认为None
    
    返回:
        dict: API响应的JSON数据
    """
    # API端点
    url = "https://wd-vectordb.wmcloud.org/item/query/"
    
    # 请求头 - 添加更具描述性的User-Agent
    headers = {
        "accept": "application/json",
        "User-Agent": "Library-AI-demos/1.0 (Wikidata Vector DB Client; +https://github.com/yourusername/Library-AI-demos)"
    }
    
    # 如果提供了API密钥，添加到请求头
    if api_secret:
        headers["x-api-secret"] = api_secret
    
    # 查询参数
    params = {
        "query": query_text,
        "lang": lang,
        "K": k,
        "rerank": str(rerank).lower(),
        "return_vectors": str(return_vectors).lower()
    }
    
    try:
        # 发送GET请求
        response = requests.get(url, headers=headers, params=params)
        
        # 打印请求URL以便调试
        print(f"请求URL: {response.url}")
        
        # 检查响应状态码
        response.raise_for_status()
        
        # 返回JSON响应
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        # 尝试打印响应内容以获取更多信息
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应内容: {e.response.text}")
        return None

# 示例使用
if __name__ == "__main__":
    # 查询"人工智能"
    result = query_wikidata_vector_db("人工智能")
    
    if result:
        # 打印结果
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("查询失败")