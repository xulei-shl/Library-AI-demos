import os
import json
import pandas as pd
import string

def add_related_to(obj):
    if isinstance(obj, dict):
        for key, value in list(obj.items()):  # Convert items to a list
            if key == 'castDescription':
                if 'performanceResponsibilities' in value:
                    for item in value['performanceResponsibilities']:
                        if "relatedTo" not in item:
                            item["relatedTo"] = []  # Change to empty list
            elif isinstance(value, (dict, list)):
                add_related_to(value)
            elif key != 'castDescription' and "relatedTo" not in obj:
                obj["relatedTo"] = []  # Change to empty list
    elif isinstance(obj, list):
        for item in obj:
            add_related_to(item)

def cleaning_json(excel_file, logger):

    df = pd.read_excel(excel_file)

    selected_column = '演出类型'
    file_name_column = '文件名'  # 假设文件名列的名称为'文件名'

    json_data = []
    for index, row in df.iterrows():
        event_data = json.loads(row[selected_column])
        file_name = row[file_name_column]
        
        # 使用字母表生成后缀
        suffixes = iter(string.ascii_uppercase)
        
        # 计算当前行中performingEvent的数量
        performing_events_count = sum(1 for event in event_data if 'performingEvent' in event)
        
        for i, event in enumerate(event_data):
            if 'performingEvent' in event:
                # 如果只有一个performingEvent，不添加后缀
                if performing_events_count == 1:
                    event_id = file_name
                else:
                    event_id = f"{file_name}-{next(suffixes)}"
                
                event['performingEvent']['id'] = event_id
                event['performingEvent']['hasMaterials'] = {
                    "type": "Digital Images",
                    "linkID": file_name
                }
                event['performingEvent']['relatedTo'] = []  # Change to empty list
                
                event['performingEvent']['deleted'] = False
                
                # 添加 performingSeason 字段
                event['performingEvent']['performingSeason'] = {
                    "name": "",
                    "type": "",
                    "time": "",
                    "location": {
                        "venue": "",
                        "description": "",
                        "address": "",
                        "relatedTo": []  # Change to empty list
                    },
                    "relatedTo": []  # Change to empty list
                }
                
                # 为eventType添加relatedTo
                if 'eventType' in event['performingEvent']:
                    event['performingEvent']['eventType']['relatedTo'] = []  # Change to empty list
                if 'eventType' in event['performingEvent']:
                    event['performingEvent']['location']['relatedTo'] = []  # Change to empty list
                
                # 添加 relatedTo 字段到指定的节点
                for key in ['performanceResponsibilities', 'performanceCasts', 'performanceWorks', 'involvedParties', 'performingTroupes']:
                    if key in event['performingEvent']:
                        if key in ['performanceCasts', 'performanceWorks']:
                            if 'content' in event['performingEvent'][key]:
                                add_related_to(event['performingEvent'][key]['content'])
                        else:
                            add_related_to(event['performingEvent'][key])
                
                # 将每个performingEvent拆分为单独的JSON对象
                json_data.append({"performingEvent": event['performingEvent']})


    # 获取原始Excel文件的路径和文件名（不包括扩展名）
    excel_path = os.path.dirname(excel_file)
    excel_name = os.path.splitext(os.path.basename(excel_file))[0]

    # 创建新的JSON文件名
    json_file_name = f"{excel_name}-json-data.json"
    json_file_path = os.path.join(excel_path, json_file_name)

    # 将JSON数据写入新文件
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    
    # logger.info(f"\nJSON数据已保存到: {json_file_path}")

    # print(f"JSON数据已保存到: {json_file_path}")

# if __name__ == "__main__":

#     # 配置图片文件夹地址
#     base_path = r'E:\scripts\jiemudan\2\output'
#     # 设置日志记录器
#     logger = setup_logger(r'E:\scripts\jiemudan\logs')

#     # 查找最近的Excel文件
#     excel_files = [f for f in os.listdir(base_path) if f.startswith('results_') and f.endswith('.xlsx')]
#     if not excel_files:
#         raise FileNotFoundError("No Excel files found starting with 'results_'")
    
#     excel_files.sort(key=lambda x: os.path.getmtime(os.path.join(base_path, x)), reverse=True)
#     excel_file = os.path.join(base_path, excel_files[0])
#     logger.info(f"\nUsing Excel file: {excel_file}\n")
#     print(f"Using Excel file: {excel_file}")

#     # 提取最终结果到json文件
#     cleaning_json(excel_file)