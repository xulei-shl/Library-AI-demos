import os
import pandas as pd
from datetime import datetime
import tools.prompts as prompts
from tools.metadata_extractor import extract_metadata
import json
import tools.festivals_info_processor as json_processor
from tools.llm_json_extractor import extract_json_content


def festivals_metadata(image_folder, logger):
    output_folder = os.path.join(image_folder, 'output')
    current_date = datetime.now().strftime('%Y%m%d')
    excel_file_path = os.path.join(output_folder, f'results_{current_date}.xlsx')

    # 尝试读取已有的 Excel 文件
    if os.path.exists(excel_file_path):
        df = pd.read_excel(excel_file_path)
    else:
        df = pd.DataFrame(columns=['文件名', '输入token', '输出token'])

    prompts_and_keywords = [
        ("festivals_system_prompt", "festivals_user_prompt", "演出事件"),
        #("shows_list_system_prompt", "shows_list_user_prompt", "演出节目"),
        # 添加更多的 system_prompt 和 user_prompt 对
    ]

    for filename in os.listdir(output_folder):
        if filename.endswith('_ocr_1_final_result.md'):
            md_file_path = os.path.join(output_folder, filename)
            file_prefix = filename.split('_ocr_1_final_result.md')[0]

            # 找到对应的 _ocr_final_result.md 文件
            description_md_file = os.path.join(output_folder, f"{file_prefix}_md_final_result.md")

            print(f"\n-----------------开始演出(季、系列)信息提取-------------------------\n")
            print(filename)
            logger.info(f"正在处理文件: {filename}")

            # 检查文件是否已经处理过
            if file_prefix in df['文件名'].values and pd.notna(df.loc[df['文件名'] == file_prefix, '演出事件'].values[0]):
                print(f"文件 {filename} 已经处理过，跳过")
                logger.info(f"文件 {filename} 已经处理过，跳过")
                continue

            df.loc[len(df)] = {'文件名': file_prefix, '输入token': 0, '输出token': 0}

            total_token_count = 0  # 用于跟踪该文件的总 token 数量
            total_output_token_count = 0  # 用于跟踪该文件的总输出 token 数量

            for system_prompt_key, keyword, column_name in prompts_and_keywords:
                system_prompt = prompts.system_prompts.get(system_prompt_key, "")
                user_prompt = prompts.user_prompts.get(keyword, "")

                if not system_prompt or not user_prompt:
                    print(f"\n------------------------------------------\n")
                    print(f"未找到 {system_prompt_key} 或 {keyword} 对应的 prompts 文本")
                    logger.error(f"未找到 {system_prompt_key} 或 {keyword} 对应的 prompts 文本")
                    continue

                result, token_count, output_token_count = extract_metadata(md_file_path, logger, system_prompt, user_prompt)
                total_token_count += token_count  # 累加 token 数量
                total_output_token_count += output_token_count  # 累加输出 token 数量

                # 检查 result 中是否包含 ```json 字符串
                json_content = extract_json_content(result)

                print(f"\n文件 {filename} 的处理结果:\n")
                print(json_content)
                logger.info(f"文件 {filename} 的处理结果:\n{json_content}")

                if column_name not in df.columns:
                    df[column_name] = None

                try:
                    json_result = json.loads(json_content)
                except json.JSONDecodeError:
                    logger.error(f"无法解析 JSON 结果: {json_content}")
                    continue

                if isinstance(json_result, list):
                    for item in json_result:
                        token_count, output_token_count = json_processor.process_item(item, description_md_file, logger)
                        total_token_count += token_count  # 累加 token 数量
                        total_output_token_count += output_token_count  # 累加输出 token 数量
                elif isinstance(json_result, dict):
                    token_count, output_token_count = json_processor.process_item(json_result, description_md_file, logger)
                    total_token_count += token_count  # 累加 token 数量
                    total_output_token_count += output_token_count  # 累加输出 token 数量

                readable_json = json.dumps(json_result, ensure_ascii=False, indent=4)
                df.loc[df['文件名'] == file_prefix, column_name] = readable_json

            # 将该文件的总 token 消耗和输出 token 数量存储到 DataFrame 中
            df.loc[df['文件名'] == file_prefix, '输入token'] = total_token_count
            df.loc[df['文件名'] == file_prefix, '输出token'] = total_output_token_count

    if not df.empty:
        # 确保 DataFrame 有表头
        df.to_excel(excel_file_path, index=False)

        print(f"结果已保存到 {excel_file_path}")
        logger.info(f"结果已保存到 {excel_file_path}")