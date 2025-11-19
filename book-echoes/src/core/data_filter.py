"""
图书筛选器 - 支持模块化和动态扩展
"""

import os
import yaml
import pandas as pd
from typing import Dict, Any, List, Tuple
from .filters import FilterRegistry
from src.utils.logger import get_logger
from src.utils.config_manager import get_config

logger = get_logger(__name__)


class BookFilterFinal:
    """图书筛选器 - 支持模块化和动态扩展"""
    
    def __init__(self, config_path: str = "config/setting.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.filter_results = {}
        self._init_filters()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"配置文件不存在: {self.config_path}")
                return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _init_filters(self):
        """初始化所有筛选器"""
        self.filters = []
        
        # 从配置文件动态创建筛选器
        filtering_config = self.config.get('filtering', {})
        
        for rule_name, rule_config in filtering_config.items():
            if not isinstance(rule_config, dict):
                continue
                
            # 特殊处理rule_a - 它没有嵌套结构，直接是筛选器配置
            if rule_name == 'rule_a':
                if rule_config.get('enabled', False):
                    try:
                        filter_type = self._determine_filter_type(rule_name, 'hot_books')
                        filter_instance = FilterRegistry.create_filter(filter_type, rule_config)
                        self.filters.append(('hot_books', filter_instance))
                        logger.info(f"创建筛选器成功: hot_books ({filter_type})")
                    except Exception as e:
                        logger.warning(f"创建筛选器 'hot_books' 失败: {e}")
                continue
                
            # 处理rule_b和rule_c的嵌套结构
            for filter_name, filter_config in rule_config.items():
                if isinstance(filter_config, dict) and filter_config.get('enabled', False):
                    try:
                        # 根据配置类型选择筛选器
                        filter_type = self._determine_filter_type(rule_name, filter_name)
                        filter_instance = FilterRegistry.create_filter(filter_type, filter_config)
                        self.filters.append((filter_name, filter_instance))
                        logger.info(f"创建筛选器成功: {filter_name} ({filter_type})")
                    except Exception as e:
                        logger.warning(f"创建筛选器 '{filter_name}' 失败: {e}")
    
    def _determine_filter_type(self, rule_name: str, filter_name: str) -> str:
        """根据规则名称确定筛选器类型"""
        if rule_name == 'rule_a':
            return 'hot_books'
        elif rule_name == 'rule_b':
            if 'title' in filter_name.lower():
                return 'title_keywords'
            elif 'call_number' in filter_name.lower() or 'clc' in filter_name.lower():
                return 'call_number'
        elif rule_name == 'rule_c':
            return 'column_value'
        
        return 'column_value'  # 默认类型
    
    def _get_filter_reason_description(self, filter_name: str, filter_result: Dict[str, Any], filter_instance) -> str:
        """智能生成过滤原因描述
        
        Args:
            filter_name: 筛选器名称
            filter_result: 筛选结果信息
            filter_instance: 筛选器实例
            
        Returns:
            str: 过滤原因描述
        """
        # 1. 优先使用配置中的描述
        config_description = filter_result.get('description') or getattr(filter_instance, 'description', '')
        if config_description:
            return self._enhance_description(config_description, filter_name, filter_result, filter_instance)
        
        # 2. 如果没有配置描述，使用智能推断
        return self._infer_description(filter_name, filter_result, filter_instance)
    
    def _enhance_description(self, base_description: str, filter_name: str, filter_result: Dict[str, Any], filter_instance) -> str:
        """增强基础描述，添加动态信息
        
        Args:
            base_description: 基础描述
            filter_name: 筛选器名称
            filter_result: 筛选结果信息
            filter_instance: 筛选器实例
            
        Returns:
            str: 增强后的描述
        """
        # 获取筛选器类型
        filter_type = self._determine_filter_type_from_instance(filter_instance)
        
        # 根据筛选器类型动态增强描述
        if filter_type == 'hot_books':
            threshold = filter_result.get('threshold')
            if threshold:
                return f"{base_description}（借阅≥{threshold}次）"
            else:
                return f"{base_description}（动态阈值）"
        
        elif filter_type in ['title_keywords', 'call_number']:
            patterns_count = filter_result.get('patterns_count', 0)
            if patterns_count > 0:
                if filter_type == 'title_keywords':
                    return f"{base_description}（{patterns_count}个关键词）"
                else:
                    return f"{base_description}（{patterns_count}个模式）"
        
        elif filter_type == 'column_value':
            # 对于列值筛选，根据配置动态生成描述
            return self._generate_column_value_description(filter_instance, filter_result)
        
        # 通用增强：如果有阈值信息，添加阈值说明
        threshold = filter_result.get('threshold')
        if threshold:
            return f"{base_description}（阈值:{threshold}）"
        
        return base_description
    
    def _infer_description(self, filter_name: str, filter_result: Dict[str, Any], filter_instance) -> str:
        """智能推断过滤原因描述
        
        Args:
            filter_name: 筛选器名称
            filter_result: 筛选结果信息
            filter_instance: 筛选器实例
            
        Returns:
            str: 推断的描述
        """
        filter_type = self._determine_filter_type_from_instance(filter_instance)
        
        if filter_type == 'hot_books':
            threshold = filter_result.get('threshold')
            if threshold:
                return f"热门书排除（借阅≥{threshold}次）"
            else:
                return "热门书排除（借阅频率过高）"
        
        elif filter_type == 'title_keywords':
            patterns_count = filter_result.get('patterns_count', 0)
            return f"题名关键词排除（{patterns_count}个关键词）"
        
        elif filter_type == 'call_number':
            patterns_count = filter_result.get('patterns_count', 0)
            return f"索书号/CLC号模式排除（{patterns_count}个模式）"
        
        elif filter_type == 'column_value':
            return self._generate_column_value_description(filter_instance, filter_result)
        
        # 默认返回智能生成的描述
        target_column = filter_result.get('target_column')
        if target_column:
            return f"列值筛选[{target_column}]"
        
        return filter_name
    
    def _determine_filter_type_from_instance(self, filter_instance) -> str:
        """从筛选器实例确定筛选器类型
        
        Args:
            filter_instance: 筛选器实例
            
        Returns:
            str: 筛选器类型
        """
        # 根据实例的类名推断类型
        class_name = filter_instance.__class__.__name__
        
        if 'HotBooks' in class_name:
            return 'hot_books'
        elif 'TitleKeywords' in class_name:
            return 'title_keywords'
        elif 'CallNumber' in class_name:
            return 'call_number'
        elif 'ColumnValue' in class_name:
            return 'column_value'
        
        # 尝试从配置推断
        config = getattr(filter_instance, 'config', {})
        target_column = config.get('target_column', '')
        target_columns = config.get('target_columns', [])
        
        if target_column or target_columns:
            if '题名' in str(target_column) or '题名' in str(target_columns):
                return 'title_keywords'
            elif '索书号' in str(target_column) or 'CLC' in str(target_column):
                return 'call_number'
            else:
                return 'column_value'
        
        return 'unknown'
    
    def _generate_column_value_description(self, filter_instance, filter_result: Dict[str, Any]) -> str:
        """为列值筛选器生成智能描述
        
        Args:
            filter_instance: 筛选器实例
            filter_result: 筛选结果信息
            
        Returns:
            str: 列值筛选描述
        """
        config = getattr(filter_instance, 'config', {})
        target_column = filter_result.get('target_column') or config.get('target_column', '')
        filter_type = config.get('filter_type', '')
        
        if '附加信息' in str(target_column):
            return "附加信息9位数字格式校验"
        elif '备注' in str(target_column):
            return "备注列排除指定关键词"
        elif '类型' in str(target_column):
            return "类型/册数列排除指定内容"
        elif filter_type == 'regex':
            pattern = config.get('pattern', '')
            if pattern:
                return f"正则表达式筛选[{target_column}: {pattern[:20]}...]"
            else:
                return f"正则表达式筛选[{target_column}]"
        elif filter_type == 'exclude_contains':
            exclude_patterns = config.get('exclude_patterns', [])
            if exclude_patterns:
                return f"关键词排除[{target_column}: {', '.join(exclude_patterns[:3])}]"
            else:
                return f"关键词排除[{target_column}]"
        else:
            return f"列值筛选[{target_column}]"
    
    def filter_books(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """执行完整的筛选流程
        
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]: (筛选后数据, 被过滤数据, 统计信息)
        """
        logger.info(f"开始智能降噪筛选，原始数据: {len(data)} 条记录")
        
        # 验证输入数据
        if data is None or len(data) == 0:
            logger.warning("输入数据为空")
            return data, pd.DataFrame(), {}
        
        original_data = data.copy()
        result_data = data.copy()
        excluded_data = pd.DataFrame()
        all_excluded_indices = set()
        total_excluded = 0
        
        # 记录每条记录被过滤的原因：{索引: 过滤原因列表}
        exclusion_reasons = {}
        
        for filter_name, filter_instance in self.filters:
            if filter_instance.enabled:
                try:
                    # 记录筛选前数据的索引
                    before_indices = set(result_data.index)
                    
                    result_data, filter_result = filter_instance.apply(result_data)
                    self.filter_results[filter_name] = filter_result
                    
                    # 获取筛选后数据的索引
                    after_indices = set(result_data.index)
                    
                    # 计算本次筛选被排除的索引
                    excluded_indices = before_indices - after_indices
                    all_excluded_indices.update(excluded_indices)
                    
                    # 为被排除的记录添加过滤原因
                    filter_reason = self._get_filter_reason_description(filter_name, filter_result, filter_instance)
                    for index in excluded_indices:
                        if index not in exclusion_reasons:
                            exclusion_reasons[index] = []
                        exclusion_reasons[index].append(filter_reason)
                    
                    # 统计排除数量
                    excluded_count = filter_result.get('excluded_count', 0)
                    total_excluded += excluded_count
                    
                    logger.info(f"筛选器 '{filter_name}' 执行完成，排除 {excluded_count} 条记录")
                except Exception as e:
                    logger.error(f"筛选器 '{filter_name}' 执行失败: {e}")
                    self.filter_results[filter_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
        
        # 获取所有被过滤的数据，并添加过滤原因列
        if all_excluded_indices:
            excluded_data = original_data.loc[list(all_excluded_indices)].copy()
            # 添加过滤原因列
            excluded_data['过滤原因'] = excluded_data.index.map(
                lambda idx: ' | '.join(exclusion_reasons.get(idx, ['未知原因']))
            )
            # 添加过滤时间列
            from datetime import datetime
            excluded_data['过滤时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            excluded_data = pd.DataFrame(columns=original_data.columns)
            excluded_data['过滤原因'] = []
            excluded_data['过滤时间'] = []
        
        # 生成总体统计信息
        summary = {
            'original_count': len(original_data),
            'filtered_count': len(result_data),
            'excluded_count': len(excluded_data),
            'total_excluded': total_excluded,
            'exclusion_ratio': len(excluded_data) / len(original_data) if len(original_data) > 0 else 0,
            'filter_results': self.filter_results,
            'exclusion_reasons': exclusion_reasons
        }
        
        logger.info(f"智能降噪筛选完成: {len(original_data)} -> {len(result_data)} 条记录 (排除 {len(excluded_data)} 条)")
        
        return result_data, excluded_data, summary
    
    def generate_report(self, data: pd.DataFrame) -> str:
        """生成筛选报告"""
        if not self.filter_results:
            return "没有筛选结果"
        
        report = []
        report.append("=" * 60)
        report.append("书海回响 - 智能降噪筛选报告")
        report.append("=" * 60)
        report.append(f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"筛选后数据: {len(data)} 条记录")
        
        # 统计列信息
        available_columns = list(data.columns)
        report.append(f"可用Excel列: {available_columns}")
        report.append("")
        
        # 配置验证结果
        report.append("配置验证结果:")
        valid_configs = 0
        for filter_name, result in self.filter_results.items():
            if result.get('status') != 'skipped':
                valid_configs += 1
                status = "✅" if result.get('status') != 'error' else "❌"
                report.append(f"  {status} {filter_name}: {result.get('description', 'N/A')}")
        
        report.append("")
        
        # 详细规则报告
        for filter_name, result in self.filter_results.items():
            if result.get('status') in ['completed', 'skipped']:
                report.append(f"{filter_name}:")
                report.append(f"  描述: {result.get('description', 'N/A')}")
                report.append(f"  排除数量: {result.get('excluded_count', 0)} 条记录")
                report.append(f"  排除比例: {result.get('excluded_ratio', 0):.2%}")
                
                if result.get('patterns_count'):
                    report.append(f"  模式数量: {result.get('patterns_count')}")
                
                if result.get('target_column'):
                    report.append(f"  目标列: {result.get('target_column')}")
                
                if result.get('threshold'):
                    report.append(f"  筛选阈值: {result.get('threshold')}")
                
                report.append("")
        
        return "\n".join(report)