import pandas as pd
from datetime import datetime
import os

def log_vector_info(selected_topic, selected_file, folder_path):
    log_file_name = '向量化日志.xlsx'
    log_file_path = os.path.join(folder_path, log_file_name)
    
    # 获取当前日期和时间
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 创建日志数据
    log_data = {
        '向量化时间': [current_datetime],
        '主题词': [selected_topic],
        '向量化文件名': [selected_file]
    }
    
    # 创建 DataFrame
    log_df = pd.DataFrame(log_data)
    
    # 检查日志文件是否存在
    if os.path.exists(log_file_path):
        # 读取现有日志文件
        existing_log_df = pd.read_excel(log_file_path)
        # 追加新日志数据
        log_df = pd.concat([existing_log_df, log_df], ignore_index=True)
    else:
        print(f"日志文件不存在，将创建新文件: {log_file_path}")
    
    # 写入或覆盖日志文件
    log_df.to_excel(log_file_path, index=False)
    print(f"日志已写入: {log_file_path}")