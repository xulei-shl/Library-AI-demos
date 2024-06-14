from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import FewShotChatMessagePromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from rag.fastgpt import fastgpt_api
import os
from dotenv import load_dotenv

load_dotenv()

# v0.2 首先调用fastgpt_api，如果返回结果中包含"无法回答其他问题。"，则直接调用general_response函数，否则调用llm_lingyi_config函数
#v0.3 fastgpt单独出去进行调用

def complaint_reponse(query, llm_config):
    #llm = ChatOpenAI(**llm_lingyi_config)
    llm = ChatOpenAI(
        model=llm_config.get("model_name", "default-model"),
        temperature=llm_config.get("temperature", 0),
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("api_base")
    )

    system_template = """
    你是一个专业的图书馆读者服务参考咨询专家。请根据用户的投诉问题，以及搜索到的背景资料，按照样例模板，撰写一份专业的回复。请使用 markdown 格式。
    """

    examples = [
        {
            "query": "怎么有些书在官网上可以查到，但书架上找不到？",
            "output": """
                首先，我想对您在上海图书馆遇到的不便表示诚挚的歉意。我们非常重视您的反馈，对您遇到的问题深感遗憾。
                我们已经将此问题详细反馈给负责图书馆日常运营的相关部门，他们正在积极寻找解决方案，并承诺尽快解决这一问题。
                我们承诺将在问题解决后，及时向您反馈处理结果。
                上海图书馆十分重视每一位读者的需求，并会不断优化我们的服务，以满足读者的需求。我们期待您的理解，并希望有机会再次为您服务。如果您有任何疑问或需要进一步的帮助，请随时通过以下方式与我们联系：
                电话：64455555
                """,
        },
    ]    
    
    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{query}"),
            ("ai", "{output}"),
        ]
    )


    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )

    api_endpoint = os.getenv("FASTGPT_general_API_ENDPOINT")
    api_key = os.getenv("FASTGPT_general_API_KEY")
    context = fastgpt_api(query, api_endpoint, api_key)  # 调用fastgpt_api函数

    if context == "" or "无法回答问题" in context:
        messages = ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                few_shot_prompt,
                ("human", "{query}"),
            ]
        )
    else:
        messages = ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                few_shot_prompt,
                MessagesPlaceholder(context),
                ("human", "{query}"),
            ]
        )

    #print(messages)

    chain = messages | llm
    json_result = chain.invoke({"query": query})
    parser = StrOutputParser()
    result = parser.invoke(json_result)
    #print(result)
    return result

# 测试
# if __name__ == "__main__":

#     llm_config = {
#         "temperature": 0,
#         "model_name": "yi-large",
#         "openai_api_base": "https://api.lingyiwanwu.com/v1",
#         "openai_api_key": "your_api_key_here",
#     }

#     query = """在图书馆中看到了几只蟑螂，是不是应该及时处理保持图书馆的整洁？"""
#     complaint_reponse(query, llm_config)