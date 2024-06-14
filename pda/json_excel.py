import pandas as pd
import re
import ast
from datetime import date
from logs import setup_logger
import os
import json

# v0.3 出现任何错误，返回原文，其他字段为空

def clean_query(query):
    # 将双引号改为单引号
    query = query.replace('"', "'")
    
    # 删除换行符
    query = query.replace('\n', ' ')
    
    # 将多余的空白字符替换为单个空格
    query = re.sub(r'\s+', ' ', query)
    
    # 确保冒号和逗号后面只有一个空格
    query = re.sub(r'(?<=:)\s*', ' ', query)
    query = re.sub(r'(?<=,)\s*', ' ', query)
    
    # 去除冒号和逗号之前的空格
    query = re.sub(r'\s+(?=:)', '', query)
    query = re.sub(r'\s+(?=,)', '', query)

    if query.count('[') > query.count(']'):
        query += ']'

    if query.count('{') > query.count('}'):
            query += '}'        
    
    return query
    

def parse_querying(query):
    try:
        # 使用 ast.literal_eval 解析 JSON 字符串
        query_dict = ast.literal_eval(query)
    except (ValueError, SyntaxError):
        # 解析失败时，清洗 query 并重试
        query = clean_query(query)
        query_dict = ast.literal_eval(query)

    # 提取字段值
    originalFile = query_dict.get('原件')
    originalText = query_dict.get('原文')
    name = query_dict.get('name')
    phone = query_dict.get('phone')
    email = query_dict.get('email')
    submission_time = query_dict.get('submission_time')
    books = query_dict.get('books', [])

    return {
        '原件': originalFile,
        '原文': originalText,
        'name': name,
        'phone': phone,
        'email': email,
        'submission_time': submission_time,
        'books': books
    }

def save_to_excel(query, BASE_PATH, logger):
    # 清洗 query
    query = clean_query(query)

    try:
        query_dict = parse_querying(query)
    except:
        # 如果解析失败,只保留原文和原件
        query_dict = {'原件': '', '原文': query}

    logger.info(f"处理Excel文件: {query_dict}")
    print(f"\n-----------------parse_querying返回的字典结构-----------------------\n")
    print(query_dict)

    try:
        # 创建空列表用于存储每一行的数据
        data = []

        # 如果只有 '原文' 和 '原件' 两个键,则创建一行数据
        if set(query_dict.keys()) == {'原文', '原件'}:
            row = [
                query_dict.get('原件', ''),
                query_dict.get('原文', ''),
                '',  # ISBN
                '',  # 题名
                '',  # 作者
                '',  # 版本
                '',  # 出版社
                '',  # 出版年
                '',  # 姓名
                '',  # Email
                '',  # 电话
                '',  # 提交日期
                ''   # 错误信息
            ]
            data.append(row)

        # 遍历 books 列表,为每一本书创建一行数据
        for book in query_dict.get('books', []):
            row = [
                query_dict.get('原件', ''),
                query_dict.get('原文', ''),
                book.get('ISBN', ''),
                book.get('title', ''),
                book.get('author', ''),
                book.get('edition', ''),
                book.get('publisher', ''),
                book.get('publication_time', ''),
                query_dict.get('name', ''),
                query_dict.get('email', ''),
                query_dict.get('phone', ''),
                query_dict.get('submission_time', ''),
                ''
            ]
            data.append(row)

        # 创建 DataFrame
        columns = ['原件', '原文', 'ISBN', '题名', '作者', '版本', '出版社', '出版年', '姓名', 'Email', '电话', '提交日期', '错误信息']
        df = pd.DataFrame(data, columns=columns)

        # 获取当天日期
        today = date.today().strftime("%Y%m%d")
        file_name = f"{today}_output.xlsx"
        output_dir = os.path.join(BASE_PATH, 'output')
        # 检查目录是否存在，如果不存在则创建
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        file_path = os.path.join(output_dir, file_name)

        # 检查文件是否存在
        if os.path.exists(file_path):
            existing_df = pd.read_excel(file_path)
            df = pd.concat([existing_df, df], ignore_index=True)
            logger.info(f"向现有文件追加数据: {file_path}")
            print(f"\n-----------------向现有文件追加数据-------------------------\n")
            print(file_path)
        else:
            logger.info(f"创建 Excel 文件: {file_path}")
            print(f"\n-----------------创建 Excel 文件-------------------------\n")
            print(file_path)

        # 将 DataFrame 写入 Excel 文件
        df.to_excel(file_path, index=False)
        logger.info(f"保存成功： {file_path}")
        print(f"\n-----------------保存成功-------------------------\n")
        print(file_path)

    except Exception as e:
        logger.error(f"错误信息: {str(e)}")
        print(f"\n-----------------错误信息-------------------------\n")
        print(str(e))
        # 返回固定数据结构
        return {
            '原件': query_dict.get('原件', None),
            '原文': query_dict.get('原文', None),
            '错误信息': '大模型API调用错误',
            'name': None,
            'phone': None,
            'email': None,
            'submission_time': None,
            'books': []
        }

# 测试
# if __name__ == "__main__":

#     queries = [
#         """{'原件': '微信图片_202406111555251.jpg', '原文': '% A ome nd 上海图书馆外文图书征订读者推荐登记表 F 年月日 职称 职务 读者姓名 JUV 学历 单位 名称 indopesdent researcher 单位地址 JL4617@columbia.edy 单位邮编 电话或手机 13900000088 E-mail 单位经济类型□公有经济□私营经济□外商投资经济□其它 学科研究领域□社会科学 □自然科学 □生物、医药 □农业 □工业技术 □其它 推荐征订的外文图书: 书名 Christendom: The Triumph of a Ralgqios, AD 300-1300 版次 著者 Peter Heather 出版社 Knopf ISBN 978-0431494306 出版年 Aeril 2023 信息来源 publishers uabpage', 'name': 'JUV', 'phone': '13900000088', 'email': 'JL4617@columbia.edu', 'submission_time': None, 'books': [{'title': 'Christendom: The Triumph of a Ralgqios, AD 300-1300', 'author': 'Peter Heather', 'ISBN': '978-0431494306', 'publisher': 'Knopf', 'publication_time': 'Aeril 2023', 'edition': None}]}"""
#         ]

#     BASE_PATH = r'C:\Users\Administrator\Desktop\pda\2024-06-04'

#     # 日志文件路径
#     LOG_FOLDER_PATH = r'C:\Users\Administrator\Desktop\pda\logs'
#     logger = setup_logger(LOG_FOLDER_PATH)

#     for query in queries:
#         save_to_excel(query, BASE_PATH, logger)