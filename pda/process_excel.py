import os
import pandas as pd
from llm_extraction import extract_bookinfo
from logs import setup_logger
from json_excel import save_to_excel

def process_excel_files(BASE_PATH, logger, llm_config):
    logger.info(f"开始处理Excel文件: {BASE_PATH}")
    all_outputs = []

    for file_name in os.listdir(BASE_PATH):
        if file_name.endswith('.xlsx'):
            file_path = os.path.join(BASE_PATH, file_name)
            logger.info(f"处理Excel文件: {file_path}")
            print(f"----------------------------------------")
            print(f"处理Excel文件: {file_path}")

            df = pd.read_excel(file_path)

            # Iterate through all rows using `df.iterrows()`
            for index, row in df.iterrows():
                date = row['日期']
                reader_info = row['读者信息']
                content = row['咨询内容']
                query = f"## 提交信息\n提交时间 = {date}\n读者信息 = {reader_info}\n\n## 咨询内容\n{content}"
                print(f"----------------------------------------")
                print(query)
                logger.info(f"处理Excel行: {query}")

                try:
                    llm_output = extract_bookinfo(query, file_name, llm_config, logger)
                    save_to_excel(llm_output, BASE_PATH, logger)
                    all_outputs.append(llm_output)
                except Exception as e:
                    logger.error(f"extract_bookinfo 函数运行错误: {str(e)}")
                    save_to_excel({'原文': query, '原件': file_name, '错误信息': '大模型API调用错误'}, BASE_PATH, logger)                
    
    if all_outputs:
        return all_outputs
    else:
        return None


#测试
# if __name__ == "__main__":
#     llm_config = {
#         "model_name": "glm-3-turbo",
#         "api_key": "your_api_key",
#     }

#     BASE_PATH = r'C:\Users\Administrator\Desktop\pda\2024-06-04'

#     # 日志文件路径
#     LOG_FOLDER_PATH = r'C:\Users\Administrator\Desktop\pda\logs'
#     logger = setup_logger(LOG_FOLDER_PATH)

#     process_excel_files(BASE_PATH, logger, llm_config)
