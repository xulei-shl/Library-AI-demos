"""
批量调用示例

展示如何高效地批量处理多个请求。
"""

import asyncio
from core.llm_client import UnifiedLLMClient


async def batch_call_example():
    """批量调用示例"""
    print("=" * 60)
    print("批量调用示例")
    print("=" * 60)

    client = UnifiedLLMClient()

    # 准备批量请求
    requests = [
        {"task_name": "fact_description", "user_prompt": "图片1描述"},
        {"task_name": "fact_description", "user_prompt": "图片2描述"},
        {"task_name": "fact_description", "user_prompt": "图片3描述"},
        {"task_name": "correction", "user_prompt": "校对文本：这是一个测试文本。"},
        {"task_name": "correction", "user_prompt": "校对文本：这是另一个测试文本。"},
    ]

    print(f"\n发送 {len(requests)} 个请求...")

    # 批量调用
    results = await client.batch_call(requests, max_concurrent=3)

    # 处理结果
    print("\n" + "=" * 60)
    print("批量调用结果")
    print("=" * 60)

    for i, result in enumerate(results):
        print(f"\n请求 {i + 1}: {requests[i]['task_name']}")
        if result is None:
            print("  结果: 调用失败")
        else:
            print(f"  结果: {result[:100]}...")

    await client.close()


async def batch_call_with_retry():
    """批量调用带重试示例"""
    print("\n" + "=" * 60)
    print("批量调用（限制并发数）")
    print("=" * 60)

    client = UnifiedLLMClient()

    # 模拟大量请求
    requests = [
        {"task_name": "fact_description", "user_prompt": f"请求 {i}"}
        for i in range(20)
    ]

    print(f"\n发送 {len(requests)} 个请求（最大并发3）...")

    # 限制并发数为3
    results = await client.batch_call(requests, max_concurrent=3)

    success_count = sum(1 for r in results if r is not None)
    print(f"\n完成: {success_count}/{len(requests)} 成功")

    await client.close()


if __name__ == "__main__":
    asyncio.run(batch_call_example())
    asyncio.run(batch_call_with_retry())