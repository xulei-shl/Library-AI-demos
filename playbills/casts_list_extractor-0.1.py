import os
import json
import pandas as pd
from datetime import datetime
import shows_list_optimizer


# 同一个name中多个姓名用分号隔开。新版本将按照分号拆分为不同的json节点组

def extract_json_content(result):
    if '```json' in result:
        json_start = result.find('```json') + len('```json')
        json_end = result.find('```', json_start)
        return result[json_start:json_end].strip()
    return result

def optimize_name(name, logger):
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
        print(f"JSON解析失败: {json_content}")
        return name, input_tokens, output_tokens

def process_casts_list(image_folder, logger):
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
        performing_events = json.loads(row['演出节目单']) if isinstance(row['演出节目单'], str) else row['演出节目单']

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
                processed_casts = result_json.get("performanceCasts", [])
                
                # 创建变量来累加 tokens
                total_input_tokens = input_tokens
                total_output_tokens = output_tokens
                
                # 优化每个演员的名字并拆分多个名字
                print(f"\n开始优化演职人员名字...\n")
                logger.info(f"开始优化演职人员名字...\n")
                new_processed_casts = []
                for cast in processed_casts:
                    names = cast['name'].split(';')
                    for name in names:
                        optimized_name, name_input_tokens, name_output_tokens = optimize_name(name.strip(), logger)
                        new_cast = {
                            'name': optimized_name,
                            'role': cast['role'],
                            'description': cast['description']
                        }
                        new_processed_casts.append(new_cast)
                        # 累加 tokens
                        total_input_tokens += name_input_tokens
                        total_output_tokens += name_output_tokens
                
                result_json = {
                    "content": new_processed_casts,
                    "metadata": {
                        "model_name": model_name,
                        "timestamp": datetime.now().isoformat()
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
                    event['performingEvent']['performanceCasts'] = result_json
            else:
                performing_events['performingEvent']['performanceCasts'] = result_json

            df.loc[i, '演职人员清单'] = json.dumps(performing_events, ensure_ascii=False)
            df.loc[i, '输入token-总3'] = df.loc[i, '输入token-总2'] + total_input_tokens
            df.loc[i, '输出token-总3'] = df.loc[i, '输出token-总2'] + total_output_tokens

            print(f"更新Excel: 输入token-总3={df.loc[i, '输入token-总3']}, 输出token-总3={df.loc[i, '输出token-总3']}")
            df.to_excel(excel_file_path, index=False)
            print(f"Excel文件已更新: {excel_file_path}")
        else:
            print(f"{file_name}，Excel 第 {i+1} 行已有演职人员清单，跳过处理")
            print(f"{file_name}，Excel 第 {i+1} 行已有演职人员清单，跳过处理")

    print(f"所有文件处理完成，结果已保存到 {excel_file_path}")