import os
import json
import pandas as pd
from datetime import datetime

def excel2json(image_folder):
    output_folder = os.path.join(image_folder, 'output')
    current_date = datetime.now().strftime('%Y%m%d')
    excel_file_path = os.path.join(output_folder, f'results_{current_date}.xlsx')
    
    print(f"读取Excel文件: {excel_file_path}")
    df = pd.read_excel(excel_file_path)
    
    selected_column = '演出类型'
    json_data = df[selected_column].apply(json.loads).tolist()
    json_data_str = json.dumps(json_data, ensure_ascii=False)
    
    jsondata_dir = os.path.join(os.path.dirname(__file__), "jsondata")
    if not os.path.exists(jsondata_dir):
        os.makedirs(jsondata_dir)

    current_date = datetime.now().strftime('%Y%m%d')
    json_file_path = os.path.join(jsondata_dir, f"results_{current_date}_local_data.json")
    with open(json_file_path, "w", encoding='utf-8') as f:
        f.write(json_data_str)
    
    print("数据已保存到本地 JSON 文件")