from openai import OpenAI
import tools.token_counter as token_counter

def send_request(base_url, api_key, model_name, user_content, logger, system_prompt="", response_format=None):
    # 确保 base_url 和 api_key 已正确加载
    if not base_url or not api_key or not model_name:
        error_message = "BASE_URL 或 API_KEY 或 MODEL_NAME 未在 .env 文件中设置"
        logger.error(error_message)
        raise ValueError(error_message)

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    try:
        if response_format and response_format['type'] == 'json_object':
            response = client.chat.completions.create(
                model=model_name,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={
                    'type': 'json_object'
                }
            )
        else:
            response = client.chat.completions.create(
                model=model_name,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ]
            )
    except Exception as e:
        print(f"API请求失败: {e}")
        logger.info(f"API请求失败: {e}")
        return None, 0

    if response and response.choices:
        result = response.choices[0].message.content
        # logger.info(f"API响应: {result}")

        # 计算输出结果的 token 数量
        output_token_count = token_counter.count_tokens(result)

        return result, output_token_count
    else:
        print("API响应无效或没有选项")
        logger.info("API响应无效或没有选项")
        return None, 0