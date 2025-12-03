#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新书评分过滤器

专为新书零借阅场景设计的简化评分过滤规则：
1. 不同学科（索书号首字母）的最低豆瓣评分
2. 豆瓣封面图片链接非空
3. 豆瓣内容简介非空
4. 豆瓣出版年为当年
5. 复用 config/filters 下的 txt 过滤规则
"""

import re
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.utils.rule_file_parser import CallNumberMatcher, TitleKeywordsMatcher
from src.utils.config_manager import get_config_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NewSleepingFilterResult:
    """新书评分过滤结果"""
    total_count: int                    # 总记录数
    candidate_count: int                # 候选数量
    excluded_count: int                 # 排除数量
    excluded_by_rating: int             # 评分不达标排除数
    excluded_by_required_fields: int    # 必填字段缺失排除数
    excluded_by_pub_year: int           # 出版年不符合排除数
    excluded_by_title_keywords: int     # 题名关键词排除数
    excluded_by_call_number: int        # 索书号规则排除数
    category_stats: Dict[str, Dict]     # 各学科统计


class NewSleepingRatingFilter:
    """新书评分过滤器"""

    # 默认配置
    DEFAULT_CONFIG = {
        "enabled": True,
        "allow_no_rating": True,  # 是否允许无评分书籍成为候选
        "category_min_scores": {
            "I": 7.5,
            "K": 8.0,
            "B": 8.0,
            "J": 7.8,
            "default": 7.2,
        },
        "required_fields": [
            {"column": "豆瓣封面图片链接", "description": "排除没有封面图片的图书"},
            {"column": "豆瓣内容简介", "description": "排除没有内容简介的图书"},
        ],
        "pub_year_filter": {
            "enabled": True,
            "mode": "current_year",
        },
        "reuse_filters": {
            "title_keywords": True,
            "call_number_clc": True,
        },
    }

    def __init__(self, config_manager=None):
        self._config_manager = config_manager or get_config_manager()
        self.config = self._load_config()
        self._call_letter_pattern = re.compile(r"[A-Za-z]")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        full_config = self._config_manager.get_config()
        rating_filter_config = full_config.get("rating_filter", {})
        new_sleeping_config = rating_filter_config.get("new_sleeping", {})

        # 合并默认配置
        config = self.DEFAULT_CONFIG.copy()
        if new_sleeping_config:
            config.update(new_sleeping_config)
            # 特殊处理嵌套配置
            if "category_min_scores" in new_sleeping_config:
                config["category_min_scores"] = {
                    **self.DEFAULT_CONFIG["category_min_scores"],
                    **new_sleeping_config["category_min_scores"],
                }

        return config

    def apply_filter(
        self,
        df: pd.DataFrame,
        rating_column: str = "豆瓣评分",
        call_number_column: str = "索书号",
        candidate_column: str = "候选状态",
        title_column: str = "书名",
        pub_year_column: str = "豆瓣出版年",
    ) -> NewSleepingFilterResult:
        """
        应用新书评分过滤规则

        Args:
            df: 待过滤的 DataFrame
            rating_column: 评分列名
            call_number_column: 索书号列名
            candidate_column: 候选状态列名（过滤结果写入此列）
            title_column: 书名列名
            pub_year_column: 出版年列名

        Returns:
            过滤结果统计
        """
        if not self.config.get("enabled", True):
            logger.info("新书评分过滤已禁用")
            return NewSleepingFilterResult(
                total_count=len(df),
                candidate_count=0,
                excluded_count=0,
                excluded_by_rating=0,
                excluded_by_required_fields=0,
                excluded_by_pub_year=0,
                excluded_by_title_keywords=0,
                excluded_by_call_number=0,
                category_stats={},
            )

        total_count = len(df)
        logger.info(f"开始新书评分过滤，总记录数: {total_count}")

        # 初始化候选状态列
        if candidate_column not in df.columns:
            df[candidate_column] = ""

        # 初始化统计
        excluded_by_rating = 0
        excluded_by_required_fields = 0
        excluded_by_pub_year = 0
        excluded_by_title_keywords = 0
        excluded_by_call_number = 0
        category_stats = {}

        # 构建候选掩码（初始全部为候选）
        candidate_mask = pd.Series(True, index=df.index)

        # 规则1: 必填字段验证
        required_fields = self.config.get("required_fields", [])
        for field_config in required_fields:
            column = field_config.get("column")
            if column and column in df.columns:
                empty_mask = df[column].isna() | (df[column].astype(str).str.strip() == "")
                excluded_count = (candidate_mask & empty_mask).sum()
                candidate_mask &= ~empty_mask
                excluded_by_required_fields += excluded_count
                logger.info(f"必填字段验证 [{column}]: 排除 {excluded_count} 条")

        # 规则2: 出版年过滤
        pub_year_config = self.config.get("pub_year_filter", {})
        if pub_year_config.get("enabled", False) and pub_year_column in df.columns:
            current_year = datetime.now().year
            mode = pub_year_config.get("mode", "current_year")

            if mode == "current_year":
                # 解析出版年（支持多种格式：2025, 2025-5-1, 2025-5 等）
                pub_year_mask = self._check_pub_year(df[pub_year_column], current_year)
                excluded_count = (candidate_mask & ~pub_year_mask).sum()
                candidate_mask &= pub_year_mask
                excluded_by_pub_year = excluded_count
                logger.info(f"出版年过滤 [当年={current_year}]: 排除 {excluded_count} 条")

        # 规则3: 题名关键词过滤
        reuse_filters = self.config.get("reuse_filters", {})
        if reuse_filters.get("title_keywords", False):
            title_col = self._find_column(df, [title_column, "题名", "书名"])
            if title_col:
                title_matcher = TitleKeywordsMatcher()
                if title_matcher.has_keywords:
                    keyword_mask = title_matcher.apply(df[title_col])
                    excluded_count = (candidate_mask & keyword_mask).sum()
                    candidate_mask &= ~keyword_mask
                    excluded_by_title_keywords = excluded_count
                    logger.info(
                        f"题名关键词过滤: 排除 {excluded_count} 条 "
                        f"(关键词数: {title_matcher.get_keywords_count()})"
                    )

        # 规则4: 索书号规则过滤
        if reuse_filters.get("call_number_clc", False):
            call_no_col = self._find_column(df, [call_number_column, "索书号"])
            if call_no_col:
                call_number_matcher = CallNumberMatcher()
                if call_number_matcher.has_rules:
                    call_no_mask = call_number_matcher.apply(df[call_no_col])
                    excluded_count = (candidate_mask & call_no_mask).sum()
                    candidate_mask &= ~call_no_mask
                    excluded_by_call_number = excluded_count
                    logger.info(
                        f"索书号规则过滤: 排除 {excluded_count} 条 "
                        f"({call_number_matcher.get_rules_summary()})"
                    )

        # 规则5: 学科最低评分过滤
        rating_col = self._find_column(df, [rating_column, "豆瓣评分"])
        call_no_col = self._find_column(df, [call_number_column, "索书号"])

        if rating_col and call_no_col:
            category_min_scores = self.config.get("category_min_scores", {})
            default_score = category_min_scores.get("default", 7.2)
            # 是否允许无评分书籍成为候选（默认True，保持向后兼容）
            allow_no_rating = self.config.get("allow_no_rating", True)

            # 提取索书号首字母
            call_letters = df[call_no_col].apply(self._extract_call_letter)

            # 逐行判断评分
            ratings = pd.to_numeric(df[rating_col], errors="coerce").fillna(0)

            for idx in df.index:
                if not candidate_mask[idx]:
                    continue

                letter = call_letters[idx]
                rating = ratings[idx]
                min_score = category_min_scores.get(letter, default_score)

                # 记录学科统计
                if letter not in category_stats:
                    category_stats[letter] = {
                        "total": 0,
                        "passed": 0,
                        "min_score": min_score,
                    }
                category_stats[letter]["total"] += 1

                # 评分判断逻辑
                if rating == 0:
                    # 无评分书籍：根据配置决定是否保留
                    if allow_no_rating:
                        category_stats[letter]["passed"] += 1
                    else:
                        candidate_mask[idx] = False
                        excluded_by_rating += 1
                elif rating < min_score:
                    # 有评分但不达标：排除
                    candidate_mask[idx] = False
                    excluded_by_rating += 1
                else:
                    # 有评分且达标：保留
                    category_stats[letter]["passed"] += 1

            logger.info(f"学科最低评分过滤: 排除 {excluded_by_rating} 条 (allow_no_rating={allow_no_rating})")

        # 写入候选状态
        df.loc[candidate_mask, candidate_column] = "候选"
        df.loc[~candidate_mask, candidate_column] = ""

        candidate_count = candidate_mask.sum()
        excluded_count = total_count - candidate_count

        # 输出统计
        logger.info("=" * 50)
        logger.info("【新书评分过滤统计】")
        logger.info(f"  总记录数: {total_count}")
        logger.info(f"  候选数量: {candidate_count}")
        logger.info(f"  排除数量: {excluded_count}")
        logger.info(f"    - 必填字段缺失: {excluded_by_required_fields}")
        logger.info(f"    - 出版年不符合: {excluded_by_pub_year}")
        logger.info(f"    - 题名关键词: {excluded_by_title_keywords}")
        logger.info(f"    - 索书号规则: {excluded_by_call_number}")
        logger.info(f"    - 评分不达标: {excluded_by_rating}")

        if category_stats:
            logger.info("  各学科统计:")
            for letter, stats in sorted(category_stats.items()):
                logger.info(
                    f"    {letter}: 总数 {stats['total']}, 通过 {stats['passed']}, "
                    f"最低分 {stats['min_score']}"
                )
        logger.info("=" * 50)

        return NewSleepingFilterResult(
            total_count=total_count,
            candidate_count=candidate_count,
            excluded_count=excluded_count,
            excluded_by_rating=excluded_by_rating,
            excluded_by_required_fields=excluded_by_required_fields,
            excluded_by_pub_year=excluded_by_pub_year,
            excluded_by_title_keywords=excluded_by_title_keywords,
            excluded_by_call_number=excluded_by_call_number,
            category_stats=category_stats,
        )

    def _extract_call_letter(self, call_no: Optional[str]) -> str:
        """提取索书号首字母"""
        if call_no is None or pd.isna(call_no):
            return "未知"
        normalized = str(call_no).strip().upper()
        if not normalized:
            return "未知"
        match = self._call_letter_pattern.search(normalized)
        return match.group(0) if match else "未知"

    def _check_pub_year(self, pub_year_series: pd.Series, target_year: int) -> pd.Series:
        """
        检查出版年是否为目标年份

        支持格式：
        - 纯文本：2025, 2025-5-1, 2025-5, 2025/5/1, 2025年5月
        - datetime 对象
        - Excel 日期序列号（如 45678）
        """
        def extract_year(value) -> Optional[int]:
            if pd.isna(value):
                return None

            # 处理 datetime 对象
            if isinstance(value, (pd.Timestamp, datetime)):
                return value.year

            # 处理数值类型（可能是 Excel 日期序列号）
            if isinstance(value, (int, float)):
                # Excel 日期序列号通常 > 40000（约 2009 年后）
                if value > 40000:
                    try:
                        # Excel 日期序列号转换
                        dt = pd.to_datetime(value, unit='D', origin='1899-12-30')
                        return dt.year
                    except Exception:
                        pass
                # 如果是 4 位数，可能直接就是年份
                if 1900 <= value <= 2100:
                    return int(value)

            # 转为文本处理
            text = str(value).strip()
            if not text:
                return None

            # 尝试提取年份（4位数字）
            match = re.search(r"(\d{4})", text)
            if match:
                return int(match.group(1))

            return None

        years = pub_year_series.apply(extract_year)
        return years == target_year

    def _find_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """查找存在的列名"""
        for col in candidates:
            if col in df.columns:
                return col
        return None

def run_new_sleeping_rating_filter(excel_file: str) -> Tuple[str, NewSleepingFilterResult]:
    """
    运行新书评分过滤

    Args:
        excel_file: 输入的 Excel 文件路径（应为模块3-B的输出）

    Returns:
        (输出文件路径, 过滤结果)
    """
    from src.utils.time_utils import get_timestamp

    logger.info("=" * 60)
    logger.info("新书评分过滤")
    logger.info("=" * 60)
    logger.info(f"输入文件: {excel_file}")

    # 读取 Excel
    df = pd.read_excel(excel_file)
    logger.info(f"加载数据完成，共 {len(df)} 条记录")

    # 应用过滤
    rating_filter = NewSleepingRatingFilter()
    result = rating_filter.apply_filter(df)

    # 保存结果（直接写回原文件）
    input_path = Path(excel_file)
    df.to_excel(excel_file, index=False)
    logger.info(f"结果已保存到: {excel_file}")

    # 保存统计结果到 txt 文件
    timestamp = get_timestamp()
    stats_file = input_path.parent / f"{input_path.stem}_评分过滤报告_{timestamp}.txt"
    with open(stats_file, "w", encoding="utf-8") as f:
        f.write("【新书评分过滤统计】\n")
        f.write(f"总记录数: {result.total_count}\n")
        f.write(f"候选数量: {result.candidate_count}\n")
        f.write(f"排除数量: {result.excluded_count}\n")
        f.write(f"  - 必填字段缺失: {result.excluded_by_required_fields}\n")
        f.write(f"  - 出版年不符合: {result.excluded_by_pub_year}\n")
        f.write(f"  - 题名关键词: {result.excluded_by_title_keywords}\n")
        f.write(f"  - 索书号规则: {result.excluded_by_call_number}\n")
        f.write(f"  - 评分不达标: {result.excluded_by_rating}\n")
        if result.category_stats:
            f.write("各学科统计:\n")
            for letter, stats in sorted(result.category_stats.items()):
                f.write(
                    f"  {letter}: 总数 {stats['total']}, 通过 {stats['passed']}, "
                    f"最低分 {stats['min_score']}\n"
                )
    logger.info(f"统计结果已保存到: {stats_file}")

    return str(excel_file), result
