import pandas as pd
import os
import json
from datetime import datetime
import re
import hashlib

def hash_card_number(card_number):
    """生成脱敏后的卡号"""
    return hashlib.sha256(str(card_number).encode()).hexdigest()

def desensitize_card_numbers(input_file, output_file):
    """对Excel文件中的'读者卡号'列进行脱敏处理，并生成一个新的文件，不保存原始读者卡号列"""
    # 读取Excel文件
    df = pd.read_excel(input_file)

    # 对'读者卡号'列进行脱敏处理，如果为空则保持原样
    df['读者卡号_脱敏'] = df['读者卡号'].apply(lambda x: hash_card_number(x) if pd.notnull(x) else x)

    # 删除原始的'读者卡号'列
    df = df.drop(columns=['读者卡号'])

    # 保存处理后的数据到新的Excel文件
    df.to_excel(output_file, index=False)

    print("脱敏处理完成，结果已保存到:", output_file)

def filter_and_save_data(file_path, output_file_path, min_unique_readers=8, top_n=10):
    """
    筛选并保存 Excel 数据。

    :param file_path: 输入的 Excel 文件路径
    :param output_file_path: 输出的 Excel 文件路径
    :param min_unique_readers: 最少不同的读者卡号数量
    :param top_n: 每个书名的前 n 条记录
    """
    # 读取 Excel 文件，并确保 '出库时间' 列被解析为 datetime 对象
    df = pd.read_excel(file_path, parse_dates=['出库时间'])

    # 计算每本书的不同读者数量
    reader_counts = df.groupby('书名')['读者卡号_脱敏'].nunique()
    
    # 获取符合最少读者数量条件的书名
    qualified_books = reader_counts[reader_counts >= min_unique_readers].index
    
    # 在符合条件的书中找出借阅次数最多的
    book_counts = df[df['书名'].isin(qualified_books)]['书名'].value_counts()
    
    # 获取前top_n本书
    selected_books = book_counts.head(top_n).index
    
    # 筛选最终数据
    filtered_df = df[df['书名'].isin(selected_books)]

    # 保存结果到新的 Excel 文件
    filtered_df.to_excel(output_file_path, index=False)

    print(f"筛选后的数据已保存到 {output_file_path}")
    return filtered_df, book_counts

def process_filtered_data(filtered_df, book_counts, json_output_path):
    """
    进一步处理筛选后的数据，并将其解析为 JSON 格式。

    :param filtered_df: 筛选后的 DataFrame
    :param book_counts: 每个书名的出现次数
    :param json_output_path: 输出的 JSON 文件路径
    """
    # 初始化 JSON 数据结构
    json_data = {}

    # 定义正则表达式来去掉末尾的 `#` 及其后面的数字
    pattern = re.compile(r'#.*$')

    # 初始化月份计数器
    month_counts = {book: [0] * 12 for book in filtered_df['书名'].unique()}

    # 遍历筛选后的数据
    for index, row in filtered_df.iterrows():
        # 检查当前行是否有空值
        if row.isnull().any():
            continue  # 如果有空值，跳过该行

        book_title = row['书名']
        call_number = row['索书号']
        reader_id = row['读者卡号_脱敏']
        checkout_time = row['出库时间']

        # 将出库时间转换为日期格式
        checkout_date = checkout_time.strftime('%Y-%m-%d')

        # 去掉索书号末尾的 `#` 及其后面的数字
        cleaned_call_number = re.sub(pattern, '', call_number)

        # 更新月份计数器
        month = checkout_time.month
        month_counts[book_title][month - 1] += 1

        # 如果书名不在 JSON 数据中，添加书名节点
        if book_title not in json_data:
            json_data[book_title] = {
                '总次数': int(book_counts[book_title]),  # 添加书名出现的总次数
                '索书号': {}
            }

        # 如果索书号不在书名节点下，添加索书号节点
        if cleaned_call_number not in json_data[book_title]['索书号']:
            json_data[book_title]['索书号'][cleaned_call_number] = []

        # 检查是否已经存在相同的读者卡号和出库时间
        existing_record = next((record for record in json_data[book_title]['索书号'][cleaned_call_number] if record['读者卡号'] == reader_id and record['出库时间'] == checkout_date), None)

        # 如果不存在相同的记录，则添加借阅记录
        if not existing_record:
            json_data[book_title]['索书号'][cleaned_call_number].append({
                '读者卡号': reader_id,
                '出库时间': checkout_date
            })

    # 将月份计数器添加到 JSON 数据中
    for book_title, counts in month_counts.items():
        json_data[book_title]['月份借阅量'] = {f'{i+1}月': count for i, count in enumerate(counts)}

    # 将 JSON 数据保存到文件
    with open(json_output_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=4)

    print(f"JSON 数据已保存到 {json_output_path}")

# 使用示例
if __name__ == "__main__":
    # 获取当前脚本所在的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 构建数据文件的完整路径
    input_file = os.path.join(script_dir, '..', 'data', 'source-data.xlsx')
    desensitized_file = os.path.join(script_dir, '..', 'data', 'source-data_desensitized.xlsx')
    output_file = os.path.join(script_dir, '..', 'data', 'filtered_data.xlsx')
    json_output_file = os.path.join(script_dir, '..', 'data', 'filtered_data.json')

    # 对Excel文件进行脱敏处理
    desensitize_card_numbers(input_file, desensitized_file)

    # 筛选并保存数据
    filtered_df, book_counts = filter_and_save_data(desensitized_file, output_file)

    # 进一步处理筛选后的数据并保存为 JSON
    process_filtered_data(filtered_df, book_counts, json_output_file)