from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from paper_keywords import get_paper_keywords
from CNKI_spider import PaperCrawler as CNKIPaperCrawler
from google_scholar_spider import PaperCrawler as GooglePaperCrawler


load_dotenv()

def get_paper_lists(user_input, llm_config):
    paper_keywords = "".join(get_paper_keywords(user_input, llm_config))
    #paper_keywords = "图书馆 大模型"
    print(f"\n---------------关键词提取-------------------------\n")
    print(paper_keywords)
    start_year = 2020
    end_year = 2024
    papers_need = 10

    # 先尝试使用 CNKI 爬虫
    cnki_crawler = CNKIPaperCrawler(paper_keywords, start_year, end_year, papers_need)
    print(f"\n---------------知网检索-------------------------\n")
    cnki_results = cnki_crawler.crawl()

    # 如果 CNKI 爬虫没有返回结果,则使用 Google Scholar 爬虫
    if not cnki_results:
        print(f"\n---------------改用Google学术检索-------------------------\n")
        google_crawler = GooglePaperCrawler(paper_keywords, start_year, end_year, papers_need)
        google_results = google_crawler.crawl()
        #print(google_results)
        return google_results
    else:
        #print(cnki_results)
        return cnki_results

def get_paper_recommendations(user_input, llm_config):
    paper_lists = get_paper_lists(user_input, llm_config)

    llm = ChatZhipuAI(
        model=llm_config["glm"].get("model_name", "default-model"),
        temperature=llm_config["glm"].get("temperature", 0),
        api_key=llm_config["glm"].get("api_key"),
    )

    system_template = """
        # 角色
        你是一位博学的图书馆高级参考馆员，你擅长利用检索的参考文献信息，用专业、学术的语言解答用户提出的问题。

        ## 技能
        ### 技能1：参考文献查阅
        - 整合提供的文献资料`{{paper_lists}}`，为用户提供准确、全面的信息。

        ### 技能2：解答专业问题
        - 利用检索的参考文献找到用户提出问题的答案。
        - 使用专业和学术语言来回答提出的问题。

        ### 技能3：提供知识背景
        - 在需要的时候，为用户提供问题背后的知识背景。

        ## 约束条件
        - 只讨论与参考资料查阅、学术问题解答相关的话题。
        - 始终使用学术和专业的语言。
        - 在回答用户问题时，严格按照学术规范来引用参考资料。

    """
    messages = [
    SystemMessage(content=system_template),
    HumanMessage(content="读者提问：" + user_input + "\n\n" + "参考文献列表如下：\n" + "\n" + paper_lists),
]

    #print(f"\n----------------提示词----------------------------\n")
    #print(messages)
    print(f"\n--------------------大模型处理----------------------------\n")
    json_result = llm.invoke(messages)
    parser = StrOutputParser()
    llm_result = parser.invoke(json_result)
    result = f"## 大模型回答：\n\n{llm_result}\n\n## 检索到的相关文献：\n\n{paper_lists}"

    #print(result)
    return result
    
# 测试
# if __name__ == "__main__":

#     llm_config = {
#         "temperature": 0,
#         "model_name": "glm-4-air",
#         "api_key": "your_api_key",
#     }

#     user_input = """中美地缘政治冲突对中国这一波大语言模型的研究与发展有什么影响"""

#     get_paper_recommendations(user_input, llm_config)
        