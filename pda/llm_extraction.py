# v0.2 将 query 原文拼接在最终输出结果中

from langchain_community.chat_models import ChatZhipuAI
from logs import setup_logger
import ast
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)

def extract_bookinfo(query, file_name, llm_config, logger):
    query = query.replace("'", "’")

    logger.info(f"开始LLM提取,原始输入: {query}")

    llm = ChatZhipuAI(
        model_name=llm_config.get("model_name", "default-model"),
        temperature=llm_config.get("temperature", 0),
        api_key=llm_config.get("api_key"),
    )

    examples = [
        {
            "input":"希望图书馆能不能多采购或者收录台版 日版的漫画和轻小说 现在图书馆的轻小说和漫画数量非常少 如彻夜之歌 中二病也要谈恋爱 阿尼呀等等。范闲，邮箱, woshi，提交时间：2023年3月1日",
            "output": "{'name': '范闲', 'phone': None, 'email': None, 'submission_time': '2023-3-1', 'books': [{'title': '彻夜之歌', 'author': None, 'ISBN': None, 'publisher': None, 'publication_time': None, 'edition': None}, {'title': '中二病也要谈恋爱', 'author': None, 'ISBN': None, 'publisher': None, 'publication_time': None, 'edition': None}, {'title': '阿尼呀', 'author': None, 'ISBN': None, 'publisher': None, 'publication_time': None, 'edition': None}]}"
         },
        {
            "input": "流水编号 202442722138128 录入时间 2024-05-1108:08:02 受理日期 2024-05-11 投诉人 姓名：黄先生、电话：19100000035(/) 投诉渠道 12345 涉及城市 中国/上海/上海中国/上海/上海 图书借阅市民建议：粤语教程及广府文化图书的种类稀少，对读者构成明显不便。建议补充：一、《实用粤语播音主持 语言基础教程（第2版）》(9787504385581)二、《新时空粤语上册》(9787566811585)三、轻松说粤语(978-7- 5100-8765-3)四、“偷听广州”：实用粤语口语(9787519207717)五、事实与理由 《大话广府下册》(9787218152899)。",
            "output": "{'name': '黄先生', 'phone': '19100000035', 'email': None, 'submission_time': '2024-05-11', 'books': [{'title': '实用粤语播音主持 语言基础教程（第2版）', 'author': None, 'ISBN': '9787504385581', 'publisher': None, 'publication_time': None, 'edition': '第2版'}, {'title': '新时空粤语上册', 'author': None, 'ISBN': '9787566811585', 'publisher': None, 'publication_time': None, 'edition': None}, {'title': '轻松说粤语', 'author': None, 'ISBN': '978-7-5100-8765-3', 'publisher': None, 'publication_time': None, 'edition': None}, {'title': '“偷听广州”：实用粤语口语', 'author': None, 'ISBN': '9787519207717', 'publisher': None, 'publication_time': None, 'edition': None}, {'title': '大话广府下册', 'author': None, 'ISBN': '9787218152899', 'publisher': None, 'publication_time': None, 'edition': None}]}"
        },
        {
            "input":"ome ind 上海图书馆外文图书征订读者推荐登记表 F 2023年12月13日 独立学者 职务 读者姓名 刘先光 学历 职称 单位名称 单位地址 单位邮编 电话或手机 13000000988 E-mail 单位经济类型□公有经济□私营经济□外商投资经济 □其它 学科研究领域□社会科学□自然科学□生物、医药 □农业 □工业技术 □其它 推荐征订的外文图书: 书名 illiberal America: A HISTORY 版次 著者 steves Hahn 出版社 Wiw. Norton ISBN 出版年 Officially March 19 2024 信息来源 pablisher’s Webpage",
            "output": "{'name': '刘先光', 'phone': '13000000988', 'email': None, 'submission_time': '2023-12-13', 'books': [{'title': 'illiberal America: A HISTORY', 'author': 'steves Hahn', 'ISBN': None, 'publisher': 'Wiw. Norton', 'publication_time': 'March 19 2024', 'edition': None}]}"         
        },
        {
            "input":"""## 提交信息
            提交时间 = 2024-03-30 00:00:00
            读者信息 = 读者姓名：丁某翼(女),联系电话：13600000028，xianfan@163.com

            ## 咨询内容
            读者3/29反映问题：读者为《绑架 = Kidnap》（ISBN：978-7-5321-8833-8，索书号：I247.7/1261-8，作者丁某翼）一书的作者本人，反映她的该本作品在馆藏书目查询系统中“多了一个英文译名”，且没有图书封面，和她的另一本著作《小灰》（索书号：I247.7/1261-7）在系统中不太一样。读者需要回电答复 今天读者又来电希望尽快添加封面，提议可在豆瓣网找到封面图片，望尽快处理答复。""",
            "output": "{'name': '丁某翼', 'phone': '13600000028', 'email': 'xianfan@163.com', 'submission_time': '2024-03-30', 'books': [{'title': '绑架 = Kidnap', 'author': '丁某翼', 'ISBN': '978-7-5321-8833-8', 'publisher': None, 'publication_time': None, 'edition': None}]}"
         },
    ]

    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{input}"),
            ("ai", "{output}"),
        ]
    )
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=examples,
    )

    system_template = """
        # 角色
        你是一位行业内顶级的信息提取专家。你的主任务是从提交给图书馆的文献采购建议的文本中提取提交者的基本信息和他们推荐的书籍信息。

        # 任务
        请按照如下的规则说明，慢慢来，一步一步分析提取信息。

        ## 技能
        ### 技能 1: 提取提交者信息
        - 从文字中识别并提取出提交者信息：姓名、电话、邮箱、提交时间。

        ### 技能 2: 提取图书信息
        - 从文字中识别并提取出所有图书信息，包括：题名、作者、ISBN、出版社、出版时间、版本。

        ## 输出格式
        - 【重要】严格按照示例输出，其中提交者的基本信息（姓名、电话、邮箱、提交时间）和推荐的书籍列表信息（书名、ISBN、出版社、出版时间、版本）。
        - 一定要注意，提取的邮箱、电话的格式要正确。
        - 【重要】电话是纯数字。如：13600000028。
        - 【重要】邮箱必须有`@`符号。如：ds-52@163.com。

        ## 限制
        - 【重要】若某些信息无法从文本中提取，返回null作为结果。
        - 【重要】只提取要求的字段信息，其他信息不要提取。
        - 【重要】不要进行多余的解释或添加内容。
        """

    final_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_template),
            few_shot_prompt,
            ("human", "{input}"),
        ]
    )

    chain = final_prompt | llm

    llm_output = chain.invoke({"input": query})

    logger.info(f"LLM提取结果: {llm_output.content}")
    print(f"\n-----------------LLM提取结果-----------------------\n")
    #print(llm_output.content)
    #print(llm_output)

    result = f"{{'原件': '{file_name}', '原文': '{query}', {llm_output.content[1:-1]}}}"

    
    print(result)
    return result

#测试    
# if __name__ == "__main__":
    
#     llm_config = {
#         "model_name": "glm-3-turbo",
#         "api_key": "YOUR_API_KEY",
#     }
    
#     query = "流水编号 202442722138128 录入时间 2024-05-1108:08:02 受理日期 2024-05-11 投诉人 姓名：黄先生、电话：19100000035(/) 投诉渠道 12345 涉及城市 中国/上海/上海中国/上海/上海 图书借阅市民建议：粤语教程及广府文化图书的种类稀少，对读者构成明显不便。建议补充：一、《实用粤语播音主持语言基础教程（第2版）》(9787504385581)二、《新时空粤语上册》(9787566811585)。市民未提供具体 地址等相关信息，请管理部门先行联系。诉求：建议采纳。"


#     BASE_PATH = r'C:\Users\Administrator\Desktop\pda\2024-06-04'

#     # 日志文件路径
#     LOG_FOLDER_PATH = r'C:\Users\Administrator\Desktop\pda\logs'
#     logger = setup_logger(LOG_FOLDER_PATH)

#     result = extract_bookinfo(query, llm_config, logger)
