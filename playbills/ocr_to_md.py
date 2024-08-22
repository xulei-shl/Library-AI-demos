from openai import OpenAI
from dotenv import load_dotenv
import os
import tiktoken

# 加载 .env 文件中的环境变量
load_dotenv()

# 从环境变量中读取 API 密钥和基础 URL
api_key = os.getenv("OneAPI_API_KEY")
base_url = os.getenv("OneAPI_API_URL")
# api_key = os.getenv("DeepSeek_API_KEY")
# base_url = os.getenv("DeepSeek_API_URL")

client = OpenAI(api_key=api_key, base_url=base_url)

system_prompt = """
    用户提供的文本是演出节目单图片的ocr识别文本及其坐标位置。请按照坐标位置将文本整理成适合阅读的文本。请直接输出整理后的markdown格式文本。
"""

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def split_json_by_tokens(json_data, max_tokens):
    parts = []
    current_part = []
    current_tokens = 0

    for item in json_data['words_result']:
        item_str = str(item)
        item_tokens = num_tokens_from_string(item_str, "cl100k_base")

        # 如果当前部分加上新项的token数量超过了最大限制，则开始一个新的部分
        if current_tokens + item_tokens > max_tokens:
            parts.append(current_part)
            current_part = [item]
            current_tokens = item_tokens
        else:
            current_part.append(item)
            current_tokens += item_tokens

    if current_part:
        parts.append(current_part)

    return parts

def ocr_json_to_md(ocr_result):
    max_tokens = 4096  # 假设最大token限制为4096
    parts = split_json_by_tokens(ocr_result, max_tokens)

    results = []
    for part in parts:
        part_json = {"words_result": part, "words_result_num": len(part), "log_id": ocr_result["log_id"]}
        response = client.chat.completions.create(
            model="deepseek-chat",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(part_json)},
            ]
        )
        result = response.choices[0].message.content
        results.append(result)

    final_result = "\n".join(results)
    return final_result

# 测试函数
# if __name__ == "__main__":
#     ocr_result = {'words_result': [{'words': '崇敬之爱', 'location': {'top': 566, 'left': 4473, 'width': 1650, 'height': 320}}, {'words': '“——《京剧名家名段交响演唱会》拥军优属新春慰问专场', 'location': {'top': 1056, 'left': 3878, 'width': 2800, 'height': 136}}, {'words': '東方國際', 'location': {'top': 2796, 'left': 1965, 'width': 360, 'height': 144}}, {'words': '指导单位：上海市双拥办上海市退役军人事务局', 'location': {'top': 3184, 'left': 936, 'width': 1708, 'height': 92}}, {'words': '主办单位：上海市拥军优属基金会', 'location': {'top': 3317, 'left': 944, 'width': 1178, 'height': 93}}, {'words': '支持单位：东方国际（集团）有限公司', 'location': {'top': 3458, 'left': 941, 'width': 1339, 'height': 94}}, {'words': '节目单', 'location': {'top': 1837, 'left': 4979, 'width': 576, 'height': 2054}}, {'words': '演出单位：上海京剧院', 'location': {'top': 3592, 'left': 942, 'width': 794, 'height': 93}}], 'words_result_num': 8, 'log_id': 1822806243765089653}
#     md_result = ocr_json_to_md(ocr_result)
#     print(md_result)