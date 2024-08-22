import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import shows_list_optimizer
import json

load_dotenv()

def extract_json_content(result):
    if '```json' in result:
        json_start = result.find('```json') + len('```json')
        json_end = result.find('```', json_start)
        return result[json_start:json_end].strip()
    return result

def process_file(file_path, logger, prompt_key, total_token_count, total_output_token_count):
    with open(file_path, "r", encoding="utf-8") as file:
        md_content = file.read()

    result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
        md_content, logger, prompt_key=prompt_key
    )
    total_token_count += token_count
    total_output_token_count += output_token_count

    print(f"\n----------------节目单明细初步提取结果----------------------------\n")
    print(result)
    logger.info(f"节目单明细初步提取: {result}")

    return result, total_token_count, total_output_token_count

def merging_shows_list(result, logger, total_token_count, total_output_token_count):
    processed_result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
        result, logger, prompt_key="merging_shows_list_user_prompt"
    )
    total_token_count += token_count
    total_output_token_count += output_token_count

    print(f"\n----------------多事件演出节目单合并整理----------------------------\n")
    print(processed_result)
    logger.info(f"多事件演出节目单合并整理: {processed_result}")

    return processed_result, total_token_count, total_output_token_count


def preprocess_shows_list(result, logger, total_token_count, total_output_token_count):
    print(f"\n----------------开始判断是否是节目单明细----------------------------\n")
    if result != '{"individualPerformances": []}':
        processed_result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
            result, logger, prompt_key="shows_list_judgment_user_prompt"
        )
        total_token_count += token_count
        total_output_token_count += output_token_count
        
        print(f"\n----------------是否是节目单明细----------------------------\n")
        print(processed_result)
        logger.info(f"是否是节目单信息列表判断结果: {processed_result}")

        # 解析 JSON 格式的返回结果
        json_content = result[result.find('```json') + 7:result.find('```', result.find('```json') + 7)].strip() if '```json' in result else result
        processed_result_json = json.loads(json_content)
        judgment_result = processed_result_json.get("result", "")

        if judgment_result == "部分是":
            processed_result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
                result, logger, prompt_key="shows_list_extractor_user_prompt"
            )
            total_token_count += token_count
            total_output_token_count += output_token_count
            print(f"\n----------------部分节目单明细提取结果----------------------------\n")
            print(processed_result)
            logger.info(f"部分节目单明细提取结果: {processed_result}")
            result = processed_result
        elif judgment_result == "否":
            result = '{"individualPerformances": []}'
            return result, total_token_count, total_output_token_count
        elif judgment_result == "是":
            # 继续传递原始的 result
            pass

    json_content = result[result.find('```json') + 7:result.find('```', result.find('```json') + 7)].strip() if '```json' in result else result
    
    # 移除了对 is_multiple_events 的判断，现在对所有情况都进行演职人员格式化
    data = json.loads(json_content)
  #新版是传递一个个json节点组处理，而非整个json，效果不好
    # if any(item.get('castDescription') for item in data.get('individualPerformances', []) if item.get('castDescription') is not None):
    #     print(f"\n----------------开始演职人员格式化----------------------------\n")
    #     logger.info("开始演职人员格式化")
        
    #     # Process each performance in the individualPerformances list
    #     for i, performance in enumerate(data['individualPerformances']):
    #         # Only process performances with a castDescription
    #         if performance.get('castDescription'):
    #             # Convert the single performance to JSON string
    #             performance_json = json.dumps({'individualPerformances': [performance]})
                
    #             print(f"\n----------------处理第 {i+1} 个演出----------------------------\n")
    #             logger.info(f"处理第 {i+1} 个演出")
                
    #             # Process the single performance
    #             processed_result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
    #                 performance_json, logger, prompt_key="add_spaces_user_prompt"
    #             )
    #             total_token_count += token_count
    #             total_output_token_count += output_token_count
                
    #             # Parse the processed result and update the original data
    #             processed_data = json.loads(processed_result)
    #             if processed_data['individualPerformances']:
    #                 data['individualPerformances'][i] = processed_data['individualPerformances'][0]
                
    #             print(f"\n----------------第 {i+1} 个演出处理结果----------------------------\n")
    #             print(json.dumps(data['individualPerformances'][i], ensure_ascii=False, indent=2))
    #             logger.info(f"第 {i+1} 个演出处理结果: {json.dumps(data['individualPerformances'][i], ensure_ascii=False)}")
    # else:
    #     print(f"\n----------------没有需要格式化的演职人员信息----------------------------\n")
    #     logger.info("没有需要格式化的演职人员信息")

    # # Convert the final result back to JSON string
    # final_result = json.dumps(data, ensure_ascii=False, indent=2)
    
    # return final_result, total_token_count, total_output_token_count

    if any(item.get('castDescription') for item in data.get('individualPerformances', []) if item.get('castDescription') is not None):
        print(f"\n----------------开始演职人员格式化----------------------------\n")
        processed_result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
            result, logger, prompt_key="add_spaces_user_prompt"
        )
        total_token_count += token_count
        total_output_token_count += output_token_count
        print(f"\n----------------演职人员格式化优化结果----------------------------\n")
        print(processed_result)
        logger.info(f"演职人员格式化优化结果: {processed_result}")
        result = processed_result

    json_content = result[result.find('```json') + 7:result.find('```', result.find('```json') + 7)].strip() if '```json' in result else result
    return json_content, total_token_count, total_output_token_count

