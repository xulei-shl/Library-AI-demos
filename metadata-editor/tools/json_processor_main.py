from logs import setup_logger
import os
import playbiils_json_clean
import json2sql

# 配置图片文件夹地址
base_path = r'E:\scripts\jiemudan\2\output'
# 设置日志记录器
logger = setup_logger(r'E:\scripts\jiemudan\logs')



# 提取最终结果到json文件
# 查找最近的Excel文件
excel_files = [f for f in os.listdir(base_path) if f.startswith('results_') and f.endswith('.xlsx')]
if not excel_files:
    raise FileNotFoundError("No Excel files found starting with 'results_'")

excel_files.sort(key=lambda x: os.path.getmtime(os.path.join(base_path, x)), reverse=True)
excel_file = os.path.join(base_path, excel_files[0])
logger.info(f"\nUsing Excel file: {excel_file}\n")
print(f"Using Excel file: {excel_file}")

playbiils_json_clean.cleaning_json(excel_file, logger)

# json数据插入数据库
json2sql.json_sqlite(base_path, logger)
