"""文章总结调度器"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.analysis.summary_agent import ArticleSummaryAgent
from src.core.storage import StorageManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ArticleSummaryRunner:
    """负责筛选文章并执行总结"""

    def __init__(
        self,
        storage: StorageManager,
        summary_agent: Optional[ArticleSummaryAgent] = None,
        max_attempts: int = 2,
    ):
        """初始化 Runner

        Args:
            storage: 存储管理器
            summary_agent: 可注入的总结 Agent
            max_attempts: 最大尝试次数（包含首轮）
        """
        self.storage = storage
        self.summary_agent = summary_agent or ArticleSummaryAgent()
        self.max_attempts = max(1, max_attempts)

    def run(self, input_file: Optional[str] = None) -> Optional[str]:
        """执行总结流程"""
        filepath = input_file or self.storage.find_latest_stage_file("analyze")
        if not filepath:
            logger.error("未找到 analyze 阶段输出文件，无法执行总结")
            return None

        articles = self.storage.load_stage_data("analyze", filepath)
        if not articles:
            logger.error(f"文件 {filepath} 无可用数据")
            return filepath

        pending = self._select_pending_articles(articles)
        if not pending:
            logger.info("没有需要总结的文章")
            return filepath

        logger.info(f"待总结文章: {len(pending)} 篇")
        failed = self._process_batch(pending, filepath, attempt=1)

        attempt = 2
        while failed and attempt <= self.max_attempts:
            logger.info(f"开始兜底重试, 本轮待处理 {len(failed)} 篇 (第{attempt}次尝试)")
            failed = self._process_batch(failed, filepath, attempt=attempt)
            attempt += 1

        if failed:
            logger.warning(f"仍有 {len(failed)} 篇文章总结失败，可下次运行时继续重试")

        return filepath

    def _select_pending_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """筛选需要总结的文章"""
        pending = []
        for article in articles:
            if not self._is_true(article.get("filter_pass")):
                continue

            status = str(article.get("llm_summary_status", "") or "").strip()
            summary_text = str(article.get("llm_summary", "") or "").strip()
            llm_status = str(article.get("llm_status", "") or "").strip()
            filter_status = str(article.get("filter_status", "") or "").strip()

            # 添加调试日志：记录状态字段
            logger.debug(f"总结阶段状态检查 - 标题: {article.get('title', 'N/A')[:50]}...")
            logger.debug(f"  filter_pass: {article.get('filter_pass')}")
            logger.debug(f"  filter_status: '{filter_status}'")
            logger.debug(f"  llm_summary_status: '{status}'")
            logger.debug(f"  llm_summary存在: {bool(summary_text)}")

            if status == "成功" and summary_text:
                continue

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
            logger.info(f"总结文章: {title}")
            result = self.summary_agent.summarize(article)
            self._apply_result(article, result)
            article["llm_summary_last_try"] = self._current_timestamp()

            # 即时保存当前文章
            self.storage.save_analyze_results([article], filepath, skip_processed=False)

            if result.get("llm_summary_status") != "成功":
                failed_articles.append(article)

        logger.info(f"本轮完成: 成功 {len(articles) - len(failed_articles)}, 失败 {len(failed_articles)}")
        return failed_articles

    def _apply_result(self, article: Dict[str, Any], result: Dict[str, Any]) -> None:
        """将总结结果写回文章字典"""
        article["llm_summary"] = result.get("llm_summary", "")
        article["llm_summary_status"] = result.get("llm_summary_status", "")
        article["llm_summary_error"] = result.get("llm_summary_error", "")

    def _is_true(self, value: Any) -> bool:
        """统一判断布尔值"""
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return False
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized in {"true", "1", "yes", "y"}
        return False

    def _current_timestamp(self) -> str:
        """生成时间戳"""
        return datetime.now().isoformat(timespec="seconds")
