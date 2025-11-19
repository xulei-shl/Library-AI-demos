#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣流水线基类."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from src.core.douban.progress_manager import ProgressManager


@dataclass
class StageContext:
    df: pd.DataFrame
    progress_manager: ProgressManager
    douban_config: Dict[str, Any]
    full_config: Dict[str, Any]
    field_mapping: Dict[str, str]
    barcode_column: str
    isbn_column: str
    link_column: str
    status_column: str
    call_number_column: Optional[str] = None
    candidate_column: Optional[str] = None
    excel_path: Optional[Path] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def get_field(self, logical_key: str) -> str:
        return self.field_mapping.get(logical_key, logical_key)


class PipelineStep(ABC):
    name: str = "base"

    def prepare(self, context: StageContext) -> None:  # pragma: no cover - 默认空实现
        return None

    @abstractmethod
    def run(self, context: StageContext) -> Dict[str, Any]:
        raise NotImplementedError

    def finalize(self, context: StageContext) -> None:  # pragma: no cover - 默认空实现
        return None
