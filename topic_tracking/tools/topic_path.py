import os
import pandas as pd
from tools.utils import read_csv

# 定义保存主题词的CSV文件路径
TOPICS_FILE = 'data/topics.csv'

def load_topics():
    if os.path.exists(TOPICS_FILE):
        try:
            return read_csv(TOPICS_FILE)
        except pd.errors.EmptyDataError:
            return pd.DataFrame(columns=['topic', 'folder_path'])
    return pd.DataFrame(columns=['topic', 'folder_path'])

def create_csv_file(topic):
    topic_folder = topic.replace(' ', '_')
    folder_path = os.path.join('data', topic_folder)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_name = topic.replace(' ', '_') + '.csv'
    file_path = os.path.join(folder_path, file_name)
    if not os.path.exists(file_path):
        columns = ['编号', '题名', '作者', '作者机构', '日期', '期刊', '专辑', '专题', '引用数', '下载数', '关键词', '摘要', 'URL', '爬取时间']
        pd.DataFrame(columns=columns).to_csv(file_path, index=False, encoding='utf-8')
    return folder_path

def get_file_path(selected_topic):
    # 加载主题词
    topics_df = load_topics()
    
    # 获取文件路径
    file_path = topics_df[topics_df['topic'] == selected_topic]['folder_path'].values[0]
    return str(file_path)