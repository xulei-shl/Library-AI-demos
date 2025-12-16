#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""封装图书检索 API 复用的服务层。"""

from __future__ import annotations

import os
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from src.core.book_vectorization.output_formatter import OutputFormatter
from src.core.book_vectorization.query_assets import (
    QueryPackage,
    build_query_package_from_md,
)
from src.core.book_vectorization.retriever import BookRetriever
from src.utils.config_manager import ConfigManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_PATH = "config/book_vectorization.yaml"
DEFAULT_TEMPLATE = "*- {title} by {author}"
VALID_RESPONSE_FORMATS = {"json", "plain_text"}


class RetrieverService:
    """整合配置、检索器与格式化器的服务层。"""

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH) -> None:
        """
        初始化服务。

        Args:
            config_path: 配置文件路径。
        """
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.raw_config = self.config_manager.get_config()
        self.retriever = BookRetriever(config_path)
        output_config = self.raw_config.get("output", {})
        self.output_formatter = OutputFormatter(output_config)
        self.default_text_top_k = self.config_manager.get(
            "search_defaults.text_top_k", 5
        )
        self.default_text_min_rating = self.config_manager.get(
            "search_defaults.text_min_rating", None
        )
        self.default_multi_per_query_top_k = self.config_manager.get(
            "multi_query.top_k_per_query", 15
        )
        self.default_multi_final_top_k = self.config_manager.get(
            "fusion.final_top_k", 15
        )

    def text_search(
        self,
        *,
        query: str,
        top_k: Optional[int] = None,
        min_rating: Optional[float] = None,
        response_format: str = "json",
        plain_text_template: Optional[str] = None,
        llm_hint: Optional[Dict[str, Any]] = None,
        save_to_file: bool = False,
    ) -> Dict[str, Any]:
        """
        执行文本相似度检索。

        Args:
            query: 查询文本。
            top_k: 返回结果数量。
            min_rating: 最低评分过滤。
            response_format: 响应格式。
            plain_text_template: 纯文本模版。
            llm_hint: LLM 侧提示信息。
            save_to_file: 是否落盘输出。
        """
        sanitized_query = (query or "").strip()
        if not sanitized_query:
            raise ValueError("query 不能为空")

        response_format = self._normalize_response_format(response_format)
        limit = top_k or self.default_text_top_k
        if limit <= 0:
            raise ValueError("top_k 必须为正整数")

        rating_filter = (
            min_rating if min_rating is not None else self.default_text_min_rating
        )
        logger.info(
            "API 文本检索: query_preview=%s, top_k=%s, min_rating=%s",
            sanitized_query[:60],
            limit,
            rating_filter,
        )

        results = self.retriever.search_by_text(
            query_text=sanitized_query, top_k=limit, min_rating=rating_filter
        )
        metadata = {
            "mode": "text_search",
            "query": sanitized_query,
            "top_k": limit,
            "min_rating": rating_filter,
        }
        payload = self._finalize_response(
            results=results,
            metadata=metadata,
            response_format=response_format,
            plain_text_template=plain_text_template,
            llm_hint=llm_hint,
            save_to_file=save_to_file,
        )
        return payload

    def multi_query_search(
        self,
        *,
        markdown_text: str,
        per_query_top_k: Optional[int] = None,
        final_top_k: Optional[int] = None,
        min_rating: Optional[float] = None,
        enable_rerank: bool = False,
        disable_exact_match: bool = False,
        response_format: str = "json",
        plain_text_template: Optional[str] = None,
        llm_hint: Optional[Dict[str, Any]] = None,
        save_to_file: bool = False,
    ) -> Dict[str, Any]:
        """
        执行 Markdown → 多子查询检索。

        Args:
            markdown_text: Markdown 文本。
            per_query_top_k: 单个子查询候选数量。
            final_top_k: 融合后返回数量。
            min_rating: 最低评分过滤。
            enable_rerank: 是否启用重排序。
            disable_exact_match: 是否禁用精确匹配。
            response_format: 响应格式。
            plain_text_template: 纯文本模版。
            llm_hint: LLM 侧提示信息。
            save_to_file: 是否落盘输出。
        """
        content = (markdown_text or "").strip()
        if not content:
            raise ValueError("markdown_text 不能为空")

        response_format = self._normalize_response_format(response_format)
        per_query_limit = per_query_top_k or self.default_multi_per_query_top_k
        final_limit = final_top_k or self.default_multi_final_top_k

        if per_query_limit <= 0 or final_limit <= 0:
            raise ValueError("top_k 参数必须为正整数")

        query_package = self._build_query_package(content, disable_exact_match)

        logger.info(
            "API 多子查询检索: origin=%s, per_query_top_k=%s, final_top_k=%s, rerank=%s, disable_exact_match=%s",
            query_package.origin,
            per_query_limit,
            final_limit,
            enable_rerank,
            disable_exact_match,
        )

        results = self.retriever.search_multi_query(
            query_package=query_package,
            min_rating=min_rating,
            per_query_top_k=per_query_limit,
            final_top_k=final_limit,
            rerank=enable_rerank,
        )
        metadata = {
            "mode": "multi_query",
            "query_package_origin": query_package.origin,
            "enable_rerank": enable_rerank,
            "disable_exact_match": disable_exact_match,
            "per_query_top_k": per_query_limit,
            "final_top_k": final_limit,
            "min_rating": min_rating,
        }
        response = self._finalize_response(
            results=results,
            metadata=metadata,
            response_format=response_format,
            plain_text_template=plain_text_template,
            llm_hint=llm_hint,
            save_to_file=save_to_file,
        )
        response["query_package"] = query_package.as_dict()
        response["query_package_metadata"] = dict(query_package.metadata)
        return response

    def _finalize_response(
        self,
        *,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        response_format: str,
        plain_text_template: Optional[str],
        llm_hint: Optional[Dict[str, Any]],
        save_to_file: bool,
    ) -> Dict[str, Any]:
        """统一构建响应结构。"""
        metadata = dict(metadata)
        metadata["response_format"] = response_format
        if llm_hint:
            metadata["llm_hint"] = llm_hint

        payload: Dict[str, Any] = {
            "results": results,
            "metadata": metadata,
        }

        if response_format == "plain_text":
            payload["context_plain_text"] = self._render_plain_text(
                results, plain_text_template
            )

        if save_to_file:
            saved_files = self._maybe_save_results(results, metadata)
            if saved_files:
                payload["saved_files"] = saved_files

        return payload

    def _render_plain_text(
        self, results: List[Dict[str, Any]], template: Optional[str]
    ) -> str:
        """根据模板输出纯文本内容。"""
        tpl = (template or DEFAULT_TEMPLATE).strip() or DEFAULT_TEMPLATE
        lines: List[str] = []
        for idx, item in enumerate(results, start=1):
            context = {
                "index": idx,
                "title": item.get("title")
                or item.get("douban_title")
                or f"未知书目{idx}",
                "author": item.get("author")
                or item.get("douban_author")
                or "未知作者",
                "rating": item.get("rating")
                or item.get("douban_rating")
                or "N/A",
                "summary": item.get("summary") or item.get("douban_summary") or "",
                "call_no": item.get("call_no", ""),
                "highlights": item.get("summary") or "",
            }
            try:
                lines.append(tpl.format(**context))
            except (KeyError, ValueError):
                fallback = DEFAULT_TEMPLATE.format(**context)
                lines.append(fallback)
        if not lines:
            return "未找到匹配书籍。"
        return "\n".join(lines)

    def _maybe_save_results(
        self, results: List[Dict[str, Any]], metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """根据配置可选落盘。"""
        if not getattr(self.output_formatter, "enabled", False):
            logger.info("输出格式化器未启用，跳过落盘")
            return {}
        try:
            return self.output_formatter.save_results(results, metadata)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("保存结果失败: %s", exc)
            return {}

    def _normalize_response_format(self, response_format: str) -> str:
        """校验响应格式。"""
        fmt = (response_format or "json").strip().lower()
        if fmt not in VALID_RESPONSE_FORMATS:
            raise ValueError("response_format 仅支持 json 或 plain_text")
        return fmt

    def _build_query_package(
        self, markdown_text: str, disable_exact_match: bool
    ) -> QueryPackage:
        """写入临时文件以复用既有解析逻辑。"""
        temp_path = None
        try:
            with NamedTemporaryFile(
                mode="w+",
                suffix=".md",
                delete=False,
                encoding="utf-8",
            ) as tmp_file:
                tmp_file.write(markdown_text)
                tmp_file.flush()
                temp_path = tmp_file.name
            package = build_query_package_from_md(temp_path)
            package.disable_exact_match = disable_exact_match
            return package
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    logger.warning("临时Markdown文件删除失败: %s", temp_path)

