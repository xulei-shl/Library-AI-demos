#!/usr/bin/env python3
"""
统一LLM调用系统 - 系统测试脚本

验证所有核心模块是否正常工作。
"""

import sys
import os
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """测试模块导入"""
    print("=" * 70)
    print("测试1: 模块导入")
    print("=" * 70)

    tests = [
        ("core.config_loader", "ConfigLoader"),
        ("core.retry_manager", "RetryManager, ErrorType"),
        ("core.exceptions", "所有异常类"),
        ("core.llm_client", "UnifiedLLMClient"),
        ("utils.logger", "get_logger, log_function_call"),
        ("utils.json_handler", "JSONHandler"),
    ]

    passed = 0
    failed = 0

    for module_name, expected in tests:
        try:
            module = __import__(module_name, fromlist=[''])
            print(f"[通过] {module_name} - 导入成功")
            passed += 1
        except Exception as e:
            print(f"[失败] {module_name} - 导入失败: {e}")
            failed += 1

    print(f"\n结果: {passed} 成功, {failed} 失败")
    return failed == 0


def test_config_loader():
    """测试配置加载器"""
    print("\n" + "=" * 70)
    print("测试2: 配置加载器")
    print("=" * 70)

    try:
        from core.config_loader import ConfigLoader

        # 测试配置文件存在
        config_path = "config/settings.yaml"
        if not os.path.exists(config_path):
            print(f"[失败] 配置文件不存在: {config_path}")
            return False

        print(f"[通过] 配置文件存在: {config_path}")

        # 测试加载配置
        loader = ConfigLoader(config_path)
        config = loader.load()

        print(f"[通过] 配置加载成功")
        print(f"   - API提供商数量: {len(config.get('api_providers', {}))}")
        print(f"   - 任务数量: {len(config.get('tasks', {}))}")

        # 测试任务配置
        for task_name in config.get('tasks', {}):
            task_config = config['tasks'][task_name]
            print(f"   - 任务 '{task_name}': {task_config['provider_type']}")

        return True
    except Exception as e:
        print(f"[失败] 配置加载失败: {e}")
        traceback.print_exc()
        return False


def test_logger():
    """测试日志系统"""
    print("\n" + "=" * 70)
    print("测试3: 日志系统")
    print("=" * 70)

    try:
        from utils.logger import get_logger, LoggerManager

        # 测试Logger获取
        logger = get_logger(__name__)
        print(f"[通过] Logger获取成功: {logger.name}")

        # 测试日志记录
        logger.info("这是一条信息日志")
        logger.warning("这是一条警告日志")
        logger.error("这是一条错误日志")

        print(f"[通过] 日志记录成功")

        # 测试日志目录
        log_dir = "runtime/logs"
        if os.path.exists(log_dir):
            print(f"[通过] 日志目录存在: {log_dir}")
        else:
            print(f"[提示] 日志目录未创建（正常，首次使用时创建）")

        return True
    except Exception as e:
        print(f"[失败] 日志系统测试失败: {e}")
        traceback.print_exc()
        return False


def test_json_handler():
    """测试JSON处理工具"""
    print("\n" + "=" * 70)
    print("测试4: JSON处理工具")
    print("=" * 70)

    try:
        from utils.json_handler import JSONHandler

        # 测试JSON解析
        test_json = '{"name": "测试", "value": 123}'
        parsed = JSONHandler.parse_response(test_json)

        if parsed and parsed.get('name') == '测试':
            print(f"[通过] JSON解析成功")
        else:
            print(f"[失败] JSON解析失败")
            return False

        # 测试格式化输出
        formatted = JSONHandler.format_output(parsed, 'json')
        print(f"[通过] JSON格式化成功")

        # 测试无效JSON修复
        invalid_json = '{name: "测试"}'  # 缺少引号
        repaired = JSONHandler.parse_response(invalid_json, enable_repair=True)

        if repaired:
            print(f"[通过] JSON修复成功")
        else:
            print(f"[提示]  JSON修复返回None（可能无法修复此格式）")

        return True
    except Exception as e:
        print(f"[失败] JSON处理测试失败: {e}")
        traceback.print_exc()
        return False


def test_exceptions():
    """测试异常系统"""
    print("\n" + "=" * 70)
    print("测试5: 异常系统")
    print("=" * 70)

    try:
        from core.exceptions import (
            LLMError, LLMCallError, ConfigurationError,
            ProviderError, NetworkError, RateLimitError
        )

        # 测试异常创建
        error = LLMCallError(
            task_name="test_task",
            error_history=[{'attempt': 1, 'error': 'test'}],
            last_error="测试错误"
        )

        print(f"[通过] LLMCallError创建成功")
        print(f"   - 错误信息: {str(error)[:50]}...")

        # 测试异常转字典
        error_dict = error.to_dict()
        print(f"[通过] 异常转字典成功")
        print(f"   - 任务名: {error_dict['task_name']}")

        return True
    except Exception as e:
        print(f"[失败] 异常系统测试失败: {e}")
        traceback.print_exc()
        return False


def test_client_creation():
    """测试客户端创建"""
    print("\n" + "=" * 70)
    print("测试6: 客户端创建")
    print("=" * 70)

    try:
        from core.llm_client import UnifiedLLMClient

        # 测试客户端创建
        client = UnifiedLLMClient()
        print(f"[通过] 客户端创建成功")

        # 测试任务列表
        tasks = client.list_tasks()
        print(f"[通过] 任务列表获取成功: {tasks}")

        # 测试获取任务配置
        if tasks:
            task_name = tasks[0]
            config = client.get_task_config(task_name)
            print(f"[通过] 任务配置获取成功: {task_name}")

        # 清理
        import asyncio
        asyncio.run(client.close())
        print(f"[通过] 客户端关闭成功")

        return True
    except FileNotFoundError as e:
        print(f"[失败] 配置文件不存在: {e}")
        print("   请确保 config/settings.yaml 存在")
        return False
    except Exception as e:
        print(f"[失败] 客户端测试失败: {e}")
        traceback.print_exc()
        return False


def test_prompt_files():
    """测试提示词文件"""
    print("\n" + "=" * 70)
    print("测试7: 提示词文件")
    print("=" * 70)

    try:
        prompt_dir = "prompts"
        if not os.path.exists(prompt_dir):
            print(f"[失败] 提示词目录不存在: {prompt_dir}")
            return False

        print(f"[通过] 提示词目录存在: {prompt_dir}")

        # 检查提示词文件
        prompt_files = [f for f in os.listdir(prompt_dir) if f.endswith('.md')]
        print(f"[通过] 找到 {len(prompt_files)} 个提示词文件:")

        for filename in prompt_files:
            filepath = os.path.join(prompt_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   - {filename} ({len(content)} 字符)")

        return True
    except Exception as e:
        print(f"[失败] 提示词文件测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n[启动] 统一LLM调用系统 - 系统测试")
    print("=" * 70)

    tests = [
        ("模块导入", test_imports),
        ("配置加载器", test_config_loader),
        ("日志系统", test_logger),
        ("JSON处理工具", test_json_handler),
        ("异常系统", test_exceptions),
        ("客户端创建", test_client_creation),
        ("提示词文件", test_prompt_files),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[失败] 测试 '{test_name}' 发生异常: {e}")
            traceback.print_exc()
            results.append((test_name, False))

    # 汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[通过]" if result else "[失败]"
        print(f"{status}: {test_name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n[成功] 所有测试通过！系统准备就绪！")
        return 0
    else:
        print(f"\n[警告] 有 {total - passed} 个测试失败，请检查上述错误")
        return 1


if __name__ == "__main__":
    sys.exit(main())