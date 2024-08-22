import os
import pandas as pd
import json
from datetime import datetime
from dotenv import load_dotenv
import tools.token_counter as token_counter
import tools.llm_requestion as llm
import tools.prompts as prompts
import shows_list_optimizer
import json
import re

# 已合并到 shows_list_extractor.py


load_dotenv()

def get_env_vars():
    env_vars = {
        "OneAPI_API_URL": os.getenv("OneAPI_API_URL"),
        "OneAPI_API_KEY": os.getenv("OneAPI_API_KEY"),
        "DeepSeek_API_URL": os.getenv("DeepSeek_API_URL"),
        "DeepSeek_API_KEY": os.getenv("DeepSeek_API_KEY"),
        "Doubao_API_URL": os.getenv("Doubao_API_URL"),
        "Doubao_API_KEY": os.getenv("Doubao_API_KEY")
    }
    return env_vars

def extract_json_content(result):
    if '```json' in result:
        json_start = result.find('```json') + len('```json')
        json_end = result.find('```', json_start)
        return result[json_start:json_end].strip()
    return result

def select_model(token_count, env_vars):
    if token_count <= 32768:
       return env_vars["OneAPI_API_URL"], env_vars["OneAPI_API_KEY"], "deepseek-chat"
        # return env_vars["DeepSeek_API_URL"], env_vars["DeepSeek_API_KEY"], "deepseek-chat"    
    elif token_count <= 131072:
        return env_vars["Doubao_API_URL"], env_vars["Doubao_API_KEY"], "ep-20240814153435-rmdkh"
    return None, None, None

def get_shows(md_file_path, logger, performing_event):
    print(f"开始处理文件: {md_file_path}")
    user_prompt = prompts.user_prompts["shows_list_user_prompt"]
    system_prompt = prompts.system_prompts["shows_list_single_event_prompt"]

    with open(md_file_path, "r", encoding="utf-8") as file:
        md_content = file.read()

    event_info = f"Event: {performing_event['performingEvent']['name']}"
    combined_prompt = f"{user_prompt}\n\n### 集合演出信息：\n{event_info}\n\n### 原始OCR文本：\n{md_content}"

    token_text = system_prompt + combined_prompt
    token_count = token_counter.count_tokens(token_text)

    logger.info(f"Tokens数量：{token_count}")
    logger.info(f"开始提取 {event_info} 的节目单信息")
    print(f"Tokens数量：{token_count}")
    print(f"开始提取 {event_info} 的节目单信息")

    env_vars = get_env_vars()
    base_url, api_key, model_name = select_model(token_count, env_vars)

    if not model_name:
        logger.info("文本的token数量超过了128k模型的限制")
        print("文本的token数量超过了128k模型的限制")
        return None, token_count, 0

    logger.info(f"调用的模型是{model_name}")
    print(f"调用的模型是{model_name}")

    result, output_token_count = llm.send_request(base_url, api_key, model_name, combined_prompt, logger, system_prompt, response_format={'type': 'json_object'})
    
    json_content = extract_json_content(result)
    logger.info(f"提取的演出节目信息: \n{json_content}")
    print(f"\n提取的演出节目信息: \n{json_content}")

    result_json = json.loads(json_content)
    if any(item.get('castDescription') for item in result_json.get('individualPerformances', []) if item.get('castDescription') is not None) or \
       any(act.get('individualPerformances', []) for act in result_json.get('sectionsOrActs', []) if any(item.get('castDescription') for item in act.get('individualPerformances', []) if item.get('castDescription') is not None)):
        print(f"\n----------------开始演职人员格式化----------------------------\n")
        logger.info(f"开始演职人员格式化")
        optimized_result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
            json_content, logger, prompt_key="add_spaces_user_prompt"
        )
        json_content = extract_json_content(optimized_result)
        print(f"\n----------------演职人员格式化优化结果----------------------------\n")
        print(json_content)
        logger.info(f"演职人员格式化优化结果: {json_content}")

    try:
        result_json = json.loads(json_content)
        result_json["metadata"] = {
            "model_name": model_name,
            "timestamp": datetime.now().isoformat()
        }
    except json.JSONDecodeError:
        print("JSON解析失败")
        result_json = {"error": "Failed to decode JSON", "raw_content": json_content, "metadata": {
            "model_name": model_name,
            "timestamp": datetime.now().isoformat()
        }}

    logger.info(f"节目单信息添加metadata的结果: {json.dumps(result_json, ensure_ascii=False, indent=4)}")
    print(f"节目单信息添加metadata的结果: {json.dumps(result_json, ensure_ascii=False, indent=4)}")
    return result_json, token_count, output_token_count

