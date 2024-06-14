from zhipuai import ZhipuAI

def sentiment_analysis(query, llm_config):
    client = ZhipuAI(api_key=llm_config["api_key"]) # 填写您自己的APIKey
    
    response = client.chat.completions.create(
        model="glm-3-turbo",  # 填写需要调用的模型名称
        messages=[
            {"role": "system","content": "你是一个情感分类器。情感分类候选词：正面、中性、负面"},
            {"role": "user", "content": f"""
                # 任务：对以下用户评论进行情感分类和特定问题标签标注，只输出结果，
                # 评论：review = "{query}"
                # 输出格式：
                "情感分类": " "
                """
                }
            ],
            temperature= 0.1
    )
    #print(response.choices[0].message.content)
    return response.choices[0].message.content

# 测试
# if __name__ == "__main__":
#     query = """你们图书馆的空调开的太冷了，能不能调高一点？"""
#     sentiment_analysis(query)