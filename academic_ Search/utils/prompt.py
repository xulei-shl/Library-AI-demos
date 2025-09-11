from langfuse import Langfuse
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union

class ConfigSource(Enum):
    DIRECT = "local"
    LANGFUSE = "langfuse"

class PromptType(Enum):
    SYSTEM = "system"
    USER = "user"

@dataclass
class LLMConfig:
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None

@dataclass
class PromptConfig:
    content: Optional[str] = None
    prompt_type: PromptType = PromptType.SYSTEM
    llm_config: Optional[LLMConfig] = None
    langfuse_prompt: Any = None

def get_prompt(
    prompt_name: Optional[str] = None,
    prompt_content: Optional[str] = None,
    prompt_type: PromptType = PromptType.SYSTEM,
    prompt_source: ConfigSource = ConfigSource.LANGFUSE,
    config_source: ConfigSource = ConfigSource.LANGFUSE,
    prompt_variables: Optional[Dict[str, Any]] = None,
    prompt_label: Optional[str] = None,
) -> PromptConfig:
    """获取提示词及相关配置"""
    # 移除所有类型转换逻辑，直接使用枚举类型
    result = PromptConfig(prompt_type=prompt_type)
    
    # 处理提示词内容
    if prompt_source == ConfigSource.DIRECT:
        result.content = prompt_content
    elif prompt_source == ConfigSource.LANGFUSE and prompt_name:
        try:
            langfuse = Langfuse()
            # 根据是否指定 label 调用不同的方法
            if prompt_label is not None:
                prompt = langfuse.get_prompt(prompt_name, label=prompt_label)
            else:
                prompt = langfuse.get_prompt(prompt_name)
            result.langfuse_prompt = prompt
            
            # 如果有变量，使用compile
            if prompt_variables:
                result.content = prompt.compile(**prompt_variables)
            else:
                result.content = prompt.compile()
            
            # 打印提示词前30个字符
            if result.content:
                preview = result.content[:30] + ('...' if len(result.content) > 30 else '')
                print(f"获取到提示词内容(前30字符): {preview}")
                
            # 如果是Langfuse配置源，获取模型配置
            if config_source == ConfigSource.LANGFUSE:
                if hasattr(prompt, 'config'):
                    config = prompt.config
                    result.llm_config = LLMConfig(
                        model_name=config.get('model'),
                        temperature=config.get('temperature'),
                        base_url=config.get('base_url'),
                        api_key=config.get('api_key')
                    )
                    # 打印模型配置(敏感信息部分隐藏)
                    if result.llm_config:
                        print("\n=== 获取到模型配置 ===")
                        print(f"模型名称: {result.llm_config.model_name}")
                        print(f"温度参数: {result.llm_config.temperature}")
                        print(f"API地址: {result.llm_config.base_url}")
                        if result.llm_config.api_key:
                            masked_key = result.llm_config.api_key[:3] + '*' * (len(result.llm_config.api_key)-6) + result.llm_config.api_key[-3:]
                            print(f"API密钥: {masked_key}")
                        print("=========================\n")
        except Exception as e:
            print(f"Langfuse提示词获取失败: {e}")
            raise SystemExit(f"错误: 无法从Langfuse获取提示词 '{prompt_name}'，程序终止")  # 新增：直接退出程序
            
    return result