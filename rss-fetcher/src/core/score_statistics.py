"""LLM评分统计分析模块

本模块负责对文章LLM评分进行统计分析，生成分数段分布报告。
功能单一，高内聚低耦合。
"""

import os
from typing import List, Dict, Any
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScoreStatistics:
    """LLM评分统计分析器"""
    
    # 定义分数段（不重叠）
    SCORE_RANGES = [
        ("95以上", 95, float('inf')),
        ("94-93", 93, 95),
        ("92-91", 91, 93),
        ("90", 90, 91),
        ("89-85", 85, 90),
        ("85以下", 0, 85)
    ]
    
    def __init__(self):
        """初始化统计分析器"""
        pass
    
    def analyze_scores(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析文章评分分布
        
        Args:
            articles: 文章列表，每篇文章包含 llm_score 字段
            
        Returns:
            统计结果字典，包含各分数段的数量和百分比
        """
        logger.info("开始进行LLM评分统计分析...")
        
        # 提取有效评分
        valid_scores = []
        for article in articles:
            score = article.get("llm_score")
            
            # 过滤无效评分
            if score is None:
                continue
            
            # 处理字符串类型的评分
            if isinstance(score, str):
                score_str = score.strip().lower()
                if score_str in ('', 'nan', 'none'):
                    continue
                try:
                    score = float(score_str)
                except (ValueError, TypeError):
                    continue
            
            # 转换为数值
            try:
                score = float(score)
                # 只统计有效分数（大于0）
                if score > 0:
                    valid_scores.append(score)
            except (ValueError, TypeError):
                continue
        
        total_valid = len(valid_scores)
        logger.info(f"共找到 {total_valid} 篇有效评分的文章")
        
        if total_valid == 0:
            logger.warning("没有找到有效的评分数据")
            return {
                "total_articles": len(articles),
                "valid_scores": 0,
                "score_distribution": {},
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # 统计各分数段
        distribution = {}
        for range_name, min_score, max_score in self.SCORE_RANGES:
            count = sum(1 for score in valid_scores if min_score <= score < max_score)
            percentage = (count / total_valid * 100) if total_valid > 0 else 0
            
            distribution[range_name] = {
                "count": count,
                "percentage": percentage,
                "range": f"{min_score}-{max_score if max_score != float('inf') else '∞'}"
            }
            
            logger.info(f"分数段 {range_name}: {count} 篇 ({percentage:.1f}%)")
        
        # 计算统计信息
        avg_score = sum(valid_scores) / total_valid if total_valid > 0 else 0
        max_score_val = max(valid_scores) if valid_scores else 0
        min_score_val = min(valid_scores) if valid_scores else 0
        
        result = {
            "total_articles": len(articles),
            "valid_scores": total_valid,
            "score_distribution": distribution,
            "statistics": {
                "average": round(avg_score, 2),
                "max": max_score_val,
                "min": min_score_val
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        logger.info(f"统计完成: 平均分={avg_score:.2f}, 最高分={max_score_val}, 最低分={min_score_val}")
        
        return result
    
    def generate_report(self, statistics: Dict[str, Any], output_path: str) -> str:
        """
        生成统计报告文本文件
        
        Args:
            statistics: 统计结果字典
            output_path: 输出文件路径
            
        Returns:
            生成的报告文件路径
        """
        logger.info(f"生成统计报告: {output_path}")
        
        # 构建报告内容
        lines = []
        lines.append("=" * 60)
        lines.append("LLM文章评分统计分析报告")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"生成时间: {statistics['timestamp']}")
        lines.append(f"文章总数: {statistics['total_articles']}")
        lines.append(f"有效评分: {statistics['valid_scores']}")
        lines.append("")
        
        # 添加统计信息
        if "statistics" in statistics:
            stats = statistics["statistics"]
            lines.append("评分统计:")
            lines.append(f"  平均分: {stats['average']}")
            lines.append(f"  最高分: {stats['max']}")
            lines.append(f"  最低分: {stats['min']}")
            lines.append("")
        
        # 添加分数段分布
        lines.append("分数段分布:")
        lines.append("-" * 60)
        lines.append(f"{'分数段':<15} {'数量':<10} {'占比':<10} {'范围':<20}")
        lines.append("-" * 60)
        
        distribution = statistics.get("score_distribution", {})
        
        # 按照预定义的顺序输出
        for range_name, _, _ in self.SCORE_RANGES:
            if range_name in distribution:
                data = distribution[range_name]
                count = data["count"]
                percentage = data["percentage"]
                range_str = data["range"]
                lines.append(f"{range_name:<15} {count:<10} {percentage:>6.1f}%    {range_str:<20}")
        
        lines.append("-" * 60)
        lines.append("")
        lines.append("=" * 60)
        
        # 写入文件
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            logger.info(f"报告已保存至: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise
    
    def run_analysis(self, articles: List[Dict[str, Any]], excel_path: str) -> str:
        """
        执行完整的统计分析流程
        
        Args:
            articles: 文章列表
            excel_path: Excel文件路径（用于确定报告保存位置）
            
        Returns:
            生成的报告文件路径
        """
        # 分析评分
        statistics = self.analyze_scores(articles)
        
        # 生成报告文件路径（与Excel同目录，同名但扩展名为.txt）
        base_path = os.path.splitext(excel_path)[0]
        report_path = f"{base_path}_评分统计报告.txt"
        
        # 生成报告
        return self.generate_report(statistics, report_path)
