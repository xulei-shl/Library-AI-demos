import tiktoken

def count_tokens(text):
    """
    计算给定文本的token数量。

    :param text: 要计算token数量的文本
    :return: 文本的token数量
    """
    # 使用 tiktoken 的 cl100k_base 编码器
    encoder = tiktoken.get_encoding("cl100k_base")
    tokens = encoder.encode(text)
    return len(tokens)


    # 示例文本
# if __name__ == "__main__":

#     text = """


#     请根据上述要求，一步步思考，逐步完成任务。
#     """

#     # 调用 count_tokens 函数计算token数量
#     token_count = count_tokens(text)

#     # 打印结果
#     print(f"文本的token数量为: {token_count}")