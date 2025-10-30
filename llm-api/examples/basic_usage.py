"""
基础使用示例

展示统一LLM客户端的基本使用方法。
"""

import asyncio
from core.llm_client import UnifiedLLMClient


async def basic_call_example():
    """基础调用示例"""
    print("=" * 60)
    print("基础调用示例")
    print("=" * 60)

    # 创建客户端
    client = UnifiedLLMClient()

    # 1. 简单调用 - 图像描述
    print("\n1. 图像描述任务")
    result = await client.call(
        task_name="fact_description",
        user_prompt="请描述这张图片的内容"
    )
    print(f"结果:\n{result}")

    # 2. 覆盖配置参数
    print("\n2. 自定义参数调用")
    result = await client.call(
        task_name="fact_description",
        user_prompt="请用JSON格式返回结果",
        temperature=0.3,
        max_tokens=1000
    )
    print(f"结果:\n{result}")

    # 3. 文本校对任务
    print("\n3. 文本校对任务")
    test_text = "这是一个需要校对的文本。它包含了一些错别字和语法错误。"
    result = await client.call(
        task_name="correction",
        user_prompt=f"请校对以下文本：{test_text}"
    )
    print(f"结果:\n{result}")

    # 关闭客户端
    await client.close()


async def list_tasks_example():
    """列出任务示例"""
    print("\n" + "=" * 60)
    print("列出任务示例")
    print("=" * 60)

    client = UnifiedLLMClient()

    # 列出所有可用任务
    tasks = client.list_tasks()
    print(f"\n可用任务: {tasks}")

    # 获取任务配置
    for task_name in tasks:
        config = client.get_task_config(task_name)
        print(f"\n任务: {task_name}")
        print(f"  提供商类型: {config['provider_type']}")
        print(f"  提示词类型: {config['prompt']['type']}")
        print(f"  温度: {config.get('temperature', '未设置')}")

    await client.close()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(basic_call_example())
    asyncio.run(list_tasks_example())