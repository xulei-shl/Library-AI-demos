from tools.topic_path import get_file_path, read_csv
import os

def check_duplicates(selected_topic):
    # 读取CSV文件

    folder_path = get_file_path(selected_topic)
    file_name = selected_topic.replace(' ', '_') + '.csv'
    file_path = os.path.join(folder_path, file_name)

    df = read_csv(file_path)
    
    # 检查题名和期刊列的重复数据
    duplicates = df[df.duplicated(['题名', '期刊'], keep=False)]
    
    return duplicates

# def remove_duplicates(selected_topic):
#     # 读取CSV文件
#     folder_path = get_file_path(selected_topic)
#     file_name = selected_topic.replace(' ', '_') + '.csv'
#     file_path = os.path.join(folder_path, file_name)

#     df = read_csv(file_path)
    
#     # 删除重复数据
#     df_cleaned = df.drop_duplicates(subset=['题名', '期刊'], keep='first')
    
#     # 保存清理后的数据到CSV文件
#     df_cleaned.to_csv(file_path, index=False, encoding='gbk')
