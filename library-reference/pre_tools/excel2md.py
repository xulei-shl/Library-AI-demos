import pandas as pd

#将excel的数据库文档整理为markdown文档 

# 读取Excel文件
df = pd.read_excel(r'C:\Users\Administrator\Desktop\cankao\基础知识库\database-info-清洗.xlsx')

# 初始化Markdown字符串
markdown_text = ""

# 遍历每一行，将其转换为Markdown格式
for index, row in df.iterrows():
    if index > 0:  # 在每个H2段落前添加分割符，但不在第一个H2段落前添加
        markdown_text += "\n---\n\n"
    # 添加H2标题
    markdown_text += f"## {row['数据库名']}\n\n"
    # 添加H3标题和内容
    for column in df.columns:
        if pd.notna(row[column]) and row[column] != "无":  # 检查单元格是否为空且不等于"无"
            markdown_text += f"### {column}\n\n{row[column]}\n\n"

# 将Markdown文本保存到文件
with open(r'C:\Users\Administrator\Desktop\cankao\基础知识库\output.md', 'w', encoding='utf-8') as file:
    file.write(markdown_text)

print("Markdown文件已生成。")
