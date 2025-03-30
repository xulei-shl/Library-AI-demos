from dotenv import load_dotenv
load_dotenv()
import os
from langfuse.openai import OpenAI
from langfuse.decorators import observe
from langfuse import Langfuse
import time
from functools import wraps
import tenacity
from typing import Dict, Any, Optional
from utils.prompt import get_system_prompt

# 环境变量设置
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv('LANGFUSE_SECRET_KEY')
os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv('LANGFUSE_PUBLIC_KEY')
os.environ["LANGFUSE_HOST"] = os.getenv('LANGFUSE_HOST')

# 定义重试装饰器，支持多级备用配置和指数退避重试机制
# 定义常量配置
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_INITIAL_WAIT = 1
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL_NAME = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_SYSTEM_PROMPT = "最大算力"

def retry_with_fallback(max_attempts: int = DEFAULT_MAX_ATTEMPTS, initial_wait: float = DEFAULT_INITIAL_WAIT):
    """
    提供重试和备用配置切换功能的装饰器工厂函数
    
    功能特点:
    1. 支持多级备用配置自动切换
    2. 实现指数退避重试策略
    3. 保留原始参数，仅更新必要的API配置
    4. 详细的错误日志记录和状态跟踪
    
    Args:
        max_attempts (int): 最大重试次数（包括首次尝试），默认为 DEFAULT_MAX_ATTEMPTS
        initial_wait (float): 首次重试等待时间（秒），后续等待时间将按指数增长，默认为 DEFAULT_INITIAL_WAIT
    
    Returns:
        decorator: 返回一个装饰器函数，用于装饰需要重试功能的函数
    
    使用示例:
        @retry_with_fallback(max_attempts=3, initial_wait=1)
        def api_call_function():
            # 函数实现
            pass
    """
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            last_exception = None
            original_kwargs = kwargs.copy()  # 保存原始参数
            
            # 将备用配置移到函数内部，便于维护
            fallback_configs = [
                {
                    'base_url': os.getenv('FALLBACK_API_BASE_1'),
                    'api_key': os.getenv('FALLBACK_API_KEY_1'),
                    'model_name': 'fallback-model-1'
                },
                {
                    'base_url': os.getenv('FALLBACK_API_BASE_2'),
                    'api_key': os.getenv('FALLBACK_API_KEY_2'),
                    'model_name': 'fallback-model-2'
                }
            ]
            
            while attempts <= max_attempts:
                try:
                    if attempts == 0:
                        return func(*args, **kwargs)
                    else:
                        fallback_idx = min(attempts - 1, len(fallback_configs) - 1)
                        fallback = fallback_configs[fallback_idx]
                        
                        # 仅更新API相关配置，保留其他原始参数
                        modified_kwargs = original_kwargs.copy()
                        for key in ['base_url', 'api_key', 'model_name']:
                            if key not in original_kwargs or original_kwargs[key] is None:
                                modified_kwargs[key] = fallback[key]
                        
                        print(f"\n=== 第{attempts}次重试：切换到备用配置 {fallback_idx + 1} ===")
                        print(f"使用模型: {modified_kwargs.get('model_name')}")
                        return func(*args, **modified_kwargs)
                
                except Exception as e:
                    last_exception = e
                    attempts += 1
                    if attempts <= max_attempts:
                        wait_time = initial_wait * (2 ** (attempts - 1))
                        print(f"\n=== 错误类型: {type(e).__name__} ===")
                        print(f"=== 错误信息: {str(e)} ===")
                        print(f"=== 等待 {wait_time} 秒后进行第 {attempts} 次重试... ===")
                        time.sleep(wait_time)
            
            print(f"\n=== 重试失败 ===")
            print(f"最大重试次数: {max_attempts}")
            print(f"最后错误类型: {type(last_exception).__name__}")
            print(f"错误信息: {str(last_exception)}")
            return None
        return wrapper
    return decorator

