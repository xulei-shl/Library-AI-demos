"""JSON 解析与修复工具。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Union

from src.utils.logger import get_logger

logger = get_logger(__name__)


FENCE_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]+?)```", re.IGNORECASE)
OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")
ARRAY_PATTERN = re.compile(r"\[[\s\S]*\]")


class JSONHandler:
    """尽量容错地解析模型返回。"""

    def parse_response(
        self,
        text: str,
        enable_repair: bool = True,
        strict_mode: bool = False,
    ) -> Optional[Union[Dict[str, Any], List[Any]]]:
        if not text:
            return None

        raw = text.strip()
        logger.debug("尝试解析 JSON，原始长度=%s", len(raw))

        for candidate in self._candidate_texts(raw):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        if enable_repair:
            repaired = self._repair(raw)
            if repaired is not None:
                return repaired

        if strict_mode:
            return None

        try:
            return json.loads(raw)
        except Exception:
            logger.warning("JSON 解析失败，返回 None")
            return None

    def format_output(self, data: Any, output_format: str = "json") -> Any:
        if output_format == "dict":
            return data
        return json.dumps(data, ensure_ascii=False)

    def _candidate_texts(self, text: str) -> List[str]:
        candidates: List[str] = []

        fence = FENCE_PATTERN.search(text)
        if fence:
            candidates.append(fence.group(1).strip())

        obj = self._balanced_extract(text, "{", "}")
        if obj:
            candidates.append(obj)

        arr = self._balanced_extract(text, "[", "]")
        if arr:
            candidates.append(arr)

        if not candidates:
            candidates.append(text)
        return candidates

    def _balanced_extract(self, text: str, left: str, right: str) -> Optional[str]:
        depth = 0
        start = -1
        for idx, ch in enumerate(text):
            if ch == left:
                if depth == 0:
                    start = idx
                depth += 1
            elif ch == right and depth:
                depth -= 1
                if depth == 0 and start != -1:
                    return text[start : idx + 1]
        return None

    def _repair(self, text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
        # 简化版修复：补全末尾引号/括号
        cleaned = text.strip()
        cleaned = cleaned.replace("\u0000", "")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        sanitized = self._sanitize_json_like(cleaned)
        if sanitized and sanitized != cleaned:
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                logger.debug("基于字符清洗的 JSON 修复失败")

        # 尝试截断到最后一个完整的 } 或 ]
        end_obj = cleaned.rfind("}")
        end_arr = cleaned.rfind("]")
        end = max(end_obj, end_arr)
        if end != -1:
            snippet = cleaned[: end + 1]
            try:
                return json.loads(snippet)
            except Exception:
                logger.debug("截断修复失败")

        return None

    def _sanitize_json_like(self, text: str) -> str:
        allowed_literals = {"true", "false", "null"}
        result: List[str] = []
        literal_buffer: List[str] = []
        in_string = False
        escape = False

        def flush_literal() -> None:
            nonlocal literal_buffer
            if not literal_buffer:
                return
            literal = "".join(literal_buffer)
            lowered = literal.lower()
            if lowered in allowed_literals:
                result.append(lowered)
            literal_buffer = []

        for idx, ch in enumerate(text):
            if in_string:
                result.append(ch)
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                flush_literal()
                result.append(ch)
                in_string = True
                escape = False
                continue

            if ch.isalpha():
                if ch in "eE" and self._looks_like_exponent(result, text, idx):
                    flush_literal()
                    result.append(ch)
                else:
                    literal_buffer.append(ch)
                continue

            flush_literal()

            if ch.isdigit() or ch in " \t\r\n:-+.,{}[]":
                result.append(ch)
            elif ch in '\\/':
                result.append(ch)

        flush_literal()
        return "".join(result)

    def _looks_like_exponent(self, built: List[str], text: str, idx: int) -> bool:
        prev_char = None
        for ch in reversed(built):
            if ch.strip() == "":
                continue
            prev_char = ch
            break
        if prev_char is None or not (prev_char.isdigit() or prev_char == "."):
            return False

        next_idx = idx + 1
        if next_idx < len(text) and text[next_idx] in "+-":
            next_idx += 1
        return next_idx < len(text) and text[next_idx].isdigit()
