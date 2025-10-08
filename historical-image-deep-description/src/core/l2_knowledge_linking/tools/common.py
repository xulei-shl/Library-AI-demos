from typing import Optional
import re

def sanitize_filename(name: Optional[str], max_len: int = 120) -> str:
    """
    清洗文件名：空格转下划线、移除非法字符、截断长度。
    - 适配 Windows 非法字符：\ / : * ? " < > |
    - 空结果回退为 "unnamed"
    """
    t = (name or "").strip()
    t = re.sub(r"\s+", "_", t)
    t = re.sub(r'[\\/:*?"<>|]+', "", t)
    if len(t) > max_len:
        t = t[:max_len]
    return t or "unnamed"