@observe()
@retry_with_fallback()
def get_llm_response(
    user_prompt: str,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str = None,
    model_name: str = DEFAULT_MODEL_NAME,
    system_prompt: str = None,
    use_langfuse_prompt: bool = True,
    temperature: float = DEFAULT_TEMPERATURE,
    name: str = None,
    tags: list = None,
    metadata: dict = None,
    prompt_name: str = DEFAULT_SYSTEM_PROMPT,
):
    """
    使用 LLM 生成响应，并通过 Langfuse 进行监控
    
    参数优先级说明(从高到低):
    - model_name/temperature/base_url/api_key: 1.显式传入值 > 2.本地提示词config > 3.Langfuse提示词config(当use_langfuse_prompt=True) > 4.函数默认值
    - system_prompt: 1.显式传入值 > 2.本地提示词 > 3.Langfuse提示词(当use_langfuse_prompt=True) > 4.None
    
    特别说明，重试时的参数覆盖规则：
    - 本地提示词或Langfuse提示词中的配置（model_name/temperature/base_url/api_key）仅在首次调用时生效
    - 重试时会使用fallback_configs中的配置覆盖非显式参数
    - 系统提示词内容（final_system_prompt）在重试过程中保持不变

    Args:
        user_prompt (str): 用户输入的提示词
        base_url (str): API 基础 URL
        api_key (str): API 密钥，如果为 None 则从环境变量获取
        model_name (str): 模型名称
        system_prompt (str): 系统提示词，用于直接在调用时传入
        use_langfuse_prompt (bool): 是否使用 Langfuse prompt，默认为 True
        temperature (float): 采样温度，控制输出的随机性，默认为 0.7
        name (str): 调用标识名称，默认为 None
        tags (list): 标签列表，用于追踪和分类请求，默认为 None
        metadata (dict): 元数据字典，用于存储额外信息，默认为 None
        prompt_name (str): 提示词配置名称，用于从本地或Langfuse获取提示词，默认为"最大算力"
    """
    # 获取 API key
    if api_key is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # 获取 system prompt 及相关配置
    prompt_data = get_system_prompt(
        prompt_name=prompt_name,
        system_prompt=system_prompt,
        use_langfuse_prompt=use_langfuse_prompt
    )
    
    # 更新配置，保持原有优先级
    final_system_prompt = prompt_data['system_prompt']
    if prompt_data['model_name']:
        model_name = prompt_data['model_name']
    if prompt_data['temperature']:
        temperature = prompt_data['temperature']
    if prompt_data['base_url']:
        base_url = prompt_data['base_url']
    if prompt_data['api_key']:
        api_key = prompt_data['api_key']

    # 初始化客户端
    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )
    
    try:
        messages = [{"role": "user", "content": user_prompt}]
        if final_system_prompt:
            messages.insert(0, {"role": "system", "content": final_system_prompt})
            
        # 增加请求信息日志
        print(f"\n=== 发送请求 ===")
        
        try:
            completion = client.chat.completions.create(
                model=model_name,
                name=f"{name}-{model_name}" if name is not None else model_name,
                messages=messages,
                temperature=temperature,
                tags=tags if tags is not None else [],
                metadata=metadata if metadata is not None else {},
                langfuse_prompt=prompt_data['prompt']  # 直接使用完整的prompt对象
            )
            # 添加成功日志
            print(f"\n=== 请求成功 ===")
            return completion
            
        except Exception as e:
            if not use_langfuse_prompt and "UpdateGenerationBody" in str(e):
                return e.args[0] if hasattr(e, 'args') and e.args else None
            raise

    except Exception as e:
        print(f"\n=== API调用错误 ===")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        raise

# 将测试代码移到 if __name__ == "__main__": 块中
if __name__ == "__main__":
    # 使用函数示例
    user_question = "什么是图像多模态大语言模型？"

    # 示例1：使用Langfuse提示词配置
    response = get_llm_response(
        user_prompt=user_question,
        prompt_name="翻译成英文",  # Langfuse中的提示词名称
    )

    # # 示例2：使用本地提示词配置
    # response = get_llm_response(
    #     user_prompt=user_question,
    #     # base_url=os.getenv('ONEAPI_API_BASE'),
    #     # api_key=os.getenv('ONEAPI_API_KEY'),
    #     # model_name="qwen",    
    #     prompt_name="翻译成英文",  # 使用本地Python模块中定义的提示词
    #     use_langfuse_prompt=False  # 禁用Langfuse提示词，使用本地提示词
    # )

    # # 示例3：使用自定义系统提示词
    # response = get_llm_response(
    #     user_prompt=user_question,
    #     system_prompt="你是一个专业的Python教程助手",  # 直接指定系统提示词
    #     use_langfuse_prompt=False  # 禁用提示词配置系统
    # )

    # # 示例4：使用完全自定义的API配置
    # response = get_llm_response(
    #     user_prompt=user_question,
    #     base_url=os.getenv('ONEAPI_API_BASE'),
    #     api_key=os.getenv('ONEAPI_API_KEY'),
    #     model_name="qwen",
    #     temperature=0.7,
    #     name="测试",
    #     tags=["Literature Search", "deepsearch"],
    #     metadata={"project": "cnki"},
    #     use_langfuse_prompt=False  # 禁用提示词配置系统
    # )

    if response:
        print(response.choices[0].message.content)