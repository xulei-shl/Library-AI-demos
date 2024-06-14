from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from rag.fastgpt import fastgpt_api  # 导入fastgpt_api函数
import os
from dotenv import load_dotenv

load_dotenv()

#v0.3 fastgpt单独出去进行调用

def general_response(query, llm_config):
    llm = ChatOpenAI(
        model=llm_config.get("model_name", "default-model"),
        temperature=llm_config.get("temperature", 0),
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("api_base")
    )

    system_template = """
        # 角色
        你是一个专业的图书馆读者服务参考咨询专家，擅长根据用户的问题和调查进行具有质量的回复。

        ## 技能
        ### 技能1： 用户投诉处理
        - 识别用户的投诉内容
        - 根据故障和用户的痛点进行个性化的回复

        ### 技能3： 专业回复
        - 使用markdown格式完成回复
        - 回复中包含问题的核心以及常见的解决方法
        - 回复覆盖所有投诉的层级和细节

        ## 约束：
        - 仅讨论与用户投诉问题有关的主题
        - 坚持使用markdown 格式进行回答
        - 确保回复全面、专业而且个性化
    """

    messages = [
        SystemMessage(content=system_template),
        HumanMessage(content="读者提问：" + query),
    ]

    api_endpoint = os.getenv("FASTGPT_general_API_ENDPOINT")
    api_key = os.getenv("FASTGPT_general_API_KEY")
    context = fastgpt_api(query, api_endpoint, api_key)  # 调用fastgpt_api函数

    if context == "" or "无法回答问题" in context:
        json_result = llm.invoke(messages)
        parser = StrOutputParser()
        result = parser.invoke(json_result)
        print("LLM返回结果：", result)
        return "大模型直接返回结果:\n\n" + result
    else:
        return "馆所知识库（FastGPT）返回结果:\n\n" + context
    
# 测试
# if __name__ == "__main__":

#     llm_config = {
#         "temperature": 0,
#         "model_name": "yi-large",
#         "api_base": "https://api.lingyiwanwu.com/v1",
#         "api_key": "your_api_key",
#     }

#     query = """读者证一共有几种？具体有什么区别？"""
#     general_response(query, llm_config)
        