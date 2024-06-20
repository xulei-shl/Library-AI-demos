from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatZhipuAI
import warnings

warnings.filterwarnings('ignore')


def classify_problem(user_input, llm_configs):
    # llm_gpt4 = ChatOpenAI(**llm_configs["gpt4"])
    # llm_lingyi = ChatOpenAI(**llm_configs["lingyi"])
    # llm_glm = ChatZhipuAI(**llm_configs["glm"])
    llm_gpt4 = ChatOpenAI(
        model=llm_configs["gpt4"].get("model_name", "default-model"),
        temperature=llm_configs["gpt4"].get("temperature", 0),
        api_key=llm_configs["gpt4"].get("api_key"),
        base_url=llm_configs["gpt4"].get("api_base")
    )
    llm_lingyi = ChatOpenAI(
        model=llm_configs["lingyi"].get("model_name", "default-model"),
        temperature=llm_configs["lingyi"].get("temperature", 0),
        api_key=llm_configs["lingyi"].get("api_key"),
        base_url=llm_configs["lingyi"].get("api_base")
    )
    llm_glm = ChatZhipuAI(
        model=llm_configs["glm"].get("model_name", "default-model"),
        temperature=llm_configs["glm"].get("temperature", 0),
        api_key=llm_configs["glm"].get("api_key"),
    )

    classify_ruler = """
        日常业务咨询 - 当有人询问有关图书馆日常业务。包括，图书馆基本信息、读者证、服务政策、服务类型、地址、交通、开放时间等信息时使用。
        
        馆藏图书报刊查询 - 当有人询问有关某本图书、报纸或其他、或关于某个主题的图书、或某个人写的图书馆等馆藏图书信息时使用。关键词：书名、作者、主题。
        
        数据库咨询 - 当有人询问关于数据库的使用方法、特定主题或问题相关的数据库选择、开放获取等信息时使用。关键词：数据库、使用方法、开放获取。
        
        电子书查询 - 当有人询问有关电子书查询、某个主题或问题可以使用哪些电子书等信息时使用。关键词：电子书、主题。
        
        学术文献查询 - 当有人询问有关期刊论文使用、某个主题或问题可以使用哪些期刊论文等信息时使用。或者读者提出的是偏严肃，专业或者学术性的问题。关键词：期刊论文、学术、专业、严肃。
        
        近代文献与古籍文献咨询 - 当有人询问有关近代文献、古籍文献使用、某个主题或问题可以使用哪些近代文献、古籍文献等信息时使用。关键词：近代文献、古籍文献。
        
        展览讲座咨询 - 当有人询问有关图书馆展览讲座的信息时使用。关键词：展览、讲座。
        
        专业服务咨询 - 当有人询问文献传递、原书外借、资料查证、收录引证、检索咨询、翻译服务、科技查新、情报定制等图情业务的服务时使用。关键词：文献传递、外借、查证、引证、检索、翻译、科技查新、情报定制。
        
        读者投诉 - 当有人抱怨图书馆服务等事情时使用。关键词：抱怨、投诉。
        
        其他 - 当不属于上述任何类别时使用。关键词：其他。
    """

    classify_agent = Agent(
        role='图书馆参考咨询专家助理',
        goal=f"""将用户咨询的问题，分为以下类别之一：
            {classify_ruler}""",
        backstory="""
            作为一名引以为豪的图书馆参考咨询专家，你是图书馆咨询团队的成员，并与其他参考咨询专家一同工作。你的主要任务是能够有效地从用户的查询中识别出关键问题与读者的真实意图，并将其地归类，从而确保项目能够在坚实的基础上展开。""",
        verbose=True,
        allow_delegation=False,
        #llm=llm_lingyi,
        llm=llm_glm,
    )

    classify_reviewer_agent = Agent(
        role='图书馆参考咨询高级专家',
        goal=f"""为'图书馆参考咨询专家助理'的读者问题分类进行审核，确保其对用户的分类是精准无误。如果有任何分类错误请提供你的分类意见，并根据如下规则重新分类：
            {classify_ruler} 
        """,
        backstory="""
            你有超过十年的图书馆参考咨询经验，并与图书馆咨询团队中的其他专家们一起工作。你的目标是确保“图书馆参考咨询高级专家”的用户分类精准无误。""",
        verbose=True,
        allow_delegation=False,
        llm=llm_gpt4,
        #llm=llm_lingyi,
    )

    classify_task = Task(
        description=f"""对读者的问题进行深入分析，并将其为合适的类别.  
        读者提交内容:\n\n {user_input}""",
        expected_output="""将读者问题分到如下类别中一个 ('日常业务咨询', '馆藏图书报刊查询', '数据库咨询', '电子书查询', '学术文献查询', '近代文献与古籍文献咨询', '展览讲座咨询', '专业服务咨询', '读者投诉', '其他') \
        eg:
        '馆藏图书报刊查询' \
        请不要给出任何多余的说明与解释，只要给出一个分类结果。
        """,
        agent=classify_agent
    )

    classify_reviewer_task = Task(
        description=f"""对'图书馆参考咨询高级专家'的分类进行检查，确保其对用户提交问题的分类是精准无误的。
        首先，你需要对'图书馆参考咨询高级专家'的分类提出质疑；
        然后，为了确保分类精准无误，考虑给出1-2其他候选分类，并且每个分类给出理由；
        如果归类为“馆藏图书报刊查询”、“电子书查询”、“学术文献查询”三个分类的任一个，你需要确认是否可以从读者提问中明确提到了“题名”、“作者”或“主题”信息，否则不要归类为这三个；
        最后，对这几个分类评估，并选出最符合的一个类别。

        读者提交内容:\n\n {user_input} \n\n
        """,
        expected_output="""将读者问题分到如下类别中一个 ('日常业务咨询', '馆藏图书报刊查询', '数据库咨询', '电子书查询', '学术文献查询', '展览讲座咨询', '专业服务咨询', '读者投诉', '其他') \
        eg:
        '日常业务咨询' \
        """,
        agent=classify_reviewer_agent
    )

    # Instantiate your crew with a sequential process
    crew = Crew(
        agents=[classify_agent, classify_reviewer_agent],
        tasks=[classify_task, classify_reviewer_task],
        verbose=2,
    )

    # Kick off the crew's work
    results = crew.kickoff()

    #final_result = results[-1]
    return results
