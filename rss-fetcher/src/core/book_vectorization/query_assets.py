#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从交叉分析 Markdown 报告中提取检索资产。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

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
DEFAULT_RECOVERY_TASK = "query_assets_recovery"
RECOVERY_SYSTEM_PROMPT = (
    "你是 Markdown 解析兜底助手。给定原始 Markdown 文本，请提取可用于图书检索的关键信息，"
    "并严格输出 JSON，字段包含 keywords(主题短语)、query_sentences(检索句)、tags(标签)、books(书名)。"
    "若无法提取，请返回空数组。"
)


@dataclass
class QueryPackage:
    """封装检索所需的多子查询集合。"""

    primary: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    insight: List[str] = field(default_factory=list)
    books: List[str] = field(default_factory=list)
    origin: str = "parsed"
    metadata: Dict[str, str] = field(default_factory=dict)

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
        self._last_content: Optional[str] = None
        if not self.md_path.exists():
            raise FileNotFoundError(f"Markdown 文件不存在: {self.md_path}")

    def parse(self, expand_with_llm: bool = False, llm_client: Optional["UnifiedLLMClient"] = None,
              expansion_task: str = DEFAULT_EXPANSION_TASK) -> QueryPackage:
        """读取 Markdown 文件并返回查询包。"""

        content = self.md_path.read_text(encoding="utf-8")
        self._last_content = content
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

    def recover_with_llm(
        self,
        llm_client: Optional["UnifiedLLMClient"],
        task_name: str = DEFAULT_RECOVERY_TASK,
    ) -> Optional[QueryPackage]:
        """当 Markdown 解析为空时，通过 LLM 兜底生成查询。"""

        if not llm_client:
            logger.warning("未提供 LLM 客户端，无法执行兜底解析。")
            return None

        content = self._last_content or self.md_path.read_text(encoding="utf-8")
        payload = {
            "markdown": content,
            "requirements": {
                "keywords": "共同母题或主题关键词，长度不超过 10 个字",
                "query_sentences": "描述主题的检索句，适合作为语义检索输入",
                "tags": "与主题相关的标签或领域词",
                "books": "文中直接提到的代表性书名，可为空",
            },
        }
        prompt_messages = [
            {"role": "system", "content": RECOVERY_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

        start_ts = perf_counter()
        try:
            response = llm_client.generate_json(task_name=task_name, messages=prompt_messages)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("LLM 兜底失败: %s", exc)
            return None

        normalized = self._normalize_recovery_payload(response)
        if not normalized:
            logger.warning("LLM 兜底返回为空，保持原有解析结果。")
            return None

        package = QueryPackage(
            primary=self._deduplicate(normalized.get("primary", [])),
            tags=self._deduplicate(normalized.get("tags", [])),
            insight=self._deduplicate(normalized.get("insight", [])),
            books=self._deduplicate(normalized.get("books", [])),
            origin="llm_recovered",
        )
        if package.count() == 0:
            logger.warning("LLM 兜底未能生成有效查询，保持空结果。")
            return None

        elapsed_ms = int((perf_counter() - start_ts) * 1000)
        package.metadata = {
            "llm_task": task_name,
            "llm_latency_ms": str(elapsed_ms),
            "primary_count": str(len(package.primary)),
            "tags_count": str(len(package.tags)),
            "insight_count": str(len(package.insight)),
            "books_count": str(len(package.books)),
        }
        logger.info(
            "LLM 兜底生成查询: primary=%s, tags=%s, insight=%s, books=%s, latency_ms=%s",
            len(package.primary),
            len(package.tags),
            len(package.insight),
            len(package.books),
            elapsed_ms,
        )
        return package

    def _normalize_recovery_payload(self, response: Any) -> Dict[str, List[str]]:
        """容错解析 LLM 返回结果。"""

        if isinstance(response, str):
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                logger.warning("LLM 兜底返回非 JSON 文本，长度=%s", len(response))
                return {}
        elif isinstance(response, dict):
            parsed = response
        else:
            return {}

        keywords = self._ensure_list(parsed.get("keywords") or parsed.get("primary"))
        sentences = self._ensure_list(parsed.get("query_sentences") or parsed.get("insight"))
        tags = self._ensure_list(parsed.get("tags"))
        books = self._ensure_list(parsed.get("books"))
        return {
            "primary": keywords,
            "insight": sentences,
            "tags": tags,
            "books": books,
        }

    @staticmethod
    def _ensure_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

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


def build_query_package_from_md(
    md_path: Path | str,
    expand_with_llm: bool = False,
    llm_client: Optional["UnifiedLLMClient"] = None,
    expansion_task: str = DEFAULT_EXPANSION_TASK,
    enable_llm_fallback: bool = True,
    recovery_task: str = DEFAULT_RECOVERY_TASK,
) -> QueryPackage:
    """便捷函数：直接从 Markdown 文件构建查询包，必要时触发 LLM 兜底。"""

    parser = MarkdownAssetParser(md_path)
    package = parser.parse(
        expand_with_llm=expand_with_llm,
        llm_client=llm_client,
        expansion_task=expansion_task,
    )

    if package.count() == 0 and enable_llm_fallback:
        logger.warning("Markdown 解析结果为空，触发 LLM 兜底")
        client = llm_client
        if client is None and UnifiedLLMClient is not None:
            try:
                client = UnifiedLLMClient()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("LLM 客户端初始化失败，无法兜底: %s", exc)
        fallback_package = parser.recover_with_llm(client, task_name=recovery_task)
        if fallback_package:
            return fallback_package
        logger.warning("LLM 兜底失败或返回空结果，继续使用原始结果。")

    return package
