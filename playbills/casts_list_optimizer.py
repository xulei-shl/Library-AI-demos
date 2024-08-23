import os
import json
import pandas as pd
from datetime import datetime
import shows_list_optimizer
from tools.llm_json_extractor import extract_json_content

def process_cast_description(cast_description, logger):
    if cast_description is None or cast_description == "":
        return []
    
    optimized_result, model_name, input_tokens, output_tokens = shows_list_optimizer.optimize_shows_list(
        cast_description, logger, prompt_key="cast_description_optimizer_prompt"
    )
    
    json_content = extract_json_content(optimized_result)
    try:
        result_json = json.loads(json_content)
        return result_json, input_tokens, output_tokens
    except json.JSONDecodeError:
        print(f"JSON解析失败: {json_content}")
        result_json = {"castDescription": {"description": cast_description}}

    return result_json, input_tokens, output_tokens

def process_performance_works(performance_works, logger):
    total_input_tokens = 0
    total_output_tokens = 0
    
    print(f"\n开始结构化演职人员描述...\n")
    logger.info(f"开始结构化演职人员描述...\n")

    for work in performance_works['content']:
        if 'castDescription' in work:
            if work['castDescription'] is None:
                work['castDescription'] = []
            else:
                result, input_tokens, output_tokens = process_cast_description(work['castDescription'], logger)
                if isinstance(work['castDescription'], dict) and 'description' in work['castDescription']:
                    work['castDescription'] = {
                        'description': work['castDescription']['description'],
                        'performanceResponsibilities': result.get('performanceResponsibilities', [])
                    }
                elif isinstance(work['castDescription'], str):
                    work['castDescription'] = {
                        'description': work['castDescription'],
                        'performanceResponsibilities': result.get('performanceResponsibilities', [])
                    }
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
    
    return performance_works, total_input_tokens, total_output_tokens

def optimize_casts(image_folder, logger):
    print(f"开始处理文件夹: {image_folder}")
    output_folder = os.path.join(image_folder, 'output')
    current_date = datetime.now().strftime('%Y%m%d')
    excel_file_path = os.path.join(output_folder, f'results_{current_date}.xlsx')
    
    print(f"读取Excel文件: {excel_file_path}")
    df = pd.read_excel(excel_file_path)

    new_columns = ['输入token-总4', '输出token-总4', '演职人员清单优化']
    for col in new_columns:
        if col not in df.columns:
            df[col] = pd.NA

    for i, row in df.iterrows():
        file_name = row['文件名']
        performing_events = json.loads(row['演职人员清单']) if isinstance(row['演职人员清单'], str) else row['演职人员清单']

        print(f"\n处理文件: {file_name}, Excel行: {i+1}")

        if pd.isna(row['演职人员清单优化']):
            total_input_tokens = 0
            total_output_tokens = 0

            if isinstance(performing_events, list):
                for event in performing_events:
                    if 'performanceWorks' in event['performingEvent']:
                        event['performingEvent']['performanceWorks'], input_tokens, output_tokens = process_performance_works(
                            event['performingEvent']['performanceWorks'], logger
                        )
                        total_input_tokens += input_tokens
                        total_output_tokens += output_tokens
            else:
                if 'performanceWorks' in performing_events['performingEvent']:
                    performing_events['performingEvent']['performanceWorks'], input_tokens, output_tokens = process_performance_works(
                        performing_events['performingEvent']['performanceWorks'], logger
                    )
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens

            df.loc[i, '演职人员清单优化'] = json.dumps(performing_events, ensure_ascii=False)
            df.loc[i, '输入token-总4'] = df.loc[i, '输入token-总3'] + total_input_tokens
            df.loc[i, '输出token-总4'] = df.loc[i, '输出token-总3'] + total_output_tokens

            print(f"更新Excel: 输入token-总4={df.loc[i, '输入token-总4']}, 输出token-总4={df.loc[i, '输出token-总4']}")
            df.to_excel(excel_file_path, index=False)
            print(f"Excel文件已更新: {excel_file_path}")
        else:
            print(f"{file_name}，Excel 第 {i+1} 行已有演职人员清单优化，跳过处理")

    print(f"所有文件处理完成，结果已保存到 {excel_file_path}")