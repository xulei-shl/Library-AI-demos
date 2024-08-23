

def extract_json_content(result):
    if '```json' in result:
        json_start = result.find('```json') + len('```json')
        json_end = result.find('```', json_start)
        return result[json_start:json_end].strip()
    return result