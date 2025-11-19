#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串行流水线执行器
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Optional, Any

from src.utils.logger import get_logger
from .folio_isbn_pipeline import FolioIsbnPipeline, FolioIsbnPipelineOptions
from .douban_rating_pipeline import DoubanRatingPipeline, DoubanRatingPipelineOptions

logger = get_logger(__name__)


@dataclass
class PipelineExecutionOptions:
    """控制串行执行的配置"""

    excel_file: str
    folio_options: Optional[FolioIsbnPipelineOptions] = None
    douban_options: Optional[DoubanRatingPipelineOptions] = None


class PipelineRunner:
    """顺序执行 FOLIO -> 豆瓣 两个阶段"""

    def __init__(
        self,
        folio_pipeline: Optional[FolioIsbnPipeline] = None,
        douban_pipeline: Optional[DoubanRatingPipeline] = None,
    ):
        self.folio_pipeline = folio_pipeline or FolioIsbnPipeline()
        self.douban_pipeline = douban_pipeline or DoubanRatingPipeline()

    def run_full_pipeline(self, options: PipelineExecutionOptions) -> Dict[str, Any]:
        """顺序执行两阶段并返回结果摘要"""
        results: Dict[str, Any] = {}
        folio_opts = options.folio_options or FolioIsbnPipelineOptions(excel_file=options.excel_file)
        folio_output, folio_stats = self.folio_pipeline.run(folio_opts)
        results["folio"] = {
            "output": folio_output,
            "stats": folio_stats,
        }

        douban_opts = options.douban_options or DoubanRatingPipelineOptions(excel_file=folio_output)
        if douban_opts.excel_file != folio_output:
            douban_opts = replace(douban_opts, excel_file=folio_output)

        douban_output, douban_stats = self.douban_pipeline.run(douban_opts)
        results["douban"] = {
            "output": douban_output,
            "stats": douban_stats,
        }
        return results
