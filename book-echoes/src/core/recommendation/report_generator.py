#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Report generator for the Recommendation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from src.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class RecommendationMetrics:
    """Container for aggregated report data."""

    total_candidates: int
    
    # Initial Review Stats
    initial_passed: int
    initial_failed: int
    initial_error: int
    initial_pending: int
    
    # Runoff Stats
    runoff_promoted: int
    runoff_auto_promoted: int
    runoff_failed: int
    runoff_error: int
    runoff_pending: int
    
    # Final Review Stats
    final_passed: int
    final_failed: int
    final_error: int
    final_pending: int
    
    # Manual Review Stats
    manual_passed: int
    manual_failed: int
    
    # Distributions
    initial_fail_reasons: Dict[str, int] = field(default_factory=dict)
    runoff_fail_reasons: Dict[str, int] = field(default_factory=dict)
    final_fail_reasons: Dict[str, int] = field(default_factory=dict)


class RecommendationReportGenerator:
    """Generate text report for the Recommendation module."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        Initialize generator.

        Args:
            output_dir: Optional output directory, defaults to runtime/outputs.
        """
        self.output_dir = Path(output_dir) if output_dir else Path("runtime/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        excel_path: str,
    ) -> Path:
        """
        Build and write the report file.
        """
        df = pd.read_excel(excel_path)
        
        metrics = self._collect_metrics(df)
        report_lines = self._build_report_lines(metrics, excel_path)

        excel_path_obj = Path(excel_path)
        report_name = f"{excel_path_obj.stem}_评选报告_{datetime.now():%Y%m%d_%H%M%S}.txt"
        report_file = excel_path_obj.parent / report_name
        report_file.write_text("\n".join(report_lines), encoding="utf-8")
        logger.info("评选任务分析报告已生成: %s", report_file)
        return report_file

    def _collect_metrics(self, df: pd.DataFrame) -> RecommendationMetrics:
        """Collect and compute metrics used in the final report."""
        
        # Filter for candidates only
        if "候选状态" in df.columns:
            candidates = df[df["候选状态"] == "候选"].copy()
        else:
            candidates = df.copy()
            
        total_candidates = len(candidates)
        
        # Initial Review
        initial_res = candidates["初评结果"].fillna("").astype(str)
        initial_passed = (initial_res == "通过").sum()
        initial_failed = (initial_res == "未通过").sum()
        initial_error = initial_res.str.startswith("ERROR").sum()
        initial_pending = total_candidates - initial_passed - initial_failed - initial_error
        
        initial_fail_reasons = candidates[initial_res == "未通过"]["初评淘汰原因"].value_counts().to_dict()

        # Runoff (only for those passed initial)
        runoff_candidates = candidates[initial_res == "通过"]
        runoff_res = runoff_candidates["主题内决选结果"].fillna("").astype(str)
        
        runoff_promoted = (runoff_res == "晋级").sum()
        runoff_auto_promoted = (runoff_res == "自动晋级").sum()
        runoff_failed = (runoff_res == "未晋级").sum()
        runoff_error = runoff_res.str.startswith("ERROR").sum()
        runoff_pending = len(runoff_candidates) - runoff_promoted - runoff_auto_promoted - runoff_failed - runoff_error
        
        # Note: Runoff fail reasons might be in "主题内决选理由" for failed ones, but usually it's just "未晋级"
        # We can check if there is a specific reason column or just use the result
        
        # Final Review (only for those promoted/auto-promoted in runoff)
        final_candidates = runoff_candidates[runoff_res.isin(["晋级", "自动晋级"])]
        final_res = final_candidates["终评结果"].fillna("").astype(str)
        
        final_passed = (final_res == "通过").sum()
        final_failed = (final_res == "未通过").sum()
        final_error = final_res.str.startswith("ERROR").sum()
        final_pending = len(final_candidates) - final_passed - final_failed - final_error
        
        final_fail_reasons = final_candidates[final_res == "未通过"]["终评淘汰原因"].value_counts().to_dict()
        
        # Manual Review
        manual_passed = 0
        manual_failed = 0
        if "人工评选" in candidates.columns:
            manual_res = candidates["人工评选"].fillna("").astype(str)
            manual_passed = (manual_res == "通过").sum()
            manual_failed = (manual_res == "未通过").sum()

        return RecommendationMetrics(
            total_candidates=total_candidates,
            initial_passed=initial_passed,
            initial_failed=initial_failed,
            initial_error=initial_error,
            initial_pending=initial_pending,
            runoff_promoted=runoff_promoted,
            runoff_auto_promoted=runoff_auto_promoted,
            runoff_failed=runoff_failed,
            runoff_error=runoff_error,
            runoff_pending=runoff_pending,
            final_passed=final_passed,
            final_failed=final_failed,
            final_error=final_error,
            final_pending=final_pending,
            manual_passed=manual_passed,
            manual_failed=manual_failed,
            initial_fail_reasons=initial_fail_reasons,
            final_fail_reasons=final_fail_reasons,
        )

    def _build_report_lines(
        self,
        metrics: RecommendationMetrics,
        excel_path: str,
    ) -> list[str]:
        """Assemble the text report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=" * 70,
            "书海回响 · 大模型三级评选模块分析报告",
            "=" * 70,
            f"生成时间: {timestamp}",
            f"数据文件: {excel_path}",
            "",
            "【总体概览】",
            f"候选书目总数: {metrics.total_candidates}",
            "",
            "【第一级：初评阶段】",
            f"  - 通过: {metrics.initial_passed}",
            f"  - 未通过: {metrics.initial_failed}",
            f"  - 异常/错误: {metrics.initial_error}",
            f"  - 待处理: {metrics.initial_pending}",
            f"  - 通过率: {(metrics.initial_passed / metrics.total_candidates * 100) if metrics.total_candidates else 0:.2f}%",
        ]
        
        if metrics.initial_fail_reasons:
            lines.append("  - 主要淘汰原因分布:")
            for reason, count in sorted(metrics.initial_fail_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"    * {reason}: {count}")

        lines.extend([
            "",
            "【第二级：主题内决选阶段】",
            f"  - 晋级: {metrics.runoff_promoted}",
            f"  - 自动晋级: {metrics.runoff_auto_promoted}",
            f"  - 未晋级: {metrics.runoff_failed}",
            f"  - 异常/错误: {metrics.runoff_error}",
            f"  - 待处理: {metrics.runoff_pending}",
            f"  - 总晋级数: {metrics.runoff_promoted + metrics.runoff_auto_promoted}",
        ])

        lines.extend([
            "",
            "【第三级：终评阶段】",
            f"  - 通过: {metrics.final_passed}",
            f"  - 未通过: {metrics.final_failed}",
            f"  - 异常/错误: {metrics.final_error}",
            f"  - 待处理: {metrics.final_pending}",
        ])
        
        if metrics.final_fail_reasons:
            lines.append("  - 主要淘汰原因分布:")
            for reason, count in sorted(metrics.final_fail_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"    * {reason}: {count}")

        if metrics.manual_passed > 0 or metrics.manual_failed > 0:
             lines.extend([
                "",
                "【人工复核情况】",
                f"  - 人工确认通过: {metrics.manual_passed}",
                f"  - 人工确认未通过: {metrics.manual_failed}",
            ])

        lines.extend([
            "",
            "【说明】",
            "1. 统计范围仅限“候选状态”为“候选”的书目。",
            "2. 各阶段数据基于当前Excel文件状态统计。",
            "3. “待处理”指在前一阶段通过但本阶段尚未有结果的数据。",
        ])

        return lines
