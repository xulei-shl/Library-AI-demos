import os
import json
import pandas as pd
from datetime import datetime
import shows_list_optimizer
from tools.llm_json_extractor import extract_json_content


def optimize_name(name, logger):
    print(f"\n开始优化名字: {name}")
    logger.info(f"开始优化名字: {name}")
    optimized_result, model_name, input_tokens, output_tokens = shows_list_optimizer.optimize_shows_list(
        name, logger, prompt_key="name_optimizer_prompt"
    )
    json_content = extract_json_content(optimized_result)
    print(f"\n优化后的名字: {json_content}\n")
    logger.info(f"优化后的名字: {json_content}")
    try:
        result_json = json.loads(json_content)
        return result_json.get("result", name), input_tokens, output_tokens
    except json.JSONDecodeError:
        print(f"\nJSON解析失败: {json_content}")
        logger.error(f"JSON解析失败: {json_content}")
        return name, input_tokens, output_tokens

def split_casts(performing_events):
    if isinstance(performing_events, list):
        for event in performing_events:
            split_casts_for_event(event['PerformanceEvent'])
    else:
        split_casts_for_event(performing_events['PerformanceEvent'])
    return performing_events

def split_casts_for_event(event):
    if 'eventCast' in event and 'content' in event['eventCast']:
        new_casts = []
        for cast in event['eventCast']['content']:
            names = cast['name'].split(';')
            for name in names:
                new_cast = {
                    'type': 'Person',
                    'name': name.strip(),
                    'roleName': cast['roleName'],
                    'description': cast['description']
                }
                new_casts.append(new_cast)
        event['eventCast']['content'] = new_casts

def process_casts_list(image_folder, logger, optimize_names=True):
    print(f"开始处理文件夹: {image_folder}")
    output_folder = os.path.join(image_folder, 'output')
    current_date = datetime.now().strftime('%Y%m%d')
    excel_file_path = os.path.join(output_folder, f'results_{current_date}.xlsx')
    
    print(f"读取Excel文件: {excel_file_path}")
    df = pd.read_excel(excel_file_path)

    new_columns = ['输入token-总3', '输出token-总3', '演职人员清单']
    for col in new_columns:
        if col not in df.columns:
            df[col] = pd.NA

    for i, row in df.iterrows():
        file_name = row['文件名']
        performing_events = json.loads(row['演出事件与作品']) if isinstance(row['演出事件与作品'], str) else row['演出事件与作品']

        print(f"\n处理文件: {file_name}, Excel行: {i+1}")

        if pd.isna(row['演职人员清单']):
            md_file_path = os.path.join(output_folder, f'{file_name}_ocr_1_final_result.md')
            with open(md_file_path, 'r', encoding='utf-8') as file:
                md_content = file.read()

            combined_prompt = f"### 原始的OCR文本：\n{md_content}"
            
            optimized_result, model_name, input_tokens, output_tokens = shows_list_optimizer.optimize_shows_list(
                combined_prompt, logger, prompt_key="casts_list_user_prompt"
            )

            json_content = extract_json_content(optimized_result)
            print(f"\n提取的演职人员清单: {json_content}\n")
            logger.info(f"提取的演职人员清单: {json_content}")
            
            try:
                result_json = json.loads(json_content)
                processed_casts = result_json.get("eventCast", [])

                # 创建变量来累加 tokens
                total_input_tokens = input_tokens
                total_output_tokens = output_tokens
                
                # 根据参数决定是否执行名字优化
                if optimize_names:
                    # 优化每个演员的名字
                    print(f"\n开始优化演职人员名字...\n")
                    logger.info(f"开始优化演职人员名字...\n")
                    for cast in processed_casts:
                        optimized_name, name_input_tokens, name_output_tokens = optimize_name(cast['name'], logger)
                        cast['name'] = optimized_name
                        total_input_tokens += name_input_tokens
                        total_output_tokens += name_output_tokens
                else:
                    print("\n跳过名字优化步骤\n")
                    logger.info("跳过名字优化步骤")
                
                result_json = {
                    "content": processed_casts,
                    "metadata": {
                        "model_name": model_name,
                        "timestamp": datetime.now().isoformat(),
                        "name_optimized": optimize_names
                    }
                }
            except json.JSONDecodeError:
                print("JSON解析失败")
                result_json = {
                    "content": [],
                    "metadata": {
                        "model_name": model_name,
                        "timestamp": datetime.now().isoformat()
                    },
                    "error": "Failed to decode JSON",
                    "raw_content": json_content
                }

            # 处理单事件和多事件的情况
            if isinstance(performing_events, list):
                for event in performing_events:
                    event['PerformanceEvent']['eventCast'] = result_json
            else:
                performing_events['PerformanceEvent']['eventCast'] = result_json

            # 拆分演职人员名单
            performing_events = split_casts(performing_events)

            df.loc[i, '演职人员清单'] = json.dumps(performing_events, ensure_ascii=False)
            df.loc[i, '输入token-总3'] = df.loc[i, '输入token-总2'] + total_input_tokens
            df.loc[i, '输出token-总3'] = df.loc[i, '输出token-总2'] + total_output_tokens

            print(f"更新Excel: 输入token-总3={df.loc[i, '输入token-总3']}, 输出token-总3={df.loc[i, '输出token-总3']}")
            df.to_excel(excel_file_path, index=False)
            print(f"Excel文件已更新: {excel_file_path}")
        else:
            print(f"{file_name}，Excel 第 {i+1} 行已有演职人员清单，跳过处理")

    print(f"所有文件处理完成，结果已保存到 {excel_file_path}")