#旧的处理逻辑舍弃。新逻辑 process_single_event，对每个节目进行循环调用判断其所属的章节演出
def process_event(event, md_file_path, logger):
    result_json, token_count, output_token_count = get_shows(md_file_path, logger, event)
    
    if result_json:
        original_metadata = event['performingEvent'].get('metadata', {})
        
        if 'sectionsOrActs' in result_json:
            event['performingEvent']['sectionsOrActs'] = {
                'content': result_json['sectionsOrActs'],
                'metadata': result_json.get('metadata', {})
            }
            print("更新了sectionsOrActs")
        elif 'individualPerformances' in result_json:
            event['performingEvent']['individualPerformances'] = {
                'content': result_json['individualPerformances'],
                'metadata': result_json.get('metadata', {})
            }
            print("更新了individualPerformances")
        
        event['performingEvent']['metadata'] = original_metadata

    print(f"事件处理完成，输入token: {token_count}, 输出token: {output_token_count}")
    return token_count, output_token_count

def process_single_event(event, shows_list, md_file_path, logger):
    with open(md_file_path, "r", encoding="utf-8") as file:
        md_content = file.read()

    try:
        shows = json.loads(shows_list)
    except json.JSONDecodeError:
        logger.error(f"无法解析节目清单列表: {shows_list}")
        print(f"错误: 无法解析节目清单列表: {shows_list}")
        return None, 0, 0

    total_input_tokens = 0
    total_output_tokens = 0

    logger.info(f"总共有 {len(shows['individualPerformances'])} 个节目需要处理")
    print(f"总共有 {len(shows['individualPerformances'])} 个节目需要处理")

    processed_performances = []

    for index, show in enumerate(shows['individualPerformances'], 1):
        show_name = show['name']
        logger.info(f"处理第 {index} 个节目: {show_name}")
        print(f"处理第 {index} 个节目: {show_name}")
        
        combined_prompt = f"### 集合演出信息：\n{json.dumps(event, ensure_ascii=False)}\n\n### 演出节目名：\n{show_name}\n\n### 原始的OCR文本：\n{md_content}"
        
        optimized_result, input_tokens, output_tokens = shows_list_optimizer.optimize_shows_list(
            combined_prompt, logger, prompt_key="single_shows_to_festivals_user_prompt"
        )
        
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        json_match = re.search(r'\{.*\}', optimized_result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                result_json = json.loads(json_str)
                sections_or_acts = result_json.get('sectionsOrActs')
                show['sectionsOrActs'] = sections_or_acts
                processed_performances.append(show)
            except json.JSONDecodeError:
                logger.warning(f"无法解析节目 '{show_name}' 的返回结果")
                print(f"警告: 无法解析节目 '{show_name}' 的返回结果")
        else:
            logger.warning(f"无法在返回结果中找到JSON格式的数据，节目: '{show_name}'")
            print(f"警告: 无法在返回结果中找到JSON格式的数据，节目: '{show_name}'")

    event['performingEvent']['individualPerformances'] = {
        'content': processed_performances,
        'metadata': {
            "model_name": "deepseek-chat",
            "timestamp": datetime.now().isoformat()
        }
    }

    logger.info(f"单事件处理完成。总输入tokens: {total_input_tokens}, 总输出tokens: {total_output_tokens}")
    print(f"单事件处理完成。总输入tokens: {total_input_tokens}, 总输出tokens: {total_output_tokens}")

    return [event], total_input_tokens, total_output_tokens

def process_multi_events(events, shows_list, md_file_path, logger):
    with open(md_file_path, "r", encoding="utf-8") as file:
        md_content = file.read()

    try:
        shows = json.loads(shows_list)
    except json.JSONDecodeError:
        logger.error(f"无法解析节目清单列表: {shows_list}")
        print(f"错误: 无法解析节目清单列表: {shows_list}")
        return None, 0, 0
    
    total_input_tokens = 0
    total_output_tokens = 0

    logger.info(f"总共有 {len(shows['individualPerformances'])} 个节目需要处理")
    print(f"总共有 {len(shows['individualPerformances'])} 个节目需要处理")

    for index, show in enumerate(shows['individualPerformances'], 1):
        show_name = show['name']
        logger.info(f"处理第 {index} 个节目: {show_name}")
        print(f"处理第 {index} 个节目: {show_name}")
        
        combined_prompt = f"### 集合演出信息：\n{json.dumps(events, ensure_ascii=False)}\n\n### 演出节目名：\n{show_name}\n\n### 原始的OCR文本：\n{md_content}"
        
        optimized_result, input_tokens, output_tokens = shows_list_optimizer.optimize_shows_list(
            combined_prompt, logger, prompt_key="shows_to_festivals_user_prompt"
        )
        
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        json_match = re.search(r'\{.*\}', optimized_result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                result_json = json.loads(json_str)
                matched_event_name = result_json.get('performingEvent')
                sections_or_acts = result_json.get('sectionsOrActs')
            except json.JSONDecodeError:
                logger.warning(f"无法解析节目 '{show_name}' 的返回结果")
                print(f"警告: 无法解析节目 '{show_name}' 的返回结果")
                continue
        else:
            logger.warning(f"无法在返回结果中找到JSON格式的数据，节目: '{show_name}'")
            print(f"警告: 无法在返回结果中找到JSON格式的数据，节目: '{show_name}'")
            continue

        if matched_event_name:
            logger.info(f"节目 '{show_name}' 匹配到事件: {matched_event_name}")
            print(f"节目 '{show_name}' 匹配到事件: {matched_event_name}")
            for event in events:
                if event['performingEvent']['name'] == matched_event_name:
                    if 'individualPerformances' not in event['performingEvent']:
                        event['performingEvent']['individualPerformances'] = []
                    
                    show['sectionsOrActs'] = sections_or_acts
                    
                    event['performingEvent']['individualPerformances'].append(show)
                    logger.info(f"已将节目 '{show_name}' 添加到事件 '{matched_event_name}'")
                    print(f"已将节目 '{show_name}' 添加到事件 '{matched_event_name}'")
                    break
        else:
            logger.warning(f"无法为节目 '{show_name}' 找到匹配的事件")
            print(f"警告: 无法为节目 '{show_name}' 找到匹配的事件")

    for event in events:
        event['performingEvent']['individualPerformances'] = {
            'content': event['performingEvent'].get('individualPerformances', []),
            'metadata': {
                "model_name": "deepseek-chat",  # 假设使用deepseek-chat模型
                "timestamp": datetime.now().isoformat()
            }
        }

    logger.info(f"多事件处理完成。总输入tokens: {total_input_tokens}, 总输出tokens: {total_output_tokens}")
    print(f"多事件处理完成。总输入tokens: {total_input_tokens}, 总输出tokens: {total_output_tokens}")

    return events, total_input_tokens, total_output_tokens

def structured_shows_list(image_folder, logger):
    print(f"开始处理文件夹: {image_folder}")
    output_folder = os.path.join(image_folder, 'output')
    current_date = datetime.now().strftime('%Y%m%d')
    excel_file_path = os.path.join(output_folder, f'results_{current_date}.xlsx')
    
    print(f"读取Excel文件: {excel_file_path}")
    df = pd.read_excel(excel_file_path)

    new_columns = ['输入token-总2', '输出token-总2', '演出节目单']
    for col in new_columns:
        if col not in df.columns:
            df[col] = pd.NA

    processed_files = 0

    for i, row in df.iterrows():
        file_name = row['文件名']
        performing_events = json.loads(row['演出事件']) if isinstance(row['演出事件'], str) else row['演出事件']
        shows_list = row['节目清单列表']

        print(f"\n处理文件: {file_name}, Excel行: {i+1}")

        try:
            shows_list_json = json.loads(shows_list)
            if shows_list_json == {"individualPerformances": []}:
                df.loc[i, '演出节目单'] = row['演出事件']
                df.loc[i, '输入token-总2'] = row['输入token-总1']
                df.loc[i, '输出token-总2'] = row['输出token-总1']
                logger.info(f"{file_name}，Excel 第 {i+1} 行跳过处理，直接复制演出事件到演出节目单")
                print(f"{file_name}，Excel 第 {i+1} 行跳过处理，直接复制演出事件到演出节目单")
                df.to_excel(excel_file_path, index=False)
                print(f"Excel文件已更新: {excel_file_path}")
                processed_files += 1
                continue
            elif pd.notna(row['演出节目单']):
                logger.info(f"{file_name}，Excel 第 {i+1} 行跳过处理")
                print(f"{file_name}，Excel 第 {i+1} 行跳过处理")
                continue
        except json.JSONDecodeError:
            logger.warning(f"无法解析节目清单列表: {shows_list}")
            print(f"警告: 无法解析节目清单列表: {shows_list}")
            continue

        performing_events = [performing_events] if not isinstance(performing_events, list) else performing_events

        md_file_path = os.path.join(output_folder, f'{file_name}_ocr_1_final_result.md')
        
        if len(performing_events) > 1:
            logger.info(f"{file_name}，Excel 第 {i+1} 行是多事件，开始处理")
            print(f"{file_name}，Excel 第 {i+1} 行是多事件，开始处理")
            
            result, input_tokens, output_tokens = process_multi_events(performing_events, shows_list, md_file_path, logger)
        else:
            logger.info(f"{file_name}，Excel 第 {i+1} 行是单事件，开始处理")
            print(f"{file_name}，Excel 第 {i+1} 行是单事件，开始处理")
            
            event = performing_events[0]
            logger.info(f"处理事件: {event['performingEvent']['name']}")
            print(f"处理事件: {event['performingEvent']['name']}")
            result, input_tokens, output_tokens = process_single_event(event, shows_list, md_file_path, logger)

        df.loc[i, '输入token-总2'] = df.loc[i, '输入token-总1'] + input_tokens
        df.loc[i, '输出token-总2'] = df.loc[i, '输出token-总1'] + output_tokens
        df.loc[i, '演出节目单'] = json.dumps(result, ensure_ascii=False)
        
        print(f"更新Excel: 输入token-总2={df.loc[i, '输入token-总2']}, 输出token-总2={df.loc[i, '输出token-总2']}")
        df.to_excel(excel_file_path, index=False)
        print(f"Excel文件已更新: {excel_file_path}")

        processed_files += 1

    if processed_files > 0:
        logger.info(f"所有文件处理完成，结果已保存到 {excel_file_path}")
        print(f"所有文件处理完成，结果已保存到 {excel_file_path}")
    else:
        logger.info("没有处理任何文件")
        print("没有处理任何文件")


# if __name__ == "__main__":
#     image_folder = "path/to/your/image/folder"
#     logger = None  # 假设你有一个logger对象
#     structured_shows_list(image_folder, logger)
