from langfuse import Langfuse
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from prompt.sys_prompt import SYSTEM_PROMPTS

def get_system_prompt(
    prompt_name: str = "最大算力",
    system_prompt: Optional[str] = None,
    use_langfuse_prompt: bool = True
) -> Dict[str, Any]:
    """
    获取系统提示词及相关配置
    
    参数:
        prompt_name (str): Langfuse中的提示词名称或本地提示词名称，默认为"最大算力"
        system_prompt (str): 自定义系统提示词，可选
        use_langfuse_prompt (bool): 是否使用Langfuse提示词，False时使用本地提示词
    
    返回:
        dict: 包含以下键的字典:
            - 'system_prompt': 最终系统提示词内容
            - 'model_name': 模型名称
            - 'temperature': 采样温度
            - 'base_url': API基础URL
            - 'api_key': API密钥
            - 'prompt': Langfuse prompt对象(仅当use_langfuse_prompt=True时)
    """
    result = {
        'system_prompt': system_prompt,
        'model_name': None,
        'temperature': None,
        'base_url': None,
        'api_key': None,
        'prompt': None  # 新增：存储Langfuse prompt对象
    }
    
    # 优先使用直接传入的提示词
    if system_prompt is not None:
        return result
        
    # 尝试从Langfuse获取（如果启用）
    if use_langfuse_prompt:
        try:
            langfuse = Langfuse()
            prompt = langfuse.get_prompt(prompt_name)
            result['prompt'] = prompt  # 保存完整的prompt对象用于追踪
            result['system_prompt'] = prompt.compile()
            
            if hasattr(prompt, 'config') and prompt.config:
                result.update({
                    'model_name': prompt.config.get('model'),
                    'temperature': prompt.config.get('temperature'),
                    'base_url': prompt.config.get('base_url'),
                    'api_key': prompt.config.get('api_key')
                })
                
                print("\n=== 从Langfuse提示词获取模型配置 ===")
                print(f"模型名称: {result['model_name']}")
                print(f"采样温度: {result['temperature']}")
                print(f"API地址: {result['base_url']}")
                if result['api_key'] and len(result['api_key']) > 8:
                    masked_key = f"{result['api_key'][:4]}...{result['api_key'][-4:]}"
                    print(f"API密钥: {masked_key}")
            
            print("\n=== 使用Langfuse提示词 ===")
            print(f"{result['system_prompt'][:50]}...")
            return result
            
        except Exception as e:
            print(f"\n=== Langfuse提示词获取失败，尝试使用本地提示词 ===")
            print(f"错误: {str(e)}")
            use_langfuse_prompt = False
    
    # 如果未启用Langfuse或Langfuse获取失败，尝试从本地提示词获取
    if not use_langfuse_prompt:
        try:
            for prompt in SYSTEM_PROMPTS:
                if prompt['name'] == prompt_name:
                    result['system_prompt'] = prompt['content']
                    if 'config' in prompt:
                        result.update({
                            'model_name': prompt['config'].get('model'),
                            'temperature': prompt['config'].get('temperature'),
                            'base_url': prompt['config'].get('base_url'),
                            'api_key': prompt['config'].get('api_key')
                        })
                    print("\n=== 使用本地提示词 ===")
                    print(f"提示词名称: {prompt_name}")
                    print(f"{result['system_prompt'][:50]}...")
                    return result
                    
        except Exception as e:
            print(f"\n=== 本地提示词加载失败 ===")
            print(f"错误: {str(e)}")
    
    return result