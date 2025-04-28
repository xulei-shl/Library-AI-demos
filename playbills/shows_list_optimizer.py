from openai import OpenAI
from dotenv import load_dotenv
import os
import tools.token_counter as token_counter
import tools.llm_requestion as llm
import tools.prompts as prompts



# 加载 .env 文件中的环境变量
load_dotenv()

def optimize_shows_list(result, logger, prompt_key):

    user_prompt = prompts.user_prompts[prompt_key]

    # 将 result 与 user_prompt 拼接在一起
    combined_prompt = f"{user_prompt}\n{result}"

    # 计算token数量
    token_count = token_counter.count_tokens(combined_prompt)

    print(f"\n--------------------------------------------\n")
    print(f"Token数量: {token_count}")

    logger.info(f"Tokens数量：{token_count}")
    logger.info(f"开始提取节目单信息")

    # 定义token阈值
    token_threshold_32k = 32768  # 32k token 的阈值
    token_threshold_128k = 131072  # 128k token 的阈值

    # 根据token数量选择模型配置
    if token_count <= token_threshold_32k:
        base_url = os.getenv("OneAPI_API_URL")
        api_key = os.getenv("OneAPI_API_KEY")
        model_name = "doubao-1-5-pro-32k-250115"
    elif token_count <= token_threshold_128k:
        base_url = os.getenv("OneAPI_API_URL")
        api_key = os.getenv("OneAPI_API_KEY")
        model_name = "doubao-1-5-pro-256k-250115"
    else:
        print(f"\n-----------------------------------------------\n")
        print("文本的token数量超过了128k模型的限制")
        logger.info("文本的token数量超过了128k模型的限制")
        return None, token_count, 0
    
    print(f"\n-----------------------------------------------\n")
    print(f"调用的模型是{model_name}")    
    logger.info(f"调用的模型是{model_name}")

    result, output_token_count = llm.send_request(base_url, api_key, model_name, combined_prompt, logger, response_format={'type': 'json_object'})
    
    return result, model_name, token_count, output_token_count

# 测试函数
# if __name__ == "__main__":
#     result = """
    
#     """
#     logger = None
#     md_result = optimize_shows_list(result, logger, prompt_key="add_spaces_user_prompt")
#     print(md_result)