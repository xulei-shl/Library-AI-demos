

def extract_json_content(result):
    # 首先尝试查找 ```json 标记
    if '```json' in result:
        json_start = result.find('```json') + len('```json')
        json_end = result.find('```', json_start)
        return result[json_start:json_end].strip()
    
    # 如果没有找到 ```json，则尝试查找普通的 ``` 代码块
    elif '```' in result:
        # 找到第一个 ``` 的位置
        block_start = result.find('```') + len('```')
        # 跳过可能存在的语言标识符（如果有的话）
        if result[block_start:].lstrip().startswith('\n'):
            block_start = result.find('\n', block_start) + 1
        # 找到代码块的结束位置
        block_end = result.find('```', block_start)
        if block_end != -1:
            content = result[block_start:block_end].strip()
            # 尝试判断内容是否看起来像 JSON（简单检查）
            if content.strip().startswith('{') or content.strip().startswith('['):
                return content
    
    # 如果都没找到，返回原始内容
    return result