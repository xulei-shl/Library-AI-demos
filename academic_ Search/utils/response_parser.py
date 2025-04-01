import re
from typing import Dict

def parse_llm_response(content: str) -> Dict[str, str]:
    """
    解析LLM返回的响应内容，提取思考过程和回答内容
    
    Args:
        content (str): LLM返回的原始响应文本
        
    Returns:
        Dict[str, str]: 包含思考过程和回答的字典
    """
    think_pattern = r'<think>(.*?)</think>'
    think_match = re.search(think_pattern, content, re.DOTALL)
    
    if think_match:
        thinking = think_match.group(1).strip()
        answer = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()
        return {
            "thinking": thinking,
            "answer": answer
        }
    else:
        return {
            "thinking": "",
            "answer": content.strip()
        }