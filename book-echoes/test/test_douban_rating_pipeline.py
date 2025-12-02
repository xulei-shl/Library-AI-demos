#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DoubanRatingPipeline 输出路径生成逻辑测试."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.douban.pipelines.douban_rating_pipeline import DoubanRatingPipeline


def _freeze_timestamp(monkeypatch: pytest.MonkeyPatch) -> str:
    """将 pandas 时间戳冻结到固定值，方便断言输出."""
    fixed = pd.Timestamp("2025-12-02 11:06:05")
    monkeypatch.setattr(
        pd.Timestamp,
        "now",
        classmethod(lambda cls: fixed),
    )
    return fixed.strftime("%Y%m%d_%H%M%S")


@pytest.fixture
def pipeline() -> DoubanRatingPipeline:
    """提供无需实际配置的 DoubanRatingPipeline 实例."""
    return DoubanRatingPipeline(config_manager=object())


def test_build_output_path_without_partial_suffix(
    pipeline: DoubanRatingPipeline,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """普通输入文件应直接在末尾附加豆瓣结果标识."""
    timestamp = _freeze_timestamp(monkeypatch)
    source = tmp_path / "数据筛选结果_20251201_162727.xlsx"
    source.touch()

    result = pipeline._build_output_path(source)

    assert (
        result.name
        == f"数据筛选结果_20251201_162727_豆瓣结果_{timestamp}.xlsx"
    )


def test_build_output_path_strips_partial_suffix(
    pipeline: DoubanRatingPipeline,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """partial 续跑的输入应去掉 _partial 再生成最终文件名."""
    timestamp = _freeze_timestamp(monkeypatch)
    source = tmp_path / "数据筛选结果_20251201_162727_partial.xlsx"
    source.touch()

    result = pipeline._build_output_path(source)

    assert (
        result.name
        == f"数据筛选结果_20251201_162727_豆瓣结果_{timestamp}.xlsx"
    )
