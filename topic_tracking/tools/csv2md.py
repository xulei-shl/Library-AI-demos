import os
import pandas as pd
from datetime import datetime
import time
from tools.topic_path import get_file_path, read_csv


def parse_date(date_string):
    """
    尝试使用多种格式解析日期字符串
    """
    formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']
    for fmt in formats:
        try:
            return pd.to_datetime(date_string, format=fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {date_string}")


def convert_csv_to_md(selected_topic, st=None):

    folder_path = get_file_path(selected_topic)
    file_name = selected_topic.replace(' ', '_') + '.csv'
    file_path = os.path.join(folder_path, file_name)

    file_dir = os.path.dirname(file_path)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        if st:
            st.error(f"未找到主题词 '{selected_topic}' 对应的 CSV 文件。")
            time.sleep(1.5)
            st.rerun()
        return False

    # 读取CSV文件
    try:
        df = read_csv(file_path)
    except pd.errors.EmptyDataError:
        if st:
            st.error(f"主题词 '{selected_topic}' 对应的 CSV 文件为空。")
            time.sleep(1.5)
            st.rerun()
        return False

    # 检查是否存在"爬取时间"列
    if '爬取时间' not in df.columns:
        if st:
            st.error("CSV文件中缺少'爬取时间'列。")
            time.sleep(1.5)
            st.rerun()
        return False

    # 获取最新的Markdown文件名中的日期
    existing_md_files = [f for f in os.listdir(file_dir) if f.startswith(selected_topic.replace(' ', '_')) and f.endswith('.md')]
    if existing_md_files:
        latest_md_file = max(existing_md_files, key=lambda x: datetime.strptime(x.split('_')[-1].split('.')[0], "%Y%m%d"))
        latest_md_date = datetime.strptime(latest_md_file.split('_')[-1].split('.')[0], "%Y%m%d")
    else:
        latest_md_date = datetime.min

    # 解析CSV文件中的爬取时间
    df['爬取时间'] = df['爬取时间'].apply(parse_date)
    latest_csv_date = df['爬取时间'].max()

    # 检查是否有新的数据需要转换
    if latest_csv_date.date() <= latest_md_date.date():
        if st:
            st.info(f"没有新的数据需要转换，最新的爬取时间是 {latest_csv_date.date()}，最新的Markdown文件日期是 {latest_md_date.date()}。")
            time.sleep(1.5)
            st.rerun()
        return False

    # 过滤出爬取时间在最新Markdown文件日期之后的数据
    new_data_df = df[df['爬取时间'].dt.date > latest_md_date.date()]

    # 初始化Markdown字符串
    markdown_text = ""

    # 遍历每一行，将其转换为Markdown格式
    for index, row in new_data_df.iterrows():
        if index > 0:  # 在每个H2段落前添加分割符，但不在第一个H2段落前添加
            markdown_text += "\n---\n\n"
        # 添加H2标题
        markdown_text += f"## {row['题名']}\n\n"
        # 添加H3标题和内容，跳过'编号'、'专辑'和'专题'列
        for column in new_data_df.columns:
            if column not in ['编号', '专辑', '专题'] and pd.notna(row[column]) and row[column] != "无":  # 检查单元格是否为空且不等于"无"
                markdown_text += f"### {column}\n\n{row[column]}\n\n"

    # 获取当天日期
    today_date = datetime.now().strftime("%Y%m%d")

    # 构建输出文件名
    output_file_name = f"{selected_topic.replace(' ', '_')}_{today_date}.md"
    output_file_path = os.path.join(file_dir, output_file_name)

    # 检查是否已存在当天的Markdown文件
    if os.path.exists(output_file_path):
        # 如果文件已存在，追加内容
        with open(output_file_path, 'a', encoding='utf-8') as file:
            file.write("\n\n" + markdown_text)  # 添加两个换行符以分隔新旧内容
        if st:
            st.success(f"新内容已追加到现有的Markdown文件：{output_file_path}")
            time.sleep(1.5)
            st.rerun()
    else:
        # 如果文件不存在，创建新文件
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(markdown_text)
        if st:
            st.success(f"新的Markdown文件已生成：{output_file_path}")
            time.sleep(1.5)
            st.rerun()

    return True

# Streamlit 代码部分
import streamlit as st

def main():
    st.title("CSV to Markdown Converter")

    # 假设 st.session_state.topics_df 已经在其他地方定义
    selected_topic = st.selectbox("选择主题词", st.session_state.topics_df['topic'].tolist())
    
    if st.button("转换为 Markdown"):
        convert_csv_to_md(selected_topic, st=st)

if __name__ == "__main__":
    main()