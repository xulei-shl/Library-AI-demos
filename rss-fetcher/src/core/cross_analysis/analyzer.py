"""文章交叉分析器主模块

协调主题聚类和报告生成的完整流程
"""

from typing import Dict, Any, List
from src.utils.logger import get_logger
from .theme_cluster import ThemeCluster
from .report_generator import ReportGenerator

logger = get_logger(__name__)


class CrossAnalyzer:
    """文章交叉分析器

    执行完整的文章交叉主题分析流程
    """

    def __init__(self, config: Dict[str, Any] = None):
        """初始化分析器

        Args:
            config: 配置参数
        """
        self.config = config or {}
        self.theme_cluster = ThemeCluster()
        self.report_generator = ReportGenerator()

    def _get_cross_config(self) -> Dict[str, Any]:
        """获取交叉配置，兼容旧版结构"""
        if not isinstance(self.config, dict):
            return {"score_threshold": 90, "batch_size": 10}

        cross_config = self.config.get("cross_analysis")
        if isinstance(cross_config, dict):
            source = cross_config
        else:
            # 兼容直接把 cross 配置放在根节点的旧写法
            source = self.config

        return {
            "score_threshold": source.get("score_threshold", 90),
            "batch_size": source.get("batch_size", 10)
        }

    async def analyze(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行完整的交叉分析流程

        Args:
            articles: 文章列表，每篇包含：
                - llm_score: LLM评分
                - llm_thematic_essence: 母题描述
                - title: 标题
                - url: 链接
                - 其他元数据

        Returns:
            {
                "success": bool,
                "has_common_theme": bool,
                "main_theme": Optional[Dict],  # 主要主题
                "candidate_themes": List[Dict],  # 候选主题
                "report_path": str,  # 报告文件路径
                "metadata": Dict  # 分析元数据
            }
        """
        try:
            logger.info(f"开始交叉分析，文章数量: {len(articles)}")

            # 步骤1: 主题聚类
            logger.info("执行主题聚类...")
            cross_conf = self._get_cross_config()
            batch_size = cross_conf.get("batch_size", 10)
            score_threshold = cross_conf.get("score_threshold", 90)
            cluster_result = await self.theme_cluster.cluster_themes(
                articles,
                batch_size=batch_size,
                score_threshold=score_threshold
            )

            if not cluster_result.get("success", False):
                logger.error("主题聚类失败")
                return {
                    "success": False,
                    "has_common_theme": False,
                    "main_theme": None,
                    "candidate_themes": [],
                    "report_path": "",
                    "metadata": {
                        "error": cluster_result.get("error", "未知错误"),
                        "article_count": len(articles)
                    }
                }

            # 步骤2: 生成报告
            logger.info("生成分析报告...")
            report_path = await self.report_generator.generate_report(
                articles, cluster_result
            )

            # 步骤3: 构建返回结果
            result = {
                "success": True,
                "has_common_theme": cluster_result.get("has_common_theme", False),
                "main_theme": cluster_result.get("main_theme"),
                "candidate_themes": cluster_result.get("candidate_themes", []),
                "report_path": report_path,
                "metadata": {
                    "article_count": len(articles),
                    "filtered_count": len([
                        a for a in articles if a.get("llm_score", 0) >= score_threshold
                    ]),
                    "analysis_time": cluster_result.get("analysis_time"),
                    "config": self.config
                }
            }

            logger.info(f"交叉分析完成，报告已保存至: {report_path}")
            return result

        except Exception as e:
            logger.error(f"交叉分析失败: {str(e)}")
            return {
                "success": False,
                "has_common_theme": False,
                "main_theme": None,
                "candidate_themes": [],
                "report_path": "",
                "metadata": {
                    "error": str(e),
                    "article_count": len(articles)
                }
            }
