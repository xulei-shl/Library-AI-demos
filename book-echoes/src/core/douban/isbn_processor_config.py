#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISBN处理器配置优化

提供不同场景下的最优配置参数
支持智能引用整合，与config/setting.yaml集成
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessingConfig:
    """处理配置"""
    name: str
    description: str
    max_concurrent: int
    batch_size: int
    min_delay: float
    max_delay: float
    retry_times: int
    timeout: int
    browser_startup_timeout: int  # 浏览器启动超时时间（秒）
    page_navigation_timeout: int  # 页面导航超时时间（秒）
    use_case: str
    performance_estimate: str


# 预定义配置方案
PROCESSING_CONFIGS = {
    "conservative": ProcessingConfig(
        name="保守配置",
        description="最稳定的配置，适合生产环境",
        max_concurrent=3,
        batch_size=30,
        min_delay=1.0,
        max_delay=3.0,
        retry_times=3,
        timeout=20,
        browser_startup_timeout=180,  # 浏览器启动超时3分钟
        page_navigation_timeout=180,  # 页面导航超时3分钟
        use_case="生产环境，稳定的网络环境",
        performance_estimate="3-5倍提速，1万条需要6-10小时"
    ),

    "balanced": ProcessingConfig(
        name="平衡配置",
        description="性能和稳定性平衡，推荐默认选择",
        max_concurrent=5,
        batch_size=50,
        min_delay=0.5,
        max_delay=2.0,
        retry_times=3,
        timeout=15,
        browser_startup_timeout=180,  # 浏览器启动超时3分钟
        page_navigation_timeout=180,  # 页面导航超时3分钟
        use_case="一般生产环境，良好的网络条件",
        performance_estimate="5-8倍提速，1万条需要3-6小时"
    ),

    "aggressive": ProcessingConfig(
        name="激进配置",
        description="追求最高性能，适合测试环境",
        max_concurrent=8,
        batch_size=100,
        min_delay=0.3,
        max_delay=1.5,
        retry_times=2,
        timeout=12,
        browser_startup_timeout=180,  # 浏览器启动超时3分钟
        page_navigation_timeout=180,  # 页面导航超时3分钟
        use_case="测试环境或高速网络",
        performance_estimate="8-12倍提速，1万条需要2-4小时"
    ),

    "emergency": ProcessingConfig(
        name="紧急配置",
        description="最低延迟，适合急需处理的少量数据",
        max_concurrent=10,
        batch_size=200,
        min_delay=0.1,
        max_delay=0.8,
        retry_times=1,
        timeout=10,
        browser_startup_timeout=180,  # 浏览器启动超时3分钟
        page_navigation_timeout=180,  # 页面导航超时3分钟
        use_case="少量数据紧急处理",
        performance_estimate="10-15倍提速，但成功率可能降低"
    )
}


def load_config_from_yaml(config_dict: Dict[str, Any]) -> Optional[ProcessingConfig]:
    """
    从配置字典加载ISBN处理器配置（智能引用整合支持）

    Args:
        config_dict: 配置字典，包含isbn_processor配置

    Returns:
        ProcessingConfig: 处理配置对象，如果配置无效则返回None
    """
    if not config_dict:
        logger.warning("配置字典为空，使用默认平衡配置")
        return get_config("balanced")

    strategy = config_dict.get('strategy', 'auto')

    try:
        if strategy == 'custom':
            custom_params = config_dict.get('custom', {})
            return create_custom_config(**custom_params)
        elif strategy == 'auto':
            # auto模式需要外部数据量信息，这里返回默认配置
            logger.info("auto模式需要外部数据量信息，返回默认平衡配置")
            return get_config("balanced")
        else:
            logger.warning(f"未知配置策略: {strategy}，使用默认平衡配置")
            return get_config("balanced")
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}，使用默认平衡配置")
        return get_config("balanced")


def get_config_strategy_info() -> Dict[str, str]:
    """
    获取配置策略说明信息

    Returns:
        Dict: 策略说明字典
    """
    return {
        "custom": "使用自定义配置 (用户在config/setting.yaml中定义)",
        "auto": "根据数据量自动选择配置 (需要外部提供数据量信息)"
    }


