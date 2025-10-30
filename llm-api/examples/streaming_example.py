"""
流式调用示例

展示如何使用流式调用功能，实时获取LLM响应。
"""

import asyncio
from core.llm_client import UnifiedLLMClient


async def streaming_call_example():
    """流式调用示例"""
    print("=" * 60)
    print("流式调用示例")
    print("=" * 60)

    client = UnifiedLLMClient()

    # 流式输出文本生成
    print("\n1. 流式文本生成")
    print("响应内容: ", end="", flush=True)

    async for chunk in client.stream_call(
        task_name="correction",
        user_prompt="写一篇关于人工智能的短文"
    ):
        print(chunk, end="", flush=True)

    print("\n")  # 换行

    await client.close()


async def streaming_with_task():
    """带有任务管理的流式调用"""
    print("=" * 60)
    print("带进度显示的流式调用")
    print("=" * 60)

    client = UnifiedLLMClient()

    print("\n正在生成内容...")
    content_count = 0

    async for chunk in client.stream_call(
        task_name="correction",
        user_prompt="解释什么是机器学习，要求详细且易懂"
    ):
        print(chunk, end="", flush=True)
        content_count += len(chunk)

    print(f"\n\n生成完成，共 {content_count} 字符")

    await client.close()


if __name__ == "__main__":
    asyncio.run(streaming_call_example())
    asyncio.run(streaming_with_task())