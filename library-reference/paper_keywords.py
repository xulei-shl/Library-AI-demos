from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatZhipuAI
import warnings

warnings.filterwarnings('ignore')


def get_paper_keywords(user_input, llm_config):
    llm_lingyi = ChatOpenAI(
        model=llm_config["lingyi"].get("model_name", "default-model"),
        temperature=llm_config["lingyi"].get("temperature", 0),
        api_key=llm_config["lingyi"].get("api_key"),
        base_url=llm_config["lingyi"].get("api_base")
    )
    llm_glm = ChatZhipuAI(
        model=llm_config["glm"].get("model_name", "default-model"),
        temperature=llm_config["glm"].get("temperature", 0),
        api_key=llm_config["glm"].get("api_key"),
    )

    keyword_extractor_agent = Agent(
        role='你是一个文本分析助手，专门帮助用户从输入的文本中提取适用于Google学术检索的主题词。',
        goal=f"""从用户输入的文本中提取出最符合其搜索动机和需求的主题词，帮助用户更高效地进行学术检索。""",
        backstory="""
            用户希望通过输入的文本获取适用于Google学术检索的主题词，以便更精准地找到相关的学术资源。你的任务是理解用户的搜索动机，并从文本中抽取最多2个符合用户需求的主题词。""",
        verbose=True,
        allow_delegation=False,
        llm=llm_glm,
    )

    keyword_reviewer_agent = Agent(
        role='你是一个文本分析和优化助手，专门帮助用户审核和优化从输入文本中提取的适用于Google学术检索的主题词。',
        goal=f"""审核 `academic_keyword_extractor` 提供的关键词列表，并根据用户的搜索动机和需求，优化并提供更加合理的关键词。
        """,
        backstory="""
            用户希望通过输入的文本获取适用于Google学术检索的主题词，以便更精准地找到相关的学术资源。你需要审核`academic_keyword_extractor` 提供的关键词列表，并根据用户的搜索动机和需求，优化这些关键词。""",
        verbose=True,
        allow_delegation=False,
        llm=llm_lingyi,
    )

    keyword_extractor_task = Task(
        description=f"""
        1. 理解用户输入的文本，分析其搜索动机。
        2. 【重要】从文本中抽取出最符合用户需求的主题词。
        3. 确保主题词建议符合用户的描述和需求。
        4. 【重要】不对用户的输入进行任何解释或回复，直接给出主题词。
        5. 【重要】主题词建议最多2个，每个关键词之间用空格隔开。
        6. 【重要】关键词应尽量原子化，避免过于复杂或冗长。

        ---

        读者提交内容:\n\n {user_input}
        """,
        expected_output="""输出一个包含主题词的列表，每个关键词之间用空格隔开。\
        eg:
        用户输入：“我想了解关于机器学习在医学影像分析中的应用。”
        期望输出：机器学习 医学影像 \
        请不要给出任何多余的说明与解释，只要给出推荐的主题词。
        """,
        agent=keyword_extractor_agent
    )

    keyword_reviewer_task = Task(
        description=f"""
        1. 审核 `academic_keyword_extractor` 提供的关键词列表，确保其符合用户的搜索动机和需求。
        2. 在理解用户需求的基础上，对提供的主题词进行评估，并质疑其是否符合用户的搜索动机和需求。
        3. 在质疑的基础上，给出优化建议。
        4. 最后，提供优化后的主题词建议。

        ---

        读者提交内容:\n\n {user_input} \n\n
        """,
        expected_output="""
        1. 【重要】不对用户的输入进行任何解释或回复，直接给出优化后的关键词。\
        2. 【重要】关键词应尽量原子化，避免过于复杂或冗长。 \
        3. 【重要】关键词建议最多2个，每个关键词之间用空格隔开。\
        eg:
        用户输入：“我想了解关于机器学习在医学影像分析中的应用。” \
        `academic_keyword_extractor`的关键词列表：机器学习 医学影像分析 应用 \
        期望输出：机器学习 医学影像 \
        """,
        agent=keyword_reviewer_agent
    )

    # Instantiate your crew with a sequential process
    crew = Crew(
        agents=[keyword_extractor_agent, keyword_reviewer_agent],
        tasks=[keyword_extractor_task, keyword_reviewer_task],
        verbose=2,
    )

    # Kick off the crew's work
    results = crew.kickoff()

    #final_result = results[-1]
    return results

#测试
# if __name__ == "__main__":
#     user_input = '''有没有“大模型对图书馆业务可能的影响”相关资料'''
#     llm_config = {
#         "lingyi": {
#             "model_name": "yi-large",
#             "temperature": 0,
#             "api_key": "your_lingyi_api_key",
#             "api_base": "https://api.lingyiwanwu.com/v1",
#         },
#         "glm": {
#             "model_name": "glm-4-air",
#             "temperature": 0,
#             "api_key": "your_glm_api_key",
#         },
#     }
#     results = get_paper_keywords(user_input, llm_config)
#     print(f"Results: {results}")