def validate_config_from_dict(config_dict: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    验证配置字典的有效性

    Args:
        config_dict: 配置字典

    Returns:
        tuple: (是否有效, 错误信息列表)
    """
    errors = []

    if not isinstance(config_dict, dict):
        errors.append("配置必须是字典类型")
        return False, errors

    strategy = config_dict.get('strategy', 'auto')

    if strategy not in ['custom', 'auto']:
        errors.append(f"未知策略: {strategy}，必须是 custom/auto 之一")

    if strategy == 'custom':
        custom = config_dict.get('custom', {})
        if not isinstance(custom, dict):
            errors.append("custom配置必须是字典类型")
        else:
            # 验证自定义参数
            if 'max_concurrent' in custom:
                if not (1 <= custom['max_concurrent'] <= 20):
                    errors.append("max_concurrent应在1-20之间")
            if 'batch_size' in custom:
                if not (10 <= custom['batch_size'] <= 500):
                    errors.append("batch_size应在10-500之间")

    return len(errors) == 0, errors


def merge_configs(base_config: ProcessingConfig, override_config: Dict[str, Any]) -> ProcessingConfig:
    """
    合并配置，用override_config中的值覆盖base_config的对应值

    Args:
        base_config: 基础配置
        override_config: 覆盖配置字典

    Returns:
        ProcessingConfig: 合并后的配置
    """
    if not override_config:
        return base_config

    # 创建新配置对象
    new_config = ProcessingConfig(
        name=override_config.get('name', base_config.name),
        description=override_config.get('description', base_config.description),
        max_concurrent=override_config.get('max_concurrent', base_config.max_concurrent),
        batch_size=override_config.get('batch_size', base_config.batch_size),
        min_delay=override_config.get('min_delay', base_config.min_delay),
        max_delay=override_config.get('max_delay', base_config.max_delay),
        retry_times=override_config.get('retry_times', base_config.retry_times),
        timeout=override_config.get('timeout', base_config.timeout),
        browser_startup_timeout=override_config.get('browser_startup_timeout', base_config.browser_startup_timeout),
        page_navigation_timeout=override_config.get('page_navigation_timeout', base_config.page_navigation_timeout),
        use_case=override_config.get('use_case', base_config.use_case),
        performance_estimate=override_config.get('performance_estimate', base_config.performance_estimate)
    )

    return new_config


def get_config(config_name: str = "balanced") -> ProcessingConfig:
    """
    获取处理配置
    
    Args:
        config_name: 配置名称 (conservative, balanced, aggressive, emergency)
    
    Returns:
        ProcessingConfig: 处理配置对象
    """
    if config_name not in PROCESSING_CONFIGS:
        raise ValueError(f"未知配置: {config_name}，可用配置: {list(PROCESSING_CONFIGS.keys())}")
    
    return PROCESSING_CONFIGS[config_name]


def get_config_for_data_size(data_size: int, log_selection: bool = True) -> ProcessingConfig:
    """
    根据数据量推荐配置
    
    Args:
        data_size: 数据条数
        log_selection: 是否记录选择日志
    
    Returns:
        ProcessingConfig: 推荐的配置
    """
    if data_size <= 100:
        config = PROCESSING_CONFIGS["emergency"]
        reason = "少量数据，使用紧急配置追求最高速度"
    elif data_size <= 1000:
        config = PROCESSING_CONFIGS["aggressive"]
        reason = "中等数据量，使用激进配置追求高性能"
    elif data_size <= 10000:
        config = PROCESSING_CONFIGS["balanced"]
        reason = "较大数据量，使用平衡配置兼顾性能和稳定性"
    else:
        config = PROCESSING_CONFIGS["conservative"]
        reason = "大量数据，使用保守配置确保稳定性"
    
    if log_selection:
        logger.info(f"数据量: {data_size} 条 -> 选择配置: {config.name} ({reason})")
    
    return config


def create_custom_config(max_concurrent: int = 5,
                        batch_size: int = 50,
                        min_delay: float = 0.5,
                        max_delay: float = 2.0,
                        retry_times: int = 3,
                        timeout: int = 15,
                        browser_startup_timeout: int = 180,
                        page_navigation_timeout: int = 180) -> ProcessingConfig:
    """
    创建自定义配置

    Args:
        max_concurrent: 最大并发数
        batch_size: 批处理大小
        min_delay: 最小延迟
        max_delay: 最大延迟
        retry_times: 重试次数
        timeout: 超时时间
        browser_startup_timeout: 浏览器启动超时时间（秒）
        page_navigation_timeout: 页面导航超时时间（秒）

    Returns:
        ProcessingConfig: 自定义配置
    """
    return ProcessingConfig(
        name="自定义配置",
        description="用户自定义配置",
        max_concurrent=max_concurrent,
        batch_size=batch_size,
        min_delay=min_delay,
        max_delay=max_delay,
        retry_times=retry_times,
        timeout=timeout,
        browser_startup_timeout=browser_startup_timeout,
        page_navigation_timeout=page_navigation_timeout,
        use_case="用户自定义",
        performance_estimate="根据参数计算"
    )


def validate_config(config: ProcessingConfig) -> tuple[bool, list[str]]:
    """
    验证配置参数

    Args:
        config: 配置对象

    Returns:
        tuple: (是否有效, 错误信息列表)
    """
    errors = []

    # 验证并发数
    if not (1 <= config.max_concurrent <= 20):
        errors.append("最大并发数应在1-20之间")

    # 验证批大小
    if not (10 <= config.batch_size <= 500):
        errors.append("批处理大小应在10-500之间")

    # 验证延迟时间
    if not (0.1 <= config.min_delay <= 10):
        errors.append("最小延迟应在0.1-10秒之间")
    if not (0.2 <= config.max_delay <= 20):
        errors.append("最大延迟应在0.2-20秒之间")
    if config.min_delay >= config.max_delay:
        errors.append("最小延迟应小于最大延迟")

    # 验证重试次数
    if not (1 <= config.retry_times <= 10):
        errors.append("重试次数应在1-10次之间")

    # 验证超时时间
    if not (5 <= config.timeout <= 60):
        errors.append("超时时间应在5-60秒之间")

    # 验证浏览器启动超时时间
    if not (30 <= config.browser_startup_timeout <= 600):
        errors.append("浏览器启动超时时间应在30-600秒之间（0.5-10分钟）")

    # 验证页面导航超时时间
    if not (30 <= config.page_navigation_timeout <= 600):
        errors.append("页面导航超时时间应在30-600秒之间（0.5-10分钟）")

    return len(errors) == 0, errors


def print_config_comparison():
    """打印配置对比表"""
    print("📋 ISBN处理器配置对比")
    print("=" * 80)
    print(f"{'配置名称':<12} | {'并发数':<6} | {'批大小':<6} | {'延迟范围':<12} | {'预估性能':<15}")
    print("-" * 80)
    
    for config in PROCESSING_CONFIGS.values():
        delay_range = f"{config.min_delay:.1f}-{config.max_delay:.1f}s"
        print(f"{config.name:<12} | {config.max_concurrent:<6} | {config.batch_size:<6} | {delay_range:<12} | {config.performance_estimate:<15}")
    
    print("-" * 80)
    print("\n💡 使用建议:")
    print("• 保守配置: 适合网络不稳定或需要高成功率的场景")
    print("• 平衡配置: 推荐默认选择，性能和稳定性平衡")
    print("• 激进配置: 适合测试环境或高速网络")
    print("• 紧急配置: 适合少量数据紧急处理")


def estimate_performance(config: ProcessingConfig, data_size: int) -> Dict[str, Any]:
    """
    估算处理性能
    
    Args:
        config: 配置对象
        data_size: 数据条数
    
    Returns:
        Dict: 性能估算结果
    """
    # 基础性能估算（基于原始6.63秒/条的基准）
    base_time_per_item = 6.63
    
    # 并发加速因子
    concurrency_factor = min(config.max_concurrent * 0.8, 8)  # 并发效果递减
    
    # 延迟优化因子
    delay_factor = (config.min_delay + config.max_delay) / 4  # 平均延迟
    
    # 计算优化后的单条处理时间
    optimized_time_per_item = base_time_per_item / concurrency_factor / (1 + delay_factor * 0.1)
    
    # 总处理时间
    total_processing_time = data_size * optimized_time_per_item
    
    # 成功率和失败重试影响
    success_rate = 0.95  # 假设95%成功率
    retry_impact = 1 + (1 - success_rate) * config.retry_times * 0.3
    
    final_time = total_processing_time * retry_impact
    
    return {
        "data_size": data_size,
        "estimated_time_per_item": optimized_time_per_item,
        "total_time_seconds": final_time,
        "total_time_hours": final_time / 3600,
        "throughput_items_per_hour": data_size / (final_time / 3600),
        "speed_improvement": base_time_per_item / optimized_time_per_item,
        "estimated_success_rate": success_rate,
        "concurrent_bottleneck": config.max_concurrent >= 8
    }


if __name__ == "__main__":
    print("ISBN处理器配置优化工具")
    print("=" * 40)
    
    # 显示配置对比
    print_config_comparison()
    
    print("\n🚀 性能估算示例:")
    
    # 估算不同数据量的处理时间
    for size in [100, 1000, 10000]:
        print(f"\n📊 数据量: {size} 条")
        for config_name in ["balanced", "aggressive"]:
            config = get_config(config_name)
            estimate = estimate_performance(config, size)
            print(f"  {config.name}: {estimate['total_time_hours']:.1f}小时 "
                  f"(提升{estimate['speed_improvement']:.1f}倍)")