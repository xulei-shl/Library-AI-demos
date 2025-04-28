import os
import json
import pandas as pd
from datetime import datetime
import shows_list_optimizer
from tools.llm_json_extractor import extract_json_content
import json

def process_event(event, logger):
    print(f"\n开始演出事件与作品类型处理: {event}...\n")
    logger.info(f"开始演出事件与作品类型处理...\n")

    event_json = event  # event 已经是一个字典，不需要 JSON 解析

    optimized_result, model_name, input_tokens, output_tokens = shows_list_optimizer.optimize_shows_list(
        event_json, logger, prompt_key="event_type_user_prompt"
    )

    json_content = extract_json_content(optimized_result)
    print(f"\n返回信息: {json_content}\n")
    logger.info(f"返回信息: {json_content}")

    try:
        # 尝试将 json_content 解析为 Python 字典
        json_dict = json.loads(json_content)
        if "type" in json_dict:
            event_type = {
                "eventType": {
                    "type": json_dict["type"],
                    "metadata": {
                        "model_name": model_name,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            }
            return event_type, input_tokens, output_tokens
    except json.JSONDecodeError:
        logger.error(f"无法解析 JSON 内容: {json_content}")
    except KeyError:
        logger.error(f"JSON 内容中没有 'type' 键: {json_content}")

    return None, input_tokens, output_tokens

def process_performing_events(image_folder, logger):
    print(f"开始处理文件夹: {image_folder}")
    output_folder = os.path.join(image_folder, 'output')
    current_date = datetime.now().strftime('%Y%m%d')
    excel_file_path = os.path.join(output_folder, f'results_{current_date}.xlsx')
    
    print(f"读取Excel文件: {excel_file_path}")
    df = pd.read_excel(excel_file_path)

    new_columns = ['输入token-总5', '输出token-总5', '演出类型']
    for col in new_columns:
        if col not in df.columns:
            df[col] = pd.NA

    processed_files = 0

    for i, row in df.iterrows():
        file_name = row['文件名']
        performing_events = json.loads(row['演出事件与作品']) if isinstance(row['演出事件与作品'], str) else row['演出事件与作品']
        optimized_events = json.loads(row['演职人员清单优化']) if isinstance(row['演职人员清单优化'], str) else row['演职人员清单优化']

        print(f"\n处理文件: {file_name}, Excel行: {i+1}")

        if pd.notna(row['演出类型']):
            logger.info(f"{file_name}，Excel 第 {i+1} 行已有演出类型，跳过处理")
            print(f"{file_name}，Excel 第 {i+1} 行已有演出类型，跳过处理")
            continue

        performing_events = [performing_events] if not isinstance(performing_events, list) else performing_events
        optimized_events = [optimized_events] if not isinstance(optimized_events, list) else optimized_events

        total_input_tokens = 0
        total_output_tokens = 0

        for idx, event in enumerate(performing_events):
            logger.info(f"处理事件: {event['PerformanceEvent']['name']}")
            print(f"处理事件: {event['PerformanceEvent']['name']}")
            
            event_type, input_tokens, output_tokens = process_event(event['PerformanceEvent'], logger)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens

            if event_type and idx < len(optimized_events):
            # 更新 optimized_events 中的 PerformanceEvent
                if 'PerformanceEvent' in optimized_events[idx]:
                    optimized_events[idx]['PerformanceEvent']['eventType'] = event_type['eventType']
                else:
                    optimized_events[idx]['PerformanceEvent'] = {'eventType': event_type['eventType']}        

        df.loc[i, '输入token-总5'] = df.loc[i, '输入token-总4'] + total_input_tokens
        df.loc[i, '输出token-总5'] = df.loc[i, '输出token-总4'] + total_output_tokens
        
        # 将更新后的 optimized_events 保存到 '演出类型' 列
        df.loc[i, '演出类型'] = json.dumps(optimized_events, ensure_ascii=False)
            
        print(f"更新Excel: 输入token-总5={df.loc[i, '输入token-总5']}, 输出token-总5={df.loc[i, '输出token-总5']}")
        df.to_excel(excel_file_path, index=False)
        print(f"Excel文件已更新: {excel_file_path}")

        processed_files += 1

    if processed_files > 0:
        logger.info(f"所有文件处理完成，结果已保存到 {excel_file_path}")
        print(f"所有文件处理完成，结果已保存到 {excel_file_path}")
    else:
        logger.info("没有处理任何文件")
        print("没有处理任何文件")

