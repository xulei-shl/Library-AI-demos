# 测试
# import sys
# import os
# sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

# from dotenv import load_dotenv
# import os
# import token_counter
# import llm_requestion as llm
# import prompts
# from datetime import datetime
# import json

from dotenv import load_dotenv
import os
import tools.token_counter as token_counter
import tools.llm_requestion as llm
import tools.prompts as prompts
import json

# 加载 .env 文件中的环境变量
load_dotenv()

def get_description(md_file_path, logger, name):
    user_prompt = prompts.user_prompts["festivals_description_user_prompt"]
    system_prompt = prompts.system_prompts["festivals_description_system_prompt"]

    # 读取本地 MD 文件内容
    with open(md_file_path, "r", encoding="utf-8") as file:
        md_content = file.read()

    # 合并 MD 文件内容、user_prompt 和提取的 name
    combined_prompt = f"{md_content}\n{user_prompt}\n{name}"

    # print(f"----------------{name} 的用户提示词-------------------------------")
    # print(combined_prompt)

    token_text = system_prompt + combined_prompt

    # 计算token数量
    token_count = token_counter.count_tokens(token_text)

    print(f"----------------开始提取 {name} 的描述信息-------------------------------")
    print(f"Token数量: {token_count}")
    logger.info(f"Tokens数量：{token_count}")
    logger.info(f"开始提取 {name} 的描述信息")

    # 定义token阈值
    token_threshold_32k = 32768  # 32k token 的阈值
    token_threshold_128k = 131072  # 128k token 的阈值

    # 根据token数量选择模型配置
    if token_count <= token_threshold_32k:
        base_url = os.getenv("OneAPI_API_URL")
        api_key = os.getenv("OneAPI_API_KEY")
        model_name = "doubao-1-5-lite-32k-250115"
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

    result, output_token_count = llm.send_request(base_url, api_key, model_name, combined_prompt, logger, system_prompt)
    # print(f"-----------------------------------------------")
    # print(f"描述信息提取的结果: {result}")    
    logger.info(f"描述信息提取的结果: {result}")

    # 如果 result 是 null，则返回 None
    if result is None:
        return None, token_count, 0

    # 直接将 result 转换为 JSON 格式
    json_content = json.dumps({"description": result}, ensure_ascii=False)

    print(f"------------------描述信息提取的结果-----------------------------")
    print(json.dumps(json.loads(json_content), ensure_ascii=False, indent=4))
    logger.info(f"描述信息提取的结果: {json.dumps(json.loads(json_content), ensure_ascii=False, indent=4)}")
    return json_content, token_count, output_token_count

#测试
# if __name__ == "__main__":
#     md_file_path = r"E:\scripts\jiemudan\1\output\BROTHER8530DN_006806_md_final_result.md"
#     logger = None
#     name = "上海徐汇燕萍京剧团"
#     get_description(md_file_path, logger, name)

