from dotenv import load_dotenv
import os
import tools.token_counter as token_counter
import tools.prompts as prompts
import tools.llm_requestion as llm

# 加载 .env 文件中的环境变量
load_dotenv()

def add_spaces_to_text(result, logger):
    user_prompt = prompts.user_prompts["add_spaces_user_prompt"]
    system_prompt = prompts.system_prompts["add_spaces_system_prompt"]

    result += user_prompt
    token_text = system_prompt + result

    # 计算token数量
    token_count = token_counter.count_tokens(token_text )
    
    print(f"------------------实体对象间添加空格区分-----------------------------")
    print(f"Token数量: {token_count}")

    # 定义token阈值
    token_threshold_32k = 32768  # 32k token 的阈值
    token_threshold_128k = 131072  # 128k token 的阈值

    # 根据token数量选择模型配置
    if token_count <= token_threshold_32k:
        base_url = os.getenv("OneAPI_API_URL")
        api_key = os.getenv("OneAPI_API_KEY")
        model_name = "deepseek-Chat"
    elif token_count <= token_threshold_128k:
        base_url = os.getenv("Doubao_API_URL")
        api_key = os.getenv("Doubao_API_KEY")
        model_name = "ep-20240814153435-rmdkh"
    else:
        print(f"-----------------------------------------------")
        print("文本的token数量超过了128k模型的限制")
        logger.info("文本的token数量超过了128k模型的限制")
        return None

    print(f"-----------------------------------------------")
    print(f"调用的模型是{model_name}")

    result = llm.send_request(base_url, api_key, model_name, result, logger, system_prompt)
    return result