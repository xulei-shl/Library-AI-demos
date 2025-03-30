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
    
    优先级逻辑:
        1. 优先使用直接传入的system_prompt参数(如果提供)
        2. 其次尝试从本地提示词获取(use_langfuse_prompt=False时)
        3. 最后尝试从Langfuse获取(use_langfuse_prompt=True时)
        4. 如果都未找到，返回的system_prompt为None
    """
    result = {
        'system_prompt': system_prompt,
        'model_name': None,
        'temperature': None,
        'base_url': None,
        'api_key': None
    }
    
    # 优先使用直接传入的提示词
    if system_prompt is not None:
        return result
        
    # 尝试从本地提示词获取
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
                    print(result['system_prompt'])
                    break
        except Exception as e:
            print(f"\n=== 本地提示词加载失败 ===")
            print(f"错误: {str(e)}")
    
    # 如果本地没有找到或使用Langfuse，尝试从Langfuse获取
    if result['system_prompt'] is None and use_langfuse_prompt:
        prompt = Langfuse().get_prompt(prompt_name)
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
        print(result['system_prompt'])
    
    return result