# 新版是传递一个个json节点组处理，而非整个json。但判断不准确
def preprocess_shows_list_new(result, logger, total_token_count, total_output_token_count):
    if result == '{"individualPerformances": []}':
        return result, total_token_count, total_output_token_count

    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        logger.error(f"无法解析JSON: {result}")
        print(f"\n错误: 无法解析JSON: {result}\n")
        return result, total_token_count, total_output_token_count

    performances = data.get('individualPerformances', [])
    updated_performances = []

    print(f"\n----------------开始判断是否是节目单明细----------------------------\n")
    for performance in performances:
        performance_json = json.dumps(performance)
        processed_result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
            performance_json, logger, prompt_key="shows_list_judgment_user_prompt"
        )
        total_token_count += token_count
        total_output_token_count += output_token_count
        
        print(f"\n----------------是否是节目单明细----------------------------\n")
        print(processed_result)
        logger.info(f"是否是节目单信息列表判断结果: {processed_result}")

        try:
            judgment_result = json.loads(processed_result)
            if judgment_result.get("result") == "是":
                updated_performances.append(performance)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in judgment result: {processed_result}")

    data['individualPerformances'] = updated_performances

    if any(item.get('castDescription') for item in data.get('individualPerformances', []) if item.get('castDescription') is not None):
        print(f"\n----------------开始演职人员格式化----------------------------\n")
        for i, performance in enumerate(data['individualPerformances']):
            if performance.get('castDescription'):
                performance_json = json.dumps(performance)
                processed_result, token_count, output_token_count = shows_list_optimizer.optimize_shows_list(
                    performance_json, logger, prompt_key="add_spaces_user_prompt"
                )
                total_token_count += token_count
                total_output_token_count += output_token_count
                
                try:
                    updated_performance = json.loads(processed_result)
                    data['individualPerformances'][i] = updated_performance
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in formatted result: {processed_result}")

        print(f"\n----------------演职人员格式化优化结果----------------------------\n")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info(f"演职人员格式化优化结果: {json.dumps(data, ensure_ascii=False)}")

    return json.dumps(data, ensure_ascii=False), total_token_count, total_output_token_count

def pre_shows_list(image_folder, logger):
    print(f"开始处理文件夹: {image_folder}")
    output_folder = os.path.join(image_folder, 'output')
    current_date = datetime.now().strftime('%Y%m%d')
    excel_file_path = os.path.join(output_folder, f'results_{current_date}.xlsx')
    
    print(f"读取Excel文件: {excel_file_path}")
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        logger.error(f"无法读取Excel文件: {excel_file_path}. 错误: {str(e)}")
        print(f"错误: 无法读取Excel文件: {excel_file_path}")
        return

    # 检查并创建必要的列
    required_columns = ['文件名', '演出事件', '节目清单列表', '输入token', '输出token']
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
            logger.warning(f"Excel文件中缺少'{col}'列,已自动创建")
            print(f"警告: Excel文件中缺少'{col}'列,已自动创建")

    for i, row in df.iterrows():
        file_name = row['文件名']
        performing_events = row['演出事件']

        print(f"\n----------------开始节目单提取的预处理----------------------------\n")

        if '节目清单列表' in df.columns and pd.notna(row['节目清单列表']):
            print(f"{file_name}，Excel 第 {i+1} 行已经处理过，跳过")
            logger.info(f"{file_name}，Excel 第 {i+1} 行已经处理过，跳过")
            continue

        performing_events = json.loads(performing_events) if isinstance(performing_events, str) else performing_events
        performing_events = [performing_events] if not isinstance(performing_events, list) else performing_events
        is_multiple_events = len(performing_events) > 1

        ocr_file_path = os.path.join(output_folder, f'{file_name}_ocr_1_final_result.md')
        md_file_path = os.path.join(output_folder, f'{file_name}_md_final_result.md')

        print(f"\n----------------开始处理文件 {file_name}，Excel 第 {i+1} 行----------------------------\n")
        logger.info(f"开始处理文件 {file_name}，Excel 第 {i+1} 行")

        total_token_count = total_output_token_count = 0

        if is_multiple_events:
            print(f"处理多事件演出节目单")
            logger.info(f"处理多事件演出节目单")
            print(f"\n----------------开始第一次的节目单提取--------------\n")
            logger.info(f"开始第一次的节目单提取")
            result1, total_token_count, total_output_token_count = process_file(ocr_file_path, logger, "shows_list_stepone_prompt", total_token_count, total_output_token_count)
            print(f"\n----------------开始第二次的节目单提取--------------\n")
            logger.info(f"开始第二次的节目单提取")
            result2, total_token_count, total_output_token_count = process_file(md_file_path, logger, "shows_list_stepone_prompt", total_token_count, total_output_token_count)
            merged_result = f"## 第一次识别的节目当信息：\n{result1}\n\n## 第二次识别的节目当信息：\n{result2}"
            print(f"\n----------------对两次结果进行合并整理--------------\n")
            logger.info(f"对两次结果进行合并整理")
            merged_result, total_token_count, total_output_token_count = merging_shows_list(merged_result, logger, total_token_count, total_output_token_count)

        else:
            print(f"处理单个事件演出节目单")
            logger.info(f"处理单个事件演出节目单")
            merged_result, total_token_count, total_output_token_count = process_file(ocr_file_path, logger, "shows_list_stepone_prompt", total_token_count, total_output_token_count)

        merged_result = extract_json_content(merged_result)
        final_result, total_token_count, total_output_token_count = preprocess_shows_list(merged_result, logger, total_token_count, total_output_token_count)

        df.at[i, '输入token-总1'] = row['输入token'] + total_token_count
        df.at[i, '输出token-总1'] = row['输出token'] + total_output_token_count
        df.at[i, '节目清单列表'] = extract_json_content(final_result)

        df.to_excel(excel_file_path, index=False)
        print(f"已保存文件 {file_name} 的处理结果到 Excel")
        logger.info(f"已保存文件 {file_name} 的处理结果到 Excel")

    print("所有文件处理完成")
    logger.info("所有文件处理完成")

# if __name__ == "__main__":
#     image_folder = r"E:\scripts\jiemudan\2"
#     logger = None
#     shows_list(image_folder, logger)
