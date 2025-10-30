"""
常见使用场景代码模板集合

使用方法：
1. 选择符合您需求的场景
2. 复制对应代码模板
3. 修改配置参数
4. 运行测试
"""

import asyncio
import json
from typing import List, Dict, Any
from pathlib import Path

# ============================================================================
# 场景1: 文本处理 - 批量校对
# ============================================================================

async def batch_text_correction(texts: List[str]):
    """批量文本校对场景

    适用场景：
    - 批量校对用户输入
    - 内容质量检查
    - 数据清洗
    """
    import sys
    sys.path.append("llm_api")

    from core.llm_client import UnifiedLLMClient

    client = UnifiedLLMClient("llm_api/config/settings.yaml")

    try:
        # 准备请求
        requests = [
            {"task_name": "correction", "user_prompt": f"请校对以下文本：{text}"}
            for text in texts
        ]

        # 批量调用
        print(f"📝 开始批量校对 {len(texts)} 个文本...")
        results = await client.batch_call(requests, max_concurrent=5)

        # 处理结果
        corrected_texts = []
        for i, (original, corrected) in enumerate(zip(texts, results)):
            print(f"\n文本 {i+1}:")
            print(f"  原文: {original}")
            print(f"  校对后: {corrected}")
            corrected_texts.append(corrected)

        return corrected_texts

    finally:
        await client.close()


# 使用示例
if __name__ == "__main__":
    sample_texts = [
        "这是一个包含错别字的文本。",
        "另一个需要校对的文本示例。",
        "第三段需要处理的文本。"
    ]
    asyncio.run(batch_text_correction(sample_texts))


# ============================================================================
# 场景2: 图片分析 - 批量处理
# ============================================================================

async def batch_image_analysis(image_descriptions: List[str]):
    """批量图片分析场景

    适用场景：
    - 批量图片内容审核
    - 图片标签生成
    - 视觉数据分析
    """
    import sys
    sys.path.append("llm_api")

    from core.llm_client import UnifiedLLMClient

    client = UnifiedLLMClient("llm_api/config/settings.yaml")

    try:
        requests = [
            {"task_name": "fact_description", "user_prompt": img}
            for img in image_descriptions
        ]

        print(f"🖼️ 开始批量分析 {len(image_descriptions)} 张图片...")
        results = await client.batch_call(requests, max_concurrent=3)

        # 解析JSON结果（如果返回JSON格式）
        parsed_results = []
        for i, result in enumerate(results):
            print(f"\n图片 {i+1} 分析结果:")
            try:
                # 尝试解析JSON
                data = json.loads(result)
                print(f"  描述: {data.get('description', '')}")
                print(f"  文字内容: {data.get('text_content', '')}")
                parsed_results.append(data)
            except json.JSONDecodeError:
                # 如果不是JSON，直接打印
                print(f"  {result}")
                parsed_results.append({"raw_result": result})

        return parsed_results

    finally:
        await client.close()


# ============================================================================
# 场景3: 流式对话 - 实时响应
# ============================================================================

async def streaming_chat():
    """流式对话场景

    适用场景：
    - 聊天机器人
    - 实时问答系统
    - 在线助手
    """
    import sys
    sys.path.append("llm_api")

    from core.llm_client import UnifiedLLMClient

    client = UnifiedLLMClient("llm_api/config/settings.yaml")

    try:
        question = "请详细解释什么是机器学习"

        print(f"🤔 问题: {question}")
        print("💬 回答: ", end="", flush=True)

        # 流式输出
        async for chunk in client.stream_call(
            task_name="correction",  # 或自定义对话任务
            user_prompt=question
        ):
            print(chunk, end="", flush=True)

        print()  # 换行

    finally:
        await client.close()


# ============================================================================
# 场景4: 带缓存的调用 - 避免重复请求
# ============================================================================

class CachedLLMClient:
    """带缓存的LLM客户端

    避免重复请求，提升性能
    """

    def __init__(self, config_path: str):
        import sys
        sys.path.append("llm_api")

        from core.llm_client import UnifiedLLMClient

        self.client = UnifiedLLMClient(config_path)
        self.cache = {}  # 简单的内存缓存

    async def call_with_cache(self, task_name: str, user_prompt: str, **kwargs):
        """带缓存的调用"""
        # 生成缓存键
        cache_key = f"{task_name}:{user_prompt}:{json.dumps(kwargs, sort_keys=True)}"

        # 检查缓存
        if cache_key in self.cache:
            print("📦 使用缓存结果")
            return self.cache[cache_key]

        # 调用API
        result = await self.client.call(task_name, user_prompt, **kwargs)

        # 存入缓存
        self.cache[cache_key] = result

        return result

    async def close(self):
        await self.client.close()


async def cached_example():
    """使用缓存的示例"""
    client = CachedLLMClient("llm_api/config/settings.yaml")

    try:
        # 第一次调用
        print("第一次调用:")
        result1 = await client.call_with_cache(
            "correction",
            "测试缓存功能"
        )
        print(result1)

        # 第二次调用（命中缓存）
        print("\n第二次调用（应该命中缓存）:")
        result2 = await client.call_with_cache(
            "correction",
            "测试缓存功能"
        )
        print(result2)

    finally:
        await client.close()


# ============================================================================
# 场景5: 带重试的调用 - 提高稳定性
# ============================================================================

