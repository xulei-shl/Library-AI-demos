#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告生成步骤.

负责输出最终结果和生成处理报告。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import pandas as pd

from src.utils.logger import get_logger
from src.utils.time_utils import get_timestamp

if TYPE_CHECKING:
    from src.core.douban.progress_manager import ProgressManager

logger = get_logger(__name__)


class ReportGenerator:
    """报告生成器.

    负责：
    1. 输出最终 Excel 文件
    2. 生成处理报告
    """

    def __init__(self, output_dir: str = "runtime/outputs"):
        """初始化.

        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def finalize_output(
        self,
        df: pd.DataFrame,
        progress: "ProgressManager",
        excel_file: str,
    ) -> str:
        """输出最终结果.

        Args:
            df: 数据框
            progress: 进度管理器
            excel_file: 原始输入文件路径

        Returns:
            输出文件路径
        """
        # 删除临时列
        if "_normalized_isbn" in df.columns:
            df.drop(columns=["_normalized_isbn"], inplace=True)

        # 生成输出文件名
        timestamp = get_timestamp()
        input_stem = Path(excel_file).stem

        # 如果输入文件名包含 _partial，去掉这个后缀
        if input_stem.endswith("_partial"):
            input_stem = input_stem[:-8]

        output_file = self.output_dir / f"{input_stem}_ISBN_API结果_{timestamp}.xlsx"

        # 保存最终文件
        progress.finalize_output(output_file, df)

        return str(output_file)

    def generate_report(
        self,
        df: pd.DataFrame,
        output_file: str,
        total_records: int,
        isbn_stats: Dict[str, int],
        isbn_supplement_stats: Dict[str, int],
        api_stats: Dict[str, int],
        filter_stats: Dict[str, Any],
    ) -> str:
        """生成处理报告.

        Args:
            df: 数据框
            output_file: 输出文件路径
            total_records: 总记录数
            isbn_stats: ISBN 预处理统计
            isbn_supplement_stats: ISBN 补充统计
            api_stats: API 调用统计
            filter_stats: 评分过滤统计

        Returns:
            报告文件路径
        """
        timestamp = get_timestamp()
        report_file = self.output_dir / f"ISBN_API_处理报告_{timestamp}.txt"

        lines = [
            "=" * 60,
            "豆瓣 ISBN API 处理报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "【数据概览】",
            f"  总记录数: {total_records}",
            f"  有效 ISBN: {isbn_stats['valid']}",
            f"  无效 ISBN: {isbn_stats['invalid']}",
            "",
        ]

        # 添加 ISBN 补充统计
        if isbn_supplement_stats.get("total", 0) > 0 or isbn_supplement_stats.get("disabled"):
            lines.extend(["【ISBN 补充统计】"])
            if isbn_supplement_stats.get("disabled"):
                lines.append("  状态: 已禁用（配置关闭）")
            else:
                lines.extend([
                    f"  需补充记录: {isbn_supplement_stats.get('total', 0)}",
                    f"  成功补充: {isbn_supplement_stats.get('success', 0)}",
                    f"  补充失败: {isbn_supplement_stats.get('failed', 0)}",
                    f"  跳过: {isbn_supplement_stats.get('skipped', 0)}",
                ])
            lines.append("")

        # API 调用统计
        api_success = api_stats.get("success", 0)
        api_failed = api_stats.get("failed", 0)
        api_total = api_success + api_failed
        success_rate = (api_success / max(1, api_total)) * 100

        lines.extend([
            "【API 调用统计】",
            f"  成功获取: {api_success}",
            f"  未找到: {api_failed}",
            f"  跳过: {api_stats.get('skipped', 0)}",
            f"  成功率: {success_rate:.1f}%",
            "",
            "【评分过滤统计】",
            f"  候选图书数: {filter_stats.get('candidate_count', 0)}",
            f"  总样本数: {filter_stats.get('total_samples', 0)}",
            "",
            "【输出文件】",
            f"  Excel: {output_file}",
            "",
        ])

        # 添加分类统计
        if filter_stats.get("stats"):
            lines.append("【分类详情】")
            for stat in filter_stats["stats"]:
                lines.append(
                    f"  {stat['letter']}: "
                    f"总数={stat['total']}, "
                    f"候选={stat.get('candidate_count', 0)}, "
                    f"阈值={stat.get('score_threshold', 'N/A')}"
                )
            lines.append("")

        lines.append("=" * 60)

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"报告已生成: {report_file}")
        return str(report_file)
