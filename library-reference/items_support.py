import warnings
import re
import psycopg2
import requests
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core._api.beta_decorator import LangChainBetaWarning
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# 忽略LangChainBetaWarning
warnings.filterwarnings(action="ignore", category=LangChainBetaWarning)

# Database connection details
DB_CONFIG = {
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

def sql_results_to_markdown(results):
    """Converts the SQL query results to a Markdown table format."""
    headers = ["题名", "索书号", "条码", "复本号", "借阅类型", "馆藏状态", "HORIZON馆藏地", "HORIZON馆别"]
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    
    for row in results:
        markdown += "| " + " | ".join(row) + " |\n"
    
    return markdown

def google_json_to_markdown(books):
    """Converts the book information to a Markdown list format."""
    markdown = ""
    for book in books:
        markdown += f"- **Title**: {book['title']}\n"
        markdown += f"  - **Author**: {book['author']}\n"
        markdown += f"  - **ISBN**: {book['identifier-isbn']}\n"
        markdown += f"  - **Publisher**: {book['publisher']}\n"
        markdown += f"  - **Published Date**: {book['publishedDate']}\n"
        markdown += f"  - **Description**: {book['description']}\n\n"
    return markdown

def title_folio_sql_search(title):
    conn = psycopg2.connect(**DB_CONFIG)
    with conn:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                bd.jsonb ->> 'title' AS 题名,
                bd.jsonb ->> 'callNumber' AS 索书号,
                bd.jsonb ->> 'barcode' AS 条码,
                bd.jsonb ->> 'accessionNumber' AS 复本号,
                bt.jsonb ->> 'name' AS 借阅类型,
                hi.jsonb ->> 'name' AS 馆藏状态,
                bd.jsonb ->> 'location' AS HORIZON馆藏地,
                bd.jsonb ->> 'collection' AS HORIZON馆别
            FROM
                shlibrary_mod_shl_inventory.bookduplicate bd
                LEFT JOIN shlibrary_mod_shl_inventory.borrowtype bt ON bd.jsonb ->> 'permanentLoanType' = bt.id::text
                LEFT JOIN shlibrary_mod_shl_inventory.holdingidentifierstate hi ON bd.jsonb ->> 'itemStatus' = hi.id::text
            WHERE
                LOWER(f_unaccent(bd.JSONB ->> 'title')) LIKE LOWER(f_unaccent(%s))
                AND bd.JSONB ->> 'deleted' = 'false'
            LIMIT 20
            """
            title_param = '%' + title + '%'
            cursor.execute(sql, (title_param,))
            results = cursor.fetchall()
    return sql_results_to_markdown(results)

def google_book_api(title=None, author=None):
    query = ""
    if title:
        query += f"intitle:{title}"
    if author:
        if query:
            query += "+"
        query += f"inauthor:{author}"

    response = requests.get(f"https://www.googleapis.com/books/v1/volumes?q={query}").json()

    books = []
    for item in response.get('items', [])[:10]:
        volume_info = item.get('volumeInfo', {})
        industry_identifiers = volume_info.get('industryIdentifiers', [])
        
        # 提取 ISBN
        isbn_list = [identifier.get('identifier') for identifier in industry_identifiers if identifier.get('type').startswith('ISBN')]
        
        book_info = {
            'title': volume_info.get('title'),
            'author': ', '.join(volume_info.get('authors', [])),
            'identifier-isbn': ', '.join(isbn_list),
            'publisher': volume_info.get('publisher', 'N/A'),
            'publishedDate': volume_info.get('publishedDate', 'N/A'),
            'description': volume_info.get('description', 'N/A')
        }
        books.append(book_info)
    
    return google_json_to_markdown(books)

def hailuo_web_search(query):

    # 从 .env 文件中读取配置信息
    api_key = os.getenv("HAILUO_API_KEY")
    base_url = os.getenv("HAILUO_BASE_URL")

    llm = ChatOpenAI(
        model_name="hailuo",
        api_key=api_key,
        base_url=base_url,
    )

    messages = [
        SystemMessage(content="""
            # Character
            你是一名全国阅读推广大使，具有丰富的阅读指导和书目推荐经验。

            ## Skills
            ### 技能1：推荐阅读书目
            - 确定用户的阅读偏好
            - 如果提到了未知的书籍，搜索以确定其类型
            - 从用户的偏好中，推荐10本左右适合阅读的书籍。格式参考：
            =====
            - 📚 书名：<书名>
            - 💡 简介：＜100字以内的简介＞
            ====="""),
        HumanMessage(content = query),
    ]
    json_result = llm.invoke(messages)
    parser = StrOutputParser()
    result = parser.invoke(json_result)
    #print("LLM返回结果：\n\n", result)
    return "大模型直接返回结果:\n\n" + result

def classify_search(failed_generation):
    title_match = re.search(r"'title'='(.*?)'", failed_generation)
    author_match = re.search(r"'author'='(.*?)'", failed_generation)

    title = title_match.group(1) if title_match else ""
    author = author_match.group(1) if author_match else ""

    if title and author:
        return google_book_api(title=title, author=author)
    elif title:
        return google_book_api(title=title)
    else:
        return google_book_api(author=author)

def extract_bookinfo(query, llm_config):
    llm = ChatGroq(
        model_name=llm_config.get("model_name", "default-model"),
        temperature=llm_config.get("temperature", 0),
        groq_api_key=llm_config.get("api_key"),
    )

    class BookInfo(BaseModel):
        """Information about a book."""
        title: Optional[str] = Field(default=None, description="The title of the book.")
        author: Optional[str] = Field(default=None, description="The author of the book.")

    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专家提取算法。仅从文本中提取有关图书报刊的相关作者或题名信息。如果您不知道要求提取的属性的值，请为该属性的值返回null。如果文本中没有对应信息，严禁自行添加。请只返回提取的信息，不要添加任何额外信息。"),
        MessagesPlaceholder("examples"),
        ("human", "{text}"),
    ])

    # Define examples
    examples = [
        ("human", "请帮我最近几年陈亮的书籍"),
        ("ai", "book=['title'='', 'author'='陈亮']"),
        ("human", "请问有三体？"),
        ("ai", "book=['title'='三体', 'author'='']"),
        ("human", "请问有王力的数据可视化？"),
        ("ai", "book=['title'='数据可视化', 'author'='王力']"),
        ("human", "有没有数字化转型的书？"),
        ("ai", "book=['title'='数字化转型', 'author'='']"),    
    ]

    structured_llm = prompt | llm.with_structured_output(BookInfo)
    try:
        result = structured_llm.invoke({
            "examples": examples,
            "text": query
        })
        
        title = result.title or ""
        author = result.author or ""
        
        return classify_search(title, author)
    
    except Exception as e:
        error_message = str(e)
        match = re.search(r"'failed_generation': \"(.*?)\"", error_message)
        if match:
            failed_generation = match.group(1)
            print(f"--------------------------------------------")
            print("Grop提取结果:", failed_generation)
            return classify_search(failed_generation)
        else:
            print("无法提取到作者和题名信息。")
            return hailuo_web_search(query)

# 测试代码
# if __name__ == "__main__":
#     query = "我想找关于死亡或者哀伤的儿童绘本"

#     llm_config = {
#         "model_name": "Mixtral-8x7b-32768",
#         "api_key": "your-api-key",
#     }
#     result = extract_bookinfo(query, llm_config)

#     print(result)