async def robust_call(task_name: str, user_prompt: str, max_attempts: int = 5):
    """带重试的稳定调用

    适用场景：
    - 生产环境
    - 网络不稳定环境
    - 高可用性要求
    """
    import sys
    sys.path.append("llm_api")

    from core.llm_client import UnifiedLLMClient
    from core.exceptions import LLMCallError, RateLimitError, NetworkError

    client = UnifiedLLMClient("llm_api/config/settings.yaml")

    try:
        for attempt in range(max_attempts):
            try:
                print(f"尝试 {attempt + 1}/{max_attempts}...")
                result = await client.call(task_name, user_prompt)
                print("✅ 调用成功")
                return result

            except RateLimitError as e:
                print(f"⚠️ 速率限制，等待后重试... ({e})")
                await asyncio.sleep(2 ** attempt)  # 指数退避

            except NetworkError as e:
                print(f"🌐 网络错误，重试中... ({e})")
                await asyncio.sleep(1)

            except LLMCallError as e:
                print(f"❌ 调用失败: {e}")
                if attempt == max_attempts - 1:
                    raise  # 最后一次尝试失败，抛出异常

    finally:
        await client.close()


# ============================================================================
# 场景6: 异步上下文管理 - 自动资源清理
# ============================================================================

class LLMContextManager:
    """异步上下文管理器

    使用方式：
    async with LLMContextManager("config.yaml") as llm:
        result = await llm.call(...)
    """

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.client = None

    async def __aenter__(self):
        import sys
        sys.path.append("llm_api")

        from core.llm_client import UnifiedLLMClient

        self.client = UnifiedLLMClient(self.config_path)
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.close()


# 使用示例
async def context_manager_example():
    """使用上下文管理器的示例"""
    async with LLMContextManager("llm_api/config/settings.yaml") as client:
        result = await client.call(
            task_name="correction",
            user_prompt="使用上下文管理器的示例"
        )
        print(result)


# ============================================================================
# 场景7: 监控和日志 - 生产环境监控
# ============================================================================

import logging
from utils.logger import get_logger


async def monitored_llm_call(task_name: str, user_prompt: str):
    """带监控的LLM调用

    适用场景：
    - 生产环境
    - 需要详细日志的场景
    - 问题追踪和调试
    """
    import sys
    sys.path.append("llm_api")

    from core.llm_client import UnifiedLLMClient
    from utils.logger import log_function_call

    logger = get_logger(__name__)

    @log_function_call
    async def _call():
        client = UnifiedLLMClient("llm_api/config/settings.yaml")
        try:
            result = await client.call(task_name, user_prompt)
            logger.info(f"LLM调用成功，任务: {task_name}")
            return result
        finally:
            await client.close()

    return await _call()


# ============================================================================
# 场景8: 多任务并发处理 - 复杂工作流
# ============================================================================

async def process_multiple_tasks(requests: List[Dict[str, Any]]):
    """多任务并发处理

    适用场景：
    - 复杂业务流程
    - 需要同时处理多种类型的任务
    - 工作流编排
    """
    import sys
    sys.path.append("llm_api")

    from core.llm_client import UnifiedLLMClient

    client = UnifiedLLMClient("llm_api/config/settings.yaml")

    try:
        # 按任务类型分组
        text_requests = [r for r in requests if r.get("type") == "text"]
        image_requests = [r for r in requests if r.get("type") == "image"]

        # 并发处理
        tasks = []

        if text_requests:
            tasks.append(
                client.batch_call([
                    {"task_name": "correction", "user_prompt": r["prompt"]}
                    for r in text_requests
                ], max_concurrent=5)
            )

        if image_requests:
            tasks.append(
                client.batch_call([
                    {"task_name": "fact_description", "user_prompt": r["prompt"]}
                    for r in image_requests
                ], max_concurrent=3)
            )

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    finally:
        await client.close()


# 使用示例
if __name__ == "__main__":
    # 选择要运行的示例
    print("请选择要运行的示例：")
    print("1. 批量文本校对")
    print("2. 批量图片分析")
    print("3. 流式对话")
    print("4. 缓存调用")
    print("5. 稳健调用")
    print("6. 上下文管理器")
    print("7. 监控调用")
    print("8. 多任务并发")

    choice = input("请输入选项 (1-8): ").strip()

    if choice == "1":
        sample_texts = ["测试文本1", "测试文本2", "测试文本3"]
        asyncio.run(batch_text_correction(sample_texts))
    elif choice == "2":
        sample_images = ["图片1描述", "图片2描述", "图片3描述"]
        asyncio.run(batch_image_analysis(sample_images))
    elif choice == "3":
        asyncio.run(streaming_chat())
    elif choice == "4":
        asyncio.run(cached_example())
    elif choice == "5":
        asyncio.run(robust_call("correction", "测试稳健调用"))
    elif choice == "6":
        asyncio.run(context_manager_example())
    elif choice == "7":
        asyncio.run(monitored_llm_call("correction", "测试监控调用"))
    elif choice == "8":
        requests = [
            {"type": "text", "prompt": "文本1"},
            {"type": "text", "prompt": "文本2"},
            {"type": "image", "prompt": "图片1"},
        ]
        asyncio.run(process_multiple_tasks(requests))
    else:
        print("无效选项")
