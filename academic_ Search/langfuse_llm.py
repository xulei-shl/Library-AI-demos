from dotenv import load_dotenv
load_dotenv()
import os
from langfuse.openai import OpenAI
from langfuse.decorators import observe
from langfuse import Langfuse
import time
from functools import wraps
import tenacity
from typing import Dict, Any, Optional, Union
from utils.prompt import get_prompt, LLMConfig, ConfigSource, PromptType

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
DEFAULT_PROMPT = "最大算力"

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
    system_prompt: Optional[str] = None,
    prompt_name: Optional[str] = None,
    prompt_type: PromptType = PromptType.USER,
    config: Optional[LLMConfig] = None,
    prompt_source: ConfigSource = ConfigSource.LANGFUSE,
    config_source: ConfigSource = ConfigSource.LANGFUSE,
    name: Optional[str] = None,
    tags: Optional[list] = None,
    metadata: Optional[dict] = None,
    prompt_variables: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    使用大语言模型(LLM)生成响应，支持多种配置来源和提示词管理
    
    核心功能:
    - 支持从Langfuse或直接输入获取提示词和配置
    - 自动处理系统提示词和用户提示词
    - 支持提示词变量替换
    - 内置重试和备用配置切换机制
    
    参数说明:
        user_prompt (str): 用户输入的提示内容
        system_prompt (Optional[str]): 直接输入的系统提示词，当prompt_source=DIRECT时使用
        prompt_name (Optional[str]): 在Langfuse中注册的提示词名称
        prompt_type (PromptType): 提示词类型(USER/SYSTEM)，默认为USER
        config (Optional[LLMConfig]): 直接传入的LLM配置
        prompt_source (ConfigSource): 提示词来源(LANGFUSE/DIRECT)，默认为LANGFUSE
        config_source (ConfigSource): 配置来源(LANGFUSE/DIRECT)，默认为LANGFUSE
        name (Optional[str]): 为本次调用命名，用于追踪
        tags (Optional[list]): 标签列表，用于分类和过滤
        metadata (Optional[dict]): 元数据字典，用于记录额外信息
        prompt_variables (Optional[Dict[str, Any]]): 提示词变量替换字典
        
    返回:
        Any: LLM生成的响应对象，通常是OpenAI格式的Completion对象
        
    异常:
        会抛出LLM API调用过程中的异常，但会通过retry_with_fallback装饰器自动重试
        
    使用示例:
        # 使用Langfuse中的提示词配置
        response = get_llm_response(
            user_prompt="你好",
            prompt_name="问候模板",
            config_source=ConfigSource.LANGFUSE
        )
        
        # 直接使用系统提示词和自定义配置
        response = get_llm_response(
            user_prompt="解释量子计算",
            system_prompt="你是一位物理学教授",
            config=LLMConfig(model_name="gpt-4"),
            prompt_source=ConfigSource.DIRECT
        )
    """
    # 处理提示词变量
    variables = {"user_input": user_prompt}
    if prompt_variables:
        variables.update(prompt_variables)
    
    messages = []
    
    # 处理系统提示词
    if prompt_source == ConfigSource.DIRECT:
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
    elif prompt_name and prompt_type == PromptType.SYSTEM:
        try:  # 新增：捕获可能的SystemExit异常
            system_config = get_prompt(
                prompt_name=prompt_name,
                prompt_type=PromptType.SYSTEM,
                prompt_source=prompt_source,
                config_source=config_source
            )
            if system_config.content:
                messages.append({"role": "system", "content": system_config.content})
        except SystemExit as e:
            print(e)
            return None
    
    # 处理用户提示词
    if prompt_source == ConfigSource.DIRECT:
        messages.append({"role": "user", "content": user_prompt})
    elif prompt_name and prompt_type == PromptType.USER:
        try:  # 新增：捕获可能的SystemExit异常
            user_config = get_prompt(
                prompt_name=prompt_name,
                prompt_type=PromptType.USER,
                prompt_source=prompt_source,
                config_source=config_source,
                prompt_variables=variables
            )
            messages.append({"role": "user", "content": user_config.content or user_prompt})
        except SystemExit as e:
            print(e)
            return None
    else:
        messages.append({"role": "user", "content": user_prompt})
    
    # 确定最终使用的配置
    final_config = config or (
        user_config.llm_config if 'user_config' in locals() and user_config.llm_config else 
        (system_config.llm_config if 'system_config' in locals() and system_config.llm_config else None)
    ) or LLMConfig(
        model_name=DEFAULT_MODEL_NAME,
        temperature=DEFAULT_TEMPERATURE,
        base_url=DEFAULT_BASE_URL,
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )
    
    # 打印实际使用的配置信息
    print("\n=== 实际使用的模型配置 ===")
    print(f"模型名称: {final_config.model_name}")
    print(f"温度参数: {final_config.temperature}")
    print(f"API地址: {final_config.base_url}")
    if final_config.api_key:
        masked_key = final_config.api_key[:3] + '*' * (len(final_config.api_key)-6) + final_config.api_key[-3:]
        print(f"API密钥: {masked_key}")
    print("=========================\n")
    
    # 初始化客户端并调用API
    client = OpenAI(
        base_url=final_config.base_url,
        api_key=final_config.api_key
    )
    
    try:
        # 准备调用参数
        completion_params = {
            "model": final_config.model_name,
            "messages": messages,
            "temperature": final_config.temperature,
            "name": f"{name}-{final_config.model_name}" if name else final_config.model_name,
            "tags": tags or [],
            "metadata": metadata or {},
        }
        
        # 如果提示词来源是Langfuse，添加langfuse_prompt参数以便追踪
        if prompt_source == ConfigSource.LANGFUSE and prompt_name:
            # 获取当前使用的提示词对象
            langfuse_prompt_obj = None
            if prompt_type == PromptType.USER and 'user_config' in locals():
                langfuse_prompt_obj = user_config.langfuse_prompt
            elif prompt_type == PromptType.SYSTEM and 'system_config' in locals():
                langfuse_prompt_obj = system_config.langfuse_prompt
                
            # 如果成功获取到提示词对象，添加到参数中
            if langfuse_prompt_obj:
                completion_params["langfuse_prompt"] = langfuse_prompt_obj
        
        completion = client.chat.completions.create(**completion_params)
        return completion
    except Exception as e:
        if not isinstance(config_source, ConfigSource):
            config_source = ConfigSource(config_source)
        if config_source != ConfigSource.LANGFUSE and "UpdateGenerationBody" in str(e):
            return e.args[0] if hasattr(e, 'args') and e.args else None
        raise

# 测试代码更新
if __name__ == "__main__":
    user_question = "什么是图像多模态大语言模型？"

    # 示例1：使用Langfuse配置
    response = get_llm_response(
        user_prompt=user_question,
        prompt_name="翻译成英文",
        config_source=ConfigSource.LANGFUSE
    )

    # 示例2：直接传入配置（移除原来的LOCAL示例）
    response = get_llm_response(
        user_prompt=user_question,
        system_prompt="你是一个专业的Python教程助手",
        config=LLMConfig(
            model_name="qwen",
            temperature=0.7,
            base_url=os.getenv('ONEAPI_API_BASE'),
            api_key=os.getenv('ONEAPI_API_KEY')
        ),
        config_source=ConfigSource.DIRECT
    )

    if response:
        print(response.choices[0].message.content)