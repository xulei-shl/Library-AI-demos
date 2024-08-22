from dotenv import load_dotenv
import os
import tools.token_counter as token_counter
import tools.llm_requestion as llm
from datetime import datetime
import json

# 加载 .env 文件中的环境变量
load_dotenv()

def extract_metadata(md_file_path, logger, system_prompt, user_prompt):
    # 读取本地 MD 文件内容
    with open(md_file_path, "r", encoding="utf-8") as file:
        md_content = file.read()

    md_content += user_prompt

    token_text = system_prompt + md_content

    # 计算token数量
    token_count = token_counter.count_tokens(token_text)
    print(f"-----------------------------------------------")
    print(f"Token数量: {token_count}")
    logger.info(f"Token数量: {token_count}")
    print(f"-----------------------------------------------")
    print(f"开始提取 {md_file_path} 的元数据信息")    
    logger.info(f"开始提取 {md_file_path} 的元数据信息")

    # 定义token阈值
    token_threshold_32k = 32768  # 32k token 的阈值
    token_threshold_128k = 131072  # 128k token 的阈值

    # 根据token数量选择模型配置
    if token_count <= token_threshold_32k:
        base_url = os.getenv("OneAPI_API_URL")
        api_key = os.getenv("OneAPI_API_KEY")

        # base_url = os.getenv("DeepSeek_API_URL")
        # api_key = os.getenv("DeepSeek_API_KEY")
        model_name = "deepseek-chat"
    elif token_count <= token_threshold_128k:
        base_url = os.getenv("Doubao_API_URL")
        api_key = os.getenv("Doubao_API_KEY")
        model_name = "ep-20240814153435-rmdkh"
    else:
        print(f"-----------------------------------------------")
        print("文本的token数量超过了128k模型的限制")
        logger.info("文本的token数量超过了128k模型的限制")
        return None, token_count, 0

    print(f"-----------------------------------------------")
    print(f"调用的模型是{model_name}")
    logger.info(f"调用的模型是{model_name}")

    result, output_token_count = llm.send_request(base_url, api_key, model_name, md_content, logger, system_prompt, response_format={'type': 'json_object'})
    logger.info(f"元数据信息提取的结果: {result}") 
    
    # 添加 metadata 信息
    metadata = {
        "model_name": model_name,
        "timestamp": datetime.now().isoformat()
    }
    
    # 检查 result 中是否包含 ```json 字符串
    if '```json' in result:
        json_start = result.find('```json') + len('```json')
        json_end = result.find('```', json_start)
        json_content = result[json_start:json_end].strip()
    else:
        json_content = result    

    try:
        result_json = json.loads(json_content)
        
        # 处理单个演出事件的情况
        if isinstance(result_json, dict) and "performingEvent" in result_json:
            result_json["performingEvent"]["metadata"] = metadata
            result_json = [result_json]  # 将单个事件包装成列表
        # 处理多个演出事件的情况
        elif isinstance(result_json, list):
            for event in result_json:
                if "performingEvent" in event:
                    event["performingEvent"]["metadata"] = metadata
        else:
            raise ValueError("Unexpected JSON structure")
        
    except (json.JSONDecodeError, ValueError) as e:
        result_json = [{"error": str(e), "raw_content": json_content}]
    
    print(f"------------------元数据信息提取的结果-----------------------------")
    print(json.dumps(result_json, ensure_ascii=False, indent=4))
    logger.info(f"元数据信息提取的结果: {json.dumps(result_json, ensure_ascii=False, indent=4)}")
    return json.dumps(result_json, ensure_ascii=False), token_count, output_token_count