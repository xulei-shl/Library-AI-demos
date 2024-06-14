import pandas as pd
import requests
import json
import time
import random
from openai import OpenAI

# 联网秘塔、 kimi、海螺补充数据库AI介绍

# 读取Excel文件
df = pd.read_excel(r'C:\Users\Administrator\Desktop\database-info.xlsx')

# 初始化OpenAI客户端
openai_client = OpenAI(api_key="sk-", base_url="/v1")

# 创建新列
df['AI介绍'] = ''

# 遍历每一行
for index, row in df.iterrows():
    # 获取数据库名称和语种
    database_name = row['数据库名']
    database_lang = row['数据库语种']

    print(f"正在处理数据库: {database_name}")  # 打印当前正在处理的数据库名称

    # 判断语种并拼接字符串
    if database_lang == '中文数据库':
        prompt = f"你是一名图书馆信息素养教育专家。专长是给研究生培训各种学术数据库的使用。现在你需要联网搜索数据库的介绍信息，撰写一篇介绍\"{database_name}\"数据库的短文。内容包括：（1）数据库收录内容，（2）学科覆盖范围的数据库介绍。请勿添加其他信息。"
    elif database_lang == '外文数据库':
        # 翻译数据库名称
        translate_url = "https://api.deeplx.org/translate"
        translate_payload = json.dumps({
            "text": database_name,
            "source_lang": "auto",
            "target_lang": "EN"
        })
        translate_headers = {'Content-Type': 'application/json'}
        translate_response = requests.request("POST", translate_url, headers=translate_headers, data=translate_payload)
        translated_name = json.loads(translate_response.text)['data']  # 使用'data'字段作为翻译后的名称
        prompt = f"You are a library information literacy education specialist. Your specialty is training graduate students in the use of various academic databases. Now you need to network and search for introductory information about databases and write a short essay introducing the '{translated_name}' database. Include (1) the contents of the database, and (2) a description of the database in terms of subject coverage. Please do not add any other information. Please respond in Chinese."
    
    print(prompt)
    print(f"\n--------------------------------------------\n")

    # 调用OpenAI API
    response = openai_client.chat.completions.create(
        model="hailuo",
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content

    print(result)
    print(f"\n--------------------------------------------\n")

    # 保存结果到Excel
    df.at[index, 'AI介绍'] = result

    # 保存Excel文件
    df.to_excel(r'C:\Users\Administrator\Desktop\database-info.xlsx', index=False)

    # 随机间隔1-3秒
    time.sleep(random.uniform(3, 10))

