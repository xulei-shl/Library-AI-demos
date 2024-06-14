from rag.fastgpt import fastgpt_api
from rag.coze import coze_api
import os
from dotenv import load_dotenv

load_dotenv()

def fastgpt_database_api(query):
    try:
        api_endpoint = os.getenv("FASTGPT_database_API_ENDPOINT")
        api_key = os.getenv("FASTGPT_database_API_KEY")
        fastgpt_rag_result = fastgpt_api(query, api_endpoint, api_key)
        if "无法回答问题。" not in fastgpt_rag_result:
            return fastgpt_rag_result
    except Exception as e:
        print(f"发生异常: {e}")
    return None

def coze_database_api(query):
    bot_id = os.getenv("COZE_BOT_ID")
    api_key = os.getenv("COZE_API_KEY")
    try:
        coze_result = coze_api(query, bot_id, api_key)
        return coze_result
    except Exception as e:
        print(f"发生异常: {e}")
        return None

def query_database_api(query, llm_config=None):
    fastgpt_result = fastgpt_database_api(query)
    if fastgpt_result:
        #print(f"--------------------------------------------")
        #print("FastGPT返回结果\n\n:", fastgpt_result)
        return "馆所知识库（FastGPT）返回结果:\n\n" + fastgpt_result
    

    coze_result = coze_database_api(query)
    if coze_result:
    #print(f"--------------------------------------------")
    #print("Coze返回结果:\n\n", coze_result)
        return "网络搜索（Coze）返回结果:\n\n" + coze_result

    return "无法从任何数据库获取结果。"

# 测试
# if __name__ == "__main__":
#     query = "18世纪历史学资料可以查询哪些数据库？"
#     print(query_database_api(query))