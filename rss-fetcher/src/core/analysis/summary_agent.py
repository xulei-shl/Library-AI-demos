"""文章总结 Agent"""

import json
from typing import Any, Dict

from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)


class ArticleSummaryAgent:
    """负责调用 LLM 生成结构化总结"""

    def __init__(self, task_name: str = "article_summary"):
        """初始化总结 Agent

        Args:
            task_name: LLM 任务名称, 对应 config/llm.yaml 的配置
        """
        self.task_name = task_name
        self.llm_client = UnifiedLLMClient()

    def summarize(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """对文章进行总结

        Args:
            article: 文章数据字典

        Returns:
            包含总结结果的字段:
            {
                "llm_summary": str,
                "llm_summary_status": str,
                "llm_summary_error": Optional[str]
            }
        """
        title = article.get("title") or "无标题"
        text_content = article.get("full_text") or article.get("content") or ""

        if not str(text_content).strip():
            logger.warning(f"文章 '{title}' 缺少可总结内容，跳过")
            return self._build_response("", "失败", "缺少可总结内容")

        user_prompt = self._build_prompt(article, text_content)

        try:
            result = self.llm_client.call(self.task_name, user_prompt)
            summary_text = self._normalize_result(result)

            if not summary_text:
                logger.error(f"文章 '{title}' 总结为空")
                return self._build_response("", "失败", "LLM返回为空")

            logger.info(f"文章 '{title}' 总结完成")
            return self._build_response(summary_text, "成功", None)
        except Exception as exc:
            logger.error(f"文章 '{title}' 总结失败: {exc}")
            return self._build_response("", "失败", str(exc))

    def _build_prompt(self, article: Dict[str, Any], text_content: str) -> str:
        """构造用户输入内容"""
        title = article.get("title") or "无标题"
        source = article.get("source") or "未知来源"
        author = article.get("author") or ""
        link = article.get("link") or ""

        segments = [
            f"标题: {title}",
            f"来源: {source}",
        ]

        if author:
            segments.append(f"作者: {author}")
        if link:
            segments.append(f"链接: {link}")

        segments.append("正文内容如下：")
        segments.append(text_content)

        return "\n\n".join(segments)

    def _normalize_result(self, result: Any) -> str:
        """统一 LLM 返回值格式"""
        if isinstance(result, str):
            return result.strip()

        try:
            return json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(result).strip()

    def _build_response(self, summary: str, status: str, error: str | None) -> Dict[str, Any]:
        """统一输出结构"""
        return {
            "llm_summary": summary,
            "llm_summary_status": status,
            "llm_summary_error": error,
        }
