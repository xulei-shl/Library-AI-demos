#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则文件解析器 - 统一解析 config/filters 下的规则文件

职责：
- 解析 call_number_clc.txt（索书号规则）
- 解析 title_keywords.txt（题名关键词）
- 提供统一的规则数据结构

支持的指令（索书号规则）：
- DROP! / EXCLUDE! - 高优先级排除（不受 KEEP 保护）
- KEEP / INCLUDE / ALLOW - 保留规则
- DROP / EXCLUDE / DENY - 普通排除（受 KEEP 保护）
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 默认配置文件路径
DEFAULT_CALL_NUMBER_RULES_FILE = Path("config/filters/call_number_clc.txt")
DEFAULT_TITLE_KEYWORDS_FILE = Path("config/filters/title_keywords.txt")


@dataclass
class CallNumberRules:
    """索书号规则集合"""
    high_priority_exclude: List[str] = field(default_factory=list)  # DROP! 高优先级排除
    include: List[str] = field(default_factory=list)                 # KEEP 保留
    exclude: List[str] = field(default_factory=list)                 # DROP 普通排除

    @property
    def has_rules(self) -> bool:
        """是否有任何规则"""
        return bool(self.high_priority_exclude or self.include or self.exclude)

    def get_summary(self) -> str:
        """获取规则摘要"""
        return (
            f"高优先级排除: {len(self.high_priority_exclude)} 条, "
            f"保留: {len(self.include)} 条, "
            f"普通排除: {len(self.exclude)} 条"
        )


class RuleFileParser:
    """规则文件解析器"""

    # 高优先级排除指令
    HIGH_PRIORITY_DROP_DIRECTIVES = ("drop!", "exclude!")
    # 保留指令
    KEEP_DIRECTIVES = ("keep", "include", "allow")
    # 普通排除指令
    DROP_DIRECTIVES = ("drop", "exclude", "deny")

    @classmethod
    def load_call_number_rules(
        cls, file_path: Optional[Path] = None
    ) -> CallNumberRules:
        """
        加载索书号规则

        Args:
            file_path: 规则文件路径，默认为 config/filters/call_number_clc.txt

        Returns:
            CallNumberRules 规则集合
        """
        file_path = file_path or DEFAULT_CALL_NUMBER_RULES_FILE
        rules = CallNumberRules()

        if not file_path.exists():
            logger.warning(f"索书号规则文件不存在: {file_path}")
            return rules

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parsed = cls._parse_call_number_line(line)
                    if parsed:
                        group, pattern = parsed
                        if group == "high_priority_exclude":
                            rules.high_priority_exclude.append(pattern)
                        elif group == "include":
                            rules.include.append(pattern)
                        else:
                            rules.exclude.append(pattern)

            logger.info(f"加载索书号规则: {rules.get_summary()}")
        except Exception as e:
            logger.error(f"加载索书号规则文件失败: {e}")

        return rules

    @classmethod
    def _parse_call_number_line(cls, line: str) -> Optional[tuple]:
        """
        解析索书号规则行

        Returns:
            (group, pattern) 或 None
        """
        tokens = line.split(maxsplit=1)
        if len(tokens) == 1:
            # 无指令前缀，视为普通排除规则
            return ("exclude", tokens[0])

        directive, pattern = tokens[0].lower(), tokens[1]
        if directive in cls.HIGH_PRIORITY_DROP_DIRECTIVES:
            return ("high_priority_exclude", pattern)
        elif directive in cls.KEEP_DIRECTIVES:
            return ("include", pattern)
        elif directive in cls.DROP_DIRECTIVES:
            return ("exclude", pattern)
        else:
            # 无法识别的指令，将整行视为普通排除规则
            return ("exclude", line)

    @classmethod
    def load_title_keywords(cls, file_path: Optional[Path] = None) -> List[str]:
        """
        加载题名关键词

        Args:
            file_path: 关键词文件路径，默认为 config/filters/title_keywords.txt

        Returns:
            关键词列表
        """
        file_path = file_path or DEFAULT_TITLE_KEYWORDS_FILE
        keywords = []

        if not file_path.exists():
            logger.warning(f"题名关键词文件不存在: {file_path}")
            return keywords

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        keywords.append(line)

            logger.info(f"加载题名关键词: {len(keywords)} 条")
        except Exception as e:
            logger.error(f"加载题名关键词文件失败: {e}")

        return keywords


class CallNumberMatcher:
    """索书号匹配器 - 应用规则到 DataFrame"""

    def __init__(self, rules: Optional[CallNumberRules] = None):
        """
        初始化匹配器

        Args:
            rules: 规则集合，如果不传则自动加载默认文件
        """
        self.rules = rules or RuleFileParser.load_call_number_rules()

    def apply(self, call_no_series: pd.Series) -> pd.Series:
        """
        应用索书号规则过滤，返回需要排除的掩码

        过滤逻辑（按优先级）：
        1. 高优先级排除（DROP!）：无条件排除，不受 KEEP 保护
        2. 保留规则（KEEP）：匹配则保留
        3. 普通排除（DROP）：仅当未命中 KEEP 时才排除

        Args:
            call_no_series: 索书号列

        Returns:
            需要排除的布尔掩码（True 表示需要排除）
        """
        call_nos = call_no_series.fillna("").astype(str)

        # 1. 高优先级排除（无条件排除）
        high_priority_mask = self._build_mask(
            call_nos, self.rules.high_priority_exclude, "高优先级排除"
        )

        # 2. 构建保留掩码
        include_mask = self._build_mask(call_nos, self.rules.include, "保留")

        # 3. 构建普通排除掩码
        normal_exclude_mask = self._build_mask(call_nos, self.rules.exclude, "排除")

        # 组合逻辑：
        # - 高优先级排除：直接排除
        # - 普通排除：仅当未命中保留规则时才排除
        return high_priority_mask | ((~include_mask) & normal_exclude_mask)

    def _build_mask(
        self, series: pd.Series, patterns: List[str], rule_type: str
    ) -> pd.Series:
        """构建匹配掩码"""
        mask = pd.Series(False, index=series.index)
        for pattern in patterns:
            try:
                mask |= series.str.match(pattern, na=False)
            except re.error:
                logger.warning(f"无效的{rule_type}正则: {pattern}")
        return mask

    @property
    def has_rules(self) -> bool:
        """是否有任何规则"""
        return self.rules.has_rules

    def get_rules_summary(self) -> str:
        """获取规则摘要"""
        return self.rules.get_summary()


class TitleKeywordsMatcher:
    """题名关键词匹配器"""

    def __init__(self, keywords: Optional[List[str]] = None):
        """
        初始化匹配器

        Args:
            keywords: 关键词列表，如果不传则自动加载默认文件
        """
        self.keywords = keywords or RuleFileParser.load_title_keywords()

    def apply(self, title_series: pd.Series, case_sensitive: bool = False) -> pd.Series:
        """
        应用题名关键词过滤，返回需要排除的掩码

        Args:
            title_series: 题名列
            case_sensitive: 是否大小写敏感

        Returns:
            需要排除的布尔掩码（True 表示需要排除）
        """
        mask = pd.Series(False, index=title_series.index)
        titles = title_series.fillna("").astype(str)

        for keyword in self.keywords:
            mask |= titles.str.contains(keyword, case=case_sensitive, na=False)

        return mask

    @property
    def has_keywords(self) -> bool:
        """是否有任何关键词"""
        return bool(self.keywords)

    def get_keywords_count(self) -> int:
        """获取关键词数量"""
        return len(self.keywords)
