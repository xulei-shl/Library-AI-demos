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
import json
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
    llm_filtered_count: int = 0         # LLM筛选排除数
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
                llm_filtered_count=0,
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

        # 规则6: 无评分书籍LLM智能筛选
        llm_filtered_count = 0
        if rating_col and allow_no_rating:
            candidate_mask, llm_filtered_count = self._apply_no_rating_llm_filter(
                df, candidate_mask, rating_col
            )

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
        if llm_filtered_count > 0:
            logger.info(f"    - LLM智能筛选: {llm_filtered_count}")

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
            llm_filtered_count=llm_filtered_count,
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

    def _apply_no_rating_llm_filter(
        self,
        df: pd.DataFrame,
        candidate_mask: pd.Series,
        rating_column: str,
    ) -> tuple[pd.Series, int]:
        """
        对无评分候选书籍进行LLM智能筛选
        
        三层判断逻辑:
        1. 无评分候选数 > pre_filter.trigger_threshold → 触发预筛选
        2. 预筛选后数量 > llm_trigger_threshold → 触发LLM筛选
        
        Args:
            df: 数据框
            candidate_mask: 当前候选掩码
            rating_column: 评分列名
            
        Returns:
            (更新后的候选掩码, LLM筛选排除数量)
        """
        llm_config = self.config.get("no_rating_llm_filter", {})
        if not llm_config.get("enabled", False):
            return candidate_mask, 0
        
        # 1. 识别无评分的候选书籍
        ratings = pd.to_numeric(df[rating_column], errors="coerce").fillna(0)
        no_rating_candidates = candidate_mask & (ratings == 0)
        no_rating_count = no_rating_candidates.sum()
        
        logger.info(f"检测到无评分候选书籍: {no_rating_count} 条")
        
        # 2. 准备LLM筛选数据
        no_rating_df = df[no_rating_candidates].copy()
        
        # 3. 判断是否需要应用预筛选
        pre_filter_config = llm_config.get("pre_filter", {})
        pre_filter_enabled = pre_filter_config.get("enabled", False)
        pre_filter_threshold = pre_filter_config.get("trigger_threshold", 0)
        
        if pre_filter_enabled and no_rating_count > pre_filter_threshold:
            # 无评分候选数超过预筛选阈值,启动预筛选
            logger.info(
                f"无评分候选数({no_rating_count}) > 预筛选阈值({pre_filter_threshold}),启动预筛选"
            )
            no_rating_df = self._apply_pre_filter(no_rating_df, pre_filter_config)
            logger.info(f"预筛选后剩余: {len(no_rating_df)} 条")
        elif pre_filter_enabled:
            # 预筛选已启用,但无评分候选数未达到阈值
            logger.info(
                f"无评分候选数({no_rating_count}) ≤ 预筛选阈值({pre_filter_threshold}),跳过预筛选"
            )
        
        # 4. 判断预筛选后的数量是否触发LLM筛选
        # 兼容旧配置: 优先使用 llm_trigger_threshold, 其次使用 trigger_threshold
        llm_threshold = llm_config.get("llm_trigger_threshold") or llm_config.get("trigger_threshold", 100)
        final_count = len(no_rating_df)
        
        if final_count <= llm_threshold:
            logger.info(
                f"{'预筛选后' if pre_filter_enabled and no_rating_count > pre_filter_threshold else ''}"
                f"无评分候选数({final_count}) ≤ LLM阈值({llm_threshold}),跳过LLM筛选"
            )
            return candidate_mask, 0
        
        logger.info(f"无评分候选数({final_count}) > LLM阈值({llm_threshold}),启动LLM智能筛选")
        
        # 5. 分批调用LLM
        batch_config = llm_config.get("batch_processing", {})
        batch_size = batch_config.get("batch_size", 20)
        pass_quota = batch_config.get("pass_quota_per_batch", 10)
        task_name = llm_config.get("llm_task_name", "no_rating_book_filter")
        
        # 延迟导入LLM客户端
        try:
            from src.utils.llm.client import UnifiedLLMClient
        except ImportError as e:
            logger.error(f"无法导入LLM客户端: {e}")
            return candidate_mask, 0
        
        llm_client = UnifiedLLMClient()
        passed_barcodes = set()
        total_batches = (len(no_rating_df) + batch_size - 1) // batch_size
        
        logger.info(f"开始分批LLM筛选: 共{total_batches}批,每批{batch_size}本,每批最多通过{pass_quota}本")
        
        for i in range(0, len(no_rating_df), batch_size):
            batch_num = i // batch_size + 1
            batch_df = no_rating_df.iloc[i:i+batch_size]
            
            # 构建提示词
            books_info = self._format_books_for_llm(batch_df)
            prompt = f"请从以下{len(batch_df)}本书中筛选出最多{pass_quota}本推荐:\n\n{books_info}"
            
            # 调用LLM
            try:
                logger.info(f"处理第{batch_num}/{total_batches}批...")
                response = llm_client.call(task_name, prompt)
                
                # 解析响应
                results = json.loads(response)
                
                # 提取通过的书目条码
                batch_passed = 0
                for item in results:
                    if item.get("decision") == "通过":
                        barcode = item.get("barcode")
                        if barcode:
                            passed_barcodes.add(barcode)
                            batch_passed += 1
                            logger.debug(
                                f"  通过: {barcode} | 分数: {item.get('score', 'N/A')} | "
                                f"理由: {item.get('reason', 'N/A')}"
                            )
                
                logger.info(f"第{batch_num}批完成: {batch_passed}/{len(batch_df)} 通过")
                
            except json.JSONDecodeError as e:
                logger.error(f"LLM响应JSON解析失败(批次{batch_num}): {e}")
                logger.debug(f"原始响应: {response[:200]}...")
                continue
            except Exception as e:
                logger.error(f"LLM筛选批次{batch_num}失败: {e}")
                continue
        
        # 6. 更新候选状态
        # 将未通过LLM筛选的无评分书籍从候选中移除
        llm_filtered_count = 0
        for idx in no_rating_df.index:
            barcode = df.loc[idx, "书目条码"]
            if barcode not in passed_barcodes:
                candidate_mask[idx] = False
                llm_filtered_count += 1
        
        logger.info(
            f"LLM筛选完成: {len(passed_barcodes)}/{final_count} 通过, "
            f"{llm_filtered_count} 被排除"
        )
        
        return candidate_mask, llm_filtered_count

    def _format_books_for_llm(self, df: pd.DataFrame) -> str:
        """
        格式化书籍信息供LLM评估
        
        Args:
            df: 包含书籍信息的数据框
            
        Returns:
            格式化后的书籍信息字符串
        """
        books = []
        for idx, row in df.iterrows():
            # 提取关键信息
            book_info = {
                "barcode": str(row.get("书目条码", "")),
                "title": str(row.get("豆瓣书名", row.get("书名", ""))),
                "author": str(row.get("豆瓣作者", "")),
                "publisher": str(row.get("豆瓣出版社", "")),
                "pub_year": str(row.get("豆瓣出版年", "")),
                "summary": str(row.get("豆瓣内容简介", ""))[:150],  # 截取前150字
                "call_number": str(row.get("索书号", "")),
            }
            
            # 清理空值
            book_info = {k: v for k, v in book_info.items() if v and v != "nan"}
            
            books.append(json.dumps(book_info, ensure_ascii=False))
        
        return "\n".join(books)

    def _apply_pre_filter(
        self,
        df: pd.DataFrame,
        pre_filter_config: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        应用预筛选策略,在LLM前进一步缩小范围
        
        Args:
            df: 待筛选的数据框
            pre_filter_config: 预筛选配置
            
        Returns:
            筛选后的数据框
        """
        result_df = df.copy()
        filter_mask = pd.Series(False, index=result_df.index)
        has_any_condition = False  # 标记是否配置了任何有效条件
        
        # 条件1: 优先保留有指定字段值的书籍(AND逻辑:所有字段都有值才保留)
        prefer_fields = pre_filter_config.get("prefer_with_fields", [])
        if prefer_fields:  # 非空列表才执行
            has_any_condition = True
            field_mask = pd.Series(True, index=result_df.index)  # 初始为True,使用AND逻辑
            
            for field in prefer_fields:
                if field in result_df.columns:
                    has_value = result_df[field].notna() & (
                        result_df[field].astype(str).str.strip() != ""
                    )
                    field_mask &= has_value  # AND逻辑:所有字段都必须有值
                    logger.info(f"预筛选: 字段 [{field}] 有值的书籍 ({has_value.sum()} 条)")
                else:
                    # 如果配置的字段不存在,则全部过滤
                    logger.warning(f"预筛选: 字段 [{field}] 不存在于数据中,将过滤所有书籍")
                    field_mask = pd.Series(False, index=result_df.index)
                    break
            
            filter_mask |= field_mask
            logger.info(f"预筛选: 满足所有字段条件的书籍总计 ({field_mask.sum()} 条)")
        
        # 条件2: 优先保留特定学科
        priority_categories = pre_filter_config.get("priority_categories", [])
        if priority_categories:  # 非空列表才执行
            has_any_condition = True
            call_letters = result_df["索书号"].apply(self._extract_call_letter)
            is_priority = call_letters.isin(priority_categories)
            filter_mask |= is_priority
            logger.info(
                f"预筛选: 优先学科 {priority_categories} "
                f"({is_priority.sum()} 条)"
            )
        
        # 如果没有配置任何有效条件,返回原数据
        if not has_any_condition:
            logger.warning("预筛选: 未配置任何有效的筛选条件,保留所有书籍")
            return result_df
        
        # 如果配置了条件但没有书籍满足,返回空数据框
        if not filter_mask.any():
            logger.warning("预筛选: 配置了筛选条件,但没有书籍满足,返回空结果")
            return result_df[filter_mask]  # 返回空DataFrame
        
        # 应用过滤
        result_df = result_df[filter_mask]
        logger.info(f"预筛选: 最终保留 {len(result_df)} 条")
        
        return result_df

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
        if result.llm_filtered_count > 0:
            f.write(f"  - LLM智能筛选: {result.llm_filtered_count}\n")
        if result.category_stats:
            f.write("各学科统计:\n")
            for letter, stats in sorted(result.category_stats.items()):
                f.write(
                    f"  {letter}: 总数 {stats['total']}, 通过 {stats['passed']}, "
                    f"最低分 {stats['min_score']}\n"
                )
    logger.info(f"统计结果已保存到: {stats_file}")

    return str(excel_file), result
