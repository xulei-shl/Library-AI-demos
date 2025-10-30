"""
快速接入模板 - 复制此文件到您的项目中即可使用

使用方法：
1. 复制此文件到您的项目根目录
2. 修改下面的配置路径为您的实际路径
3. 运行：python quick_start_template.py
"""

import asyncio
import os
from pathlib import Path

# ============================================================================
# 第一步：配置路径 - 修改为您的实际路径
# ============================================================================

# 方法1: 直接指定绝对路径（推荐）
LLM_API_CONFIG_PATH = "/path/to/your/llm_api/config/settings.yaml"

# 方法2: 使用相对路径（如果此文件在项目根目录）
# LLM_API_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "llm_api", "config", "settings.yaml")

# 方法3: 使用环境变量（生产环境推荐）
# LLM_API_CONFIG_PATH = os.getenv("LLM_CONFIG_PATH", "llm_api/config/settings.yaml")


# ============================================================================
# 第二步：配置您的API密钥（三种方式任选其一）
# ============================================================================

# 方式1: 在项目根目录创建 .env 文件（推荐）
# .env 文件内容示例：
# DEEPSEEK_API_KEY=sk-your-api-key-here
# GROQ_API_KEY=gsk-your-groq-key

# 方式2: 直接在代码中设置环境变量（仅用于测试）
# os.environ["DEEPSEEK_API_KEY"] = "sk-your-api-key-here"

# 方式3: 修改 config/settings.yaml 中的配置
# 在 api_providers.text.primary.api_key 中直接写密钥（不推荐）


# ============================================================================
# 快速使用示例
# ============================================================================

async def quick_start():
    """1分钟快速开始示例"""

    try:
        # 导入客户端（根据您的目录结构调整路径）
        import sys
        llm_api_path = Path(__file__).parent / "llm_api"
        sys.path.insert(0, str(llm_api_path))

        from core.llm_client import UnifiedLLMClient

        print("=" * 60)
        print("🚀 统一LLM调用系统 - 快速开始")
        print("=" * 60)

        # 创建客户端
        print("\n📌 步骤1: 初始化客户端...")
        client = UnifiedLLMClient(LLM_API_CONFIG_PATH)
        print("✅ 客户端创建成功")

        # 列出可用任务
        print("\n📌 步骤2: 查看可用任务...")
        tasks = client.list_tasks()
        print(f"✅ 可用任务: {tasks}")

        # 简单文本校对
        print("\n📌 步骤3: 执行文本校对任务...")
        test_text = "这是一个测试文本，包含了一些错别字。"

        result = await client.call(
            task_name="correction",  # 使用预配置的校对任务
            user_prompt=f"请校对以下文本：{test_text}"
        )

        print("\n📝 输入文本:")
        print(f"   {test_text}")
        print("\n✨ 校对结果:")
        print(f"   {result}")

        # 流式调用示例
        print("\n📌 步骤4: 流式文本生成...")
        print("   输出: ", end="", flush=True)

        async for chunk in client.stream_call(
            task_name="correction",
            user_prompt="请用一句话介绍人工智能"
        ):
            print(chunk, end="", flush=True)

        print("\n\n✅ 所有示例执行完成！")

        # 关闭客户端
        await client.close()

    except FileNotFoundError as e:
        print(f"\n❌ 配置文件错误: {e}")
        print(f"\n💡 解决方案:")
        print(f"   1. 确保配置文件路径正确: {LLM_API_CONFIG_PATH}")
        print(f"   2. 检查文件是否存在: {os.path.exists(LLM_API_CONFIG_PATH)}")

    except Exception as e:
        print(f"\n❌ 执行出错: {type(e).__name__}: {e}")
        print(f"\n💡 常见解决方案:")
        print(f"   1. 检查API密钥是否正确配置")
        print(f"   2. 检查网络连接")
        print(f"   3. 查看详细日志: https://github.com/your-repo/llm-api/blob/main/项目接入指南.md")


async def custom_task_example():
    """自定义任务示例"""

    print("\n" + "=" * 60)
    print("🛠️ 自定义任务示例")
    print("=" * 60)

    import sys
    llm_api_path = Path(__file__).parent / "llm_api"
    sys.path.insert(0, str(llm_api_path))

    from core.llm_client import UnifiedLLMClient

    client = UnifiedLLMClient(LLM_API_CONFIG_PATH)

    # 如果您已经添加了自定义任务，可以这样调用：
    try:
        result = await client.call(
            task_name="my_custom_task",  # 您在config中定义的任务名
            user_prompt="您的自定义输入"
        )
        print(f"\n✨ 自定义任务结果: {result}")

    except Exception as e:
        print(f"\n📝 自定义任务 'my_custom_task' 不存在")
        print(f"   请参考文档添加自定义任务")
        print(f"   查看: https://github.com/your-repo/llm-api/blob/main/项目接入指南.md#自定义任务")

    await client.close()


def list_tasks():
    """列出所有可用任务和配置"""

    print("\n" + "=" * 60)
    print("📋 任务列表")
    print("=" * 60)

    import sys
    llm_api_path = Path(__file__).parent / "llm_api"
    sys.path.insert(0, str(llm_api_path))

    try:
        from core.llm_client import UnifiedLLMClient

        client = UnifiedLLMClient(LLM_API_CONFIG_PATH)

        tasks = client.list_tasks()

        print(f"\n📊 共找到 {len(tasks)} 个任务:\n")

        for task_name in tasks:
            config = client.get_task_config(task_name)
            print(f"🔹 任务名: {task_name}")
            print(f"   提供商类型: {config.get('provider_type', '未设置')}")
            print(f"   提示词类型: {config.get('prompt', {}).get('type', '未设置')}")
            print(f"   温度: {config.get('temperature', '未设置')}")
            print(f"   重试次数: {config.get('retry', {}).get('max_retries', '未设置')}")
            print()

        client.close()

    except Exception as e:
        print(f"❌ 无法加载任务列表: {e}")


async def main():
    """主函数"""

    print("\n" + "=" * 60)
    print("🎯 请选择要执行的操作:")
    print("=" * 60)
    print("1. 快速开始示例")
    print("2. 查看任务列表")
    print("3. 自定义任务示例")
    print("4. 全部执行")
    print("=" * 60)

    choice = input("\n请输入选项 (1-4): ").strip()

    if choice == "1":
        await quick_start()
    elif choice == "2":
        list_tasks()
    elif choice == "3":
        await custom_task_example()
    elif choice == "4":
        await quick_start()
        list_tasks()
        await custom_task_example()
    else:
        print("\n❌ 无效选项")


if __name__ == "__main__":
    # 运行示例
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 用户取消操作，再见！")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        print(f"\n📖 查看详细文档: ./项目接入指南.md")
