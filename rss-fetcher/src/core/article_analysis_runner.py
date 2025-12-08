"""文章深度分析调度器"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.analysis.analyst import ArticleAnalyst
from src.core.storage import StorageManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ArticleAnalysisRunner:
    """负责筛选文章并执行深度分析

    筛选条件: llm_summary_status == "成功" 且 llm_analysis_status 非成功
    输入: llm_summary 字段内容
    输出: score, primary_dimension, reason, thematic_essence, tags, mentioned_books
    """

    def __init__(
        self,
        storage: StorageManager,
        analyst: Optional[ArticleAnalyst] = None,
        max_attempts: int = 2,
    ):
        """初始化 Runner

        Args:
            storage: 存储管理器
            analyst: 可注入的深度分析 Agent
            max_attempts: 最大尝试次数（包含首轮）
        """
        self.storage = storage
        self.analyst = analyst or ArticleAnalyst()
        self.max_attempts = max(1, max_attempts)

    def run(self, input_file: Optional[str] = None) -> Optional[str]:
        """执行深度分析流程"""
        filepath = input_file or self.storage.find_latest_stage_file("analyze")
        if not filepath:
            logger.error("未找到 analyze 阶段输出文件，无法执行深度分析")
            return None

        articles = self.storage.load_stage_data("analyze", filepath)
        if not articles:
            logger.error(f"文件 {filepath} 无可用数据")
            return filepath

        pending = self._select_pending_articles(articles)
        if not pending:
            logger.info("没有需要深度分析的文章")
            return filepath

        logger.info(f"待分析文章: {len(pending)} 篇")
        failed = self._process_batch(pending, filepath, attempt=1)

        attempt = 2
        while failed and attempt <= self.max_attempts:
            logger.info(f"开始兜底重试, 本轮待处理 {len(failed)} 篇 (第{attempt}次尝试)")
            failed = self._process_batch(failed, filepath, attempt=attempt)
            attempt += 1

        if failed:
            logger.warning(f"仍有 {len(failed)} 篇文章分析失败，可下次运行时继续重试")

        return filepath

    def _select_pending_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """筛选需要深度分析的文章

        条件: llm_summary_status == "成功" 且 llm_analysis_status 非成功
        """
        pending = []
        for article in articles:
            # 检查总结状态是否成功
            summary_status = str(article.get("llm_summary_status", "") or "").strip()
            if summary_status != "成功":
                continue

            # 检查是否有总结内容
            summary_text = str(article.get("llm_summary", "") or "").strip()
            if not summary_text:
                continue

            # 检查分析状态是否已成功
            analysis_status = str(article.get("llm_analysis_status", "") or "").strip()
            if analysis_status == "成功":
                continue

            # 添加调试日志：记录状态字段
            logger.debug(f"分析阶段状态检查 - 标题: {article.get('title', 'N/A')[:50]}...")
            logger.debug(f"  llm_summary_status: '{summary_status}'")
            logger.debug(f"  llm_summary存在: {bool(summary_text)}")
            logger.debug(f"  llm_analysis_status: '{analysis_status}'")
            logger.debug(f"  filter_status: '{article.get('filter_status', '')}'")

            pending.append(article)
        return pending

    def _process_batch(
        self,
        articles: List[Dict[str, Any]],
        filepath: str,
        attempt: int,
    ) -> List[Dict[str, Any]]:
        """处理一批文章并即时保存"""
        failed_articles: List[Dict[str, Any]] = []

        for article in articles:
            title = article.get("title", "无标题")
            logger.info(f"深度分析文章: {title}")

            # 从 llm_summary 获取输入内容
            summary_content = str(article.get("llm_summary", "") or "").strip()

            result = self.analyst.analyze(summary_content)
            self._apply_result(article, result)
            article["llm_analysis_last_try"] = self._current_timestamp()

            # 即时保存当前文章
            self.storage.save_analyze_results([article], filepath, skip_processed=False)

            if result.get("status") != "成功":
                failed_articles.append(article)

        logger.info(f"本轮完成: 成功 {len(articles) - len(failed_articles)}, 失败 {len(failed_articles)}")
        return failed_articles

    def _apply_result(self, article: Dict[str, Any], result: Dict[str, Any]) -> None:
        """将分析结果写回文章字典"""
        article["llm_score"] = result.get("score", 0)
        article["llm_primary_dimension"] = result.get("primary_dimension", "")
        article["llm_reason"] = result.get("reason", "")
        article["llm_thematic_essence"] = result.get("thematic_essence", "")
        article["llm_tags"] = result.get("tags", [])
        article["llm_mentioned_books"] = result.get("mentioned_books", [])
        article["llm_analysis_status"] = result.get("status", "")
        article["llm_analysis_error"] = result.get("error", "")

    def _current_timestamp(self) -> str:
        """生成时间戳"""
        return datetime.now().isoformat(timespec="seconds")
