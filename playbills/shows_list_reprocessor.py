import os
from datetime import datetime
import pandas as pd

def replace_texts(image_folder):
    # 定义路径
    output_folder = os.path.join(image_folder, 'output')
    current_date = datetime.now().strftime('%Y%m%d')
    excel_file_path = os.path.join(output_folder, f'results_{current_date}.xlsx')

    # 读取Excel文件
    df = pd.read_excel(excel_file_path)

    # 替换 "performanceWorks" 为 "performanceWorks"
    df.replace('performanceWorks', 'performanceWorks', inplace=True)

    # 保存修改后的Excel文件
    df.to_excel(excel_file_path, index=False)