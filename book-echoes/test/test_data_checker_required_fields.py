#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DataChecker 必填字段判定单元测试."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import sys

# 将项目根目录加入路径，便于导入 src 模块
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from src.core.douban.database.data_checker import DataChecker


class _FakeDBManager:
    """用于注入的伪造数据库管理器."""

    def __init__(self, duplicate_payload: Dict[str, Any]) -> None:
        self._duplicate_payload = duplicate_payload

    def batch_check_duplicates(self, *_, **__) -> Dict[str, Any]:
        return self._duplicate_payload


def _build_excel_rows() -> List[Dict[str, Any]]:
    """构造最小化的 Excel 行数据."""
    return [
        {
            "书目条码": "B001",
            "_index": 0,
        }
    ]


def test_data_checker_marks_incomplete_db_records_as_pending() -> None:
    """缺少必填字段的 existing_valid 应转入 existing_valid_incomplete."""
    payload = {
        "existing_valid": [
            {
                "barcode": "B001",
                "data": {
                    "barcode": "B001",
                    "douban_title": "",
                    "douban_summary": "简介",
                    "douban_cover_image": "",
                },
            }
        ],
        "existing_stale": [],
        "new": [],
    }
    fake_db = _FakeDBManager(payload)
    checker = DataChecker(
        fake_db,
        {
            "enabled": True,
            "required_fields": ["douban_title", "douban_summary", "douban_cover_image"],
        },
    )

    result = checker.check_and_categorize_books(_build_excel_rows())

    assert result["existing_valid"] == []
    assert len(result["existing_valid_incomplete"]) == 1
    assert result["existing_valid_incomplete"][0]["_needs_api_patch"] is True


def test_data_checker_keeps_complete_records_in_valid_bucket() -> None:
    """完整字段应维持在 existing_valid."""
    payload = {
        "existing_valid": [
            {
                "barcode": "B001",
                "data": {
                    "barcode": "B001",
                    "douban_title": "书名",
                    "douban_summary": "简介",
                    "douban_cover_image": "https://example.com/cover.jpg",
                },
            }
        ],
        "existing_stale": [],
        "new": [],
    }
    fake_db = _FakeDBManager(payload)
    checker = DataChecker(
        fake_db,
        {
            "enabled": True,
            "required_fields": ["douban_title", "douban_summary", "douban_cover_image"],
        },
    )

    result = checker.check_and_categorize_books(_build_excel_rows())

    assert len(result["existing_valid"]) == 1
    assert result["existing_valid_incomplete"] == []
