"""
JSON 修复工具
用于修复 LLM 输出中的常见 JSON 格式问题，包括：
1. 移除 fenced code block (```json ... ```)
2. 处理尾随的重复文本
3. 修复常见的 JSON 语法错误
"""

import json
import re
from typing import Optional, Dict, Any

def repair_json_output(txt: str) -> Optional[Dict[str, Any]]:
    """
    修复 LLM 输出的 JSON 格式问题
    
    Args:
        txt: LLM 原始输出文本
        
    Returns:
        修复后的 JSON 对象，如果修复失败则返回 None
    """
    if not txt:
        return None
        
    # 步骤1: 移除 fenced code block
    txt = _remove_fenced_code_blocks(txt)
    
    # 步骤2: 提取第一个有效的 JSON 块
    json_str = _extract_first_json(txt)
    if not json_str:
        return None
    
    # 步骤3: 尝试解析 JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 步骤4: 如果仍然失败，尝试修复常见问题
        fixed_json = _fix_common_json_issues(json_str)
        if fixed_json:
            try:
                return json.loads(fixed_json)
            except json.JSONDecodeError:
                return None
        return None

def _remove_fenced_code_blocks(txt: str) -> str:
    """移除 fenced code block 标记"""
    # 更健壮地移除所有位置的 ```json 和 ```（不局限于行首/行尾）
    txt = re.sub(r'```json', '', txt)
    txt = re.sub(r'```', '', txt)
    return txt.strip()

def _extract_first_json(txt: str) -> Optional[str]:
    """
    从文本中提取第一个有效的 JSON 块
    使用花括号平衡来找到完整的 JSON 对象
    """
    # 寻找第一个 {
    start_idx = txt.find('{')
    if start_idx == -1:
        return None
    
    # 使用计数器找到匹配的 }
    brace_count = 0
    in_string = False
    escape_next = False
    
    for i in range(start_idx, len(txt)):
        char = txt[i]
        
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # 找到完整的 JSON 对象
                    return txt[start_idx:i+1]
    
    return None

def _fix_common_json_issues(txt: str) -> Optional[str]:
    """修复常见的 JSON 语法问题"""
    try:
        # 移除 BOM 和零宽字符
        txt = txt.encode('utf-8').decode('utf-8-sig')
        txt = re.sub(r'[\u200B-\u200D\uFEFF]', '', txt)

        # 移除多余的空行（LLM经常生成带空行的JSON）
        txt = re.sub(r'\n\n+', '\n', txt)

        # 先处理引号问题：
        # 1) 将常见的中文/全角/排版引号统一为半角双引号 "
        # 2) 对位于中文语境中（两侧为中文或中文标点）出现的半角双引号进行转义，避免被 JSON 误判为字符串结束符
        #    示例： ... ，"剧联"根据 ... 需要变为 ... ，\"剧联\"根据 ...
        quote_map = {
            '“': '"',
            '”': '"',
            '＂': '"',
            '「': '"',
            '」': '"',
            '『': '"',
            '』': '"',
            '〝': '"',
            '〞': '"',
            '〟': '"',
        }
        for k, v in quote_map.items():
            txt = txt.replace(k, v)

        # 仅转义位于「中文或 ASCII 字母/数字」语境中的半角双引号，避免破坏 JSON 结构性引号
        # 例如：中文词语中的 "剧联"、"围剿" 等，或混合英文/数字的片段如 X"Y
        flank_pattern = r'(?<=[\u4e00-\u9fff\u3000-\u303F\uFF00-\uFFEFA-Za-z0-9])"(?=[\u4e00-\u9fff\u3000-\u303F\uFF00-\uFFEFA-Za-z0-9])'
        txt = re.sub(flank_pattern, r'\\"', txt)

        # 替换全角标点为半角（在处理引号之后，以免影响引号的语境判断）
        txt = txt.replace('：', ':')
        txt = txt.replace('，', ',')
        txt = txt.replace('（', '(')
        txt = txt.replace('）', ')')
        txt = txt.replace('【', '[')
        txt = txt.replace('】', ']')
        txt = txt.replace('｛', '{')
        txt = txt.replace('｝', '}')

        # 移除尾随的逗号
        txt = re.sub(r',(\s*[}\]])', r'\1', txt)

        # 修复缺少引号的键（更安全，只在对象/数组上下文中匹配键名）
        # 例如：{ key: value } 或 , key: value -> 替换为 { "key": value } / , "key": value
        # 该模式避免影响字符串内部的类似片段（如 "http://..."）
        txt = re.sub(r'([{\[,]\s*)([A-Za-z_][\w]*)\s*:', r'\1"\2":', txt)

        return txt
    except Exception:
        return None

def is_valid_json(txt: str) -> bool:
    """检查文本是否为有效的 JSON"""
    try:
        json.loads(txt)
        return True
    except (json.JSONDecodeError, TypeError):
        return False