"""
自定义配置示例

展示如何使用自定义配置文件和动态修改配置。
"""

import asyncio
from core.llm_client import UnifiedLLMClient
from core.exceptions import ConfigurationError


async def custom_config_example():
    """自定义配置示例"""
    print("=" * 60)
    print("自定义配置示例")
    print("=" * 60)

    # 使用自定义配置文件
    print("\n1. 使用自定义配置文件")
    client = UnifiedLLMClient(config_path="config/settings.yaml")

    # 获取任务配置
    config = client.get_task_config("fact_description")
    print(f"fact_description 配置:")
    print(f"  提供商类型: {config['provider_type']}")
    print(f"  温度: {config['temperature']}")
    print(f"  提示词路径: {config['prompt']['source']}")

    # 列出所有任务
    tasks = client.list_tasks()
    print(f"\n所有可用任务: {tasks}")

    await client.close()


async def config_override_example():
    """配置覆盖示例"""
    print("\n" + "=" * 60)
    print("配置覆盖示例")
    print("=" * 60)

    client = UnifiedLLMClient()

    # 在调用时覆盖配置
    print("\n1. 动态覆盖温度参数")
    result1 = await client.call(
        task_name="fact_description",
        user_prompt="测试文本",
        temperature=0.1  # 覆盖配置，使用更低的温度
    )
    print(f"低温结果 (temperature=0.1): {result1[:100]}...")

    print("\n2. 动态覆盖最大tokens")
    result2 = await client.call(
        task_name="fact_description",
        user_prompt="测试文本",
        max_tokens=500  # 覆盖配置
    )
    print(f"短文本结果 (max_tokens=500): {result2[:100]}...")

    await client.close()


async def error_handling_example():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("错误处理示例")
    print("=" * 60)

    client = UnifiedLLMClient()

    # 处理配置错误
    print("\n1. 处理配置错误")
    try:
        result = await client.call(
            task_name="nonexistent_task",  # 不存在的任务
            user_prompt="测试"
        )
    except ConfigurationError as e:
        print(f"捕获配置错误: {e}")

    # 处理调用失败
    print("\n2. 处理调用失败")
    try:
        # 使用无效的API密钥会导致失败
        # 这里只是演示错误处理机制
        result = await client.call(
            task_name="fact_description",
            user_prompt="测试"
        )
    except Exception as e:
        print(f"捕获调用错误: {type(e).__name__}: {str(e)[:100]}")

    await client.close()


async def reload_config_example():
    """重新加载配置示例"""
    print("\n" + "=" * 60)
    print("重新加载配置示例")
    print("=" * 60)

    client = UnifiedLLMClient()

    # 获取当前任务列表
    print("\n1. 初始任务列表")
    tasks = client.list_tasks()
    print(f"任务: {tasks}")

    # 重新加载配置
    print("\n2. 重新加载配置")
    client.reload_config()
    print("配置已重新加载")

    # 再次获取任务列表
    print("\n3. 重新加载后的任务列表")
    tasks = client.list_tasks()
    print(f"任务: {tasks}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(custom_config_example())
    asyncio.run(config_override_example())
    asyncio.run(error_handling_example())
    asyncio.run(reload_config_example())