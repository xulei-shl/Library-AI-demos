#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从交叉分析 Markdown 报告中提取检索资产。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from src.utils.logger import get_logger

try:  # 延迟导入，避免在无 LLM 依赖时抛错
    from src.utils.llm.client import UnifiedLLMClient
except ImportError:  # pragma: no cover
    UnifiedLLMClient = None  # type: ignore

logger = get_logger(__name__)

SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
NAME_PATTERN = re.compile(r"-\s*名称[:：]\s*(.+)")
KEYWORDS_PATTERN = re.compile(r"-\s*关键词[:：]\s*(.+)")
SUMMARY_PATTERN = re.compile(r"-\s*摘要[:：]\s*(.+)")
TAG_LINE_PATTERN = re.compile(r"\|\s*标签\s*\|\s*(.+?)\s*\|")
BOOK_LINE_PATTERN = re.compile(r"\|\s*提及书籍\s*\|\s*(.+?)\s*\|")
BULLET_LINE_PATTERN = re.compile(r"^-\s+(.*)")

DEFAULT_PRIORITY = ["primary", "tags", "insight", "books"]
DEFAULT_EXPANSION_TASK = "query_assets_expansion"


@dataclass
class QueryPackage:
    """封装检索所需的多子查询集合。"""

    primary: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    insight: List[str] = field(default_factory=list)
    books: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, List[str]]:
        """以字典形式返回全部子查询。"""

        return {
            "primary": list(self.primary),
            "tags": list(self.tags),
            "insight": list(self.insight),
            "books": list(self.books),
        }

    def iter_queries(self, priority: Optional[Sequence[str]] = None) -> Iterable[Tuple[str, str]]:
        """按照优先级遍历所有子查询。"""

        order = priority or DEFAULT_PRIORITY
        for bucket in order:
            for query_text in getattr(self, bucket, []):
                yield bucket, query_text

    def count(self) -> int:
        """统计查询总数。"""

        return sum(len(values) for values in self.as_dict().values())


class MarkdownAssetParser:
    """解析交叉分析 Markdown 报告以构建 `QueryPackage`。"""

    def __init__(self, md_path: Path | str):
        self.md_path = Path(md_path)
        if not self.md_path.exists():
            raise FileNotFoundError(f"Markdown 文件不存在: {self.md_path}")

    def parse(self, expand_with_llm: bool = False, llm_client: Optional["UnifiedLLMClient"] = None,
              expansion_task: str = DEFAULT_EXPANSION_TASK) -> QueryPackage:
        """读取 Markdown 文件并返回查询包。"""

        content = self.md_path.read_text(encoding="utf-8")
        primary = self._extract_primary_queries(content)
        tags = self._extract_tags(content)
        insight = self._extract_insights(content)
        books = self._extract_books(content)

        package = QueryPackage(primary=primary, tags=tags, insight=insight, books=books)
        if expand_with_llm and llm_client:
            self._augment_with_llm(package, llm_client, expansion_task)
        return package

    def _extract_primary_queries(self, content: str) -> List[str]:
        section = self._extract_section(content, "共同母题")
        if not section:
            return []
        candidates: List[str] = []
        name = self._search_line(NAME_PATTERN, section)
        summary = self._search_line(SUMMARY_PATTERN, section)
        keywords = self._split_list_text(self._search_line(KEYWORDS_PATTERN, section))
        if summary:
            candidates.append(summary)
        if name:
            candidates.append(name)
        candidates.extend(keywords)
        return self._deduplicate(candidates)

    def _extract_tags(self, content: str) -> List[str]:
        matches = TAG_LINE_PATTERN.findall(content)
        tags: List[str] = []
        for raw in matches:
            tags.extend(self._split_list_text(raw))
        return self._deduplicate(tags)

    def _extract_books(self, content: str) -> List[str]:
        matches = BOOK_LINE_PATTERN.findall(content)
        books: List[str] = []
        for raw in matches:
            values = self._split_list_text(raw)
            books.extend(values)
        return self._deduplicate([b for b in books if b and b not in {"无", "none", "None"}])

    def _extract_insights(self, content: str) -> List[str]:
        section = self._extract_section(content, "深度洞察")
        if not section:
            return []
        insights = [match.group(1).strip() for match in BULLET_LINE_PATTERN.finditer(section)]
        return self._deduplicate(insights)

    def _augment_with_llm(self, package: QueryPackage, llm_client: "UnifiedLLMClient", task_name: str) -> None:
        """调用 LLM 将关键词或洞察改写为更易检索的提示语。"""

        payload = {
            "primary": package.primary,
            "tags": package.tags,
            "insight": package.insight,
        }
        prompt_messages = [{
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False)
        }]
        try:
            response = llm_client.generate_json(task_name=task_name, messages=prompt_messages)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("LLM 扩写失败，使用原始查询: %s", exc)
            return
        for bucket in ("primary", "tags", "insight"):
            rewritten = response.get(bucket)
            if isinstance(rewritten, list):
                combined = list(rewritten) + getattr(package, bucket)
                setattr(package, bucket, self._deduplicate(combined))

    @staticmethod
    def _extract_section(content: str, heading: str) -> str:
        matches = list(SECTION_PATTERN.finditer(content))
        for idx, match in enumerate(matches):
            if match.group(1).strip() == heading:
                start = match.end()
                end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
                return content[start:end].strip()
        return ""

    @staticmethod
    def _search_line(pattern: re.Pattern[str], text: str) -> str:
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _split_list_text(raw: str) -> List[str]:
        if not raw:
            return []
        cleaned = raw.strip().strip("[]（）(){}")
        cleaned = cleaned.replace("'", "").replace('"', "")
        cleaned = cleaned.replace("‘", "").replace("’", "")
        cleaned = cleaned.replace("“", "").replace("”", "")
        cleaned = cleaned.replace("、", ",").replace("，", ",")
        cleaned = cleaned.replace("；", ",")
        candidates = [item.strip().strip("《》“”""'") for item in cleaned.split(",")]
        return [item for item in candidates if item]

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for value in values:
            norm = value.strip()
            if not norm:
                continue
            if norm in seen:
                continue
            seen.add(norm)
            ordered.append(norm)
        return ordered


def build_query_package_from_md(md_path: Path | str, expand_with_llm: bool = False,
                                llm_client: Optional["UnifiedLLMClient"] = None,
                                expansion_task: str = DEFAULT_EXPANSION_TASK) -> QueryPackage:
    """便捷函数：直接从 Markdown 文件构建查询包。"""

    parser = MarkdownAssetParser(md_path)
    return parser.parse(
        expand_with_llm=expand_with_llm,
        llm_client=llm_client,
        expansion_task=expansion_task,
    )
