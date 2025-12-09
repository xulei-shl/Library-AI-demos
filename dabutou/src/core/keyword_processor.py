"""
关键词处理器
负责处理Excel中的ISBN和题名信息
"""
import re
from typing import Tuple
import logging


class KeywordProcessor:
    """关键词处理器"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # ISBN正则表达式
        self.isbn_pattern = re.compile(r'^[0-9Xx]+$')

    def clean_isbn(self, isbn_str: str) -> list[str]:
        """
        清理ISBN字符串，支持单个或分号隔开的多个ISBN
        Args:
            isbn_str: 原始ISBN字符串
        Returns:
            清理后的ISBN列表，如果不是合法ISBN返回空列表
        """
        if not isbn_str:
            return []

        isbns = []
        # 首先按多种分隔符分割
        isbn_str = str(isbn_str)
        # 按分号、中文顿号、中文逗号分割
        separators = [';', '、', '，']
        isbn_parts = [isbn_str]
        
        for sep in separators:
            new_parts = []
            for part in isbn_parts:
                new_parts.extend(part.split(sep))
            isbn_parts = new_parts

        for part in isbn_parts:
            # 移除空格、连字符等
            cleaned = re.sub(r'[-\s]', '', part.strip())

            # 移除中文标点符号和常见中文字符
            cleaned = re.sub(r'[，。、；：？！""''（）【】《》〈〉「」『』［］｛｝〔〕·～…—－＝＋×÷＜＞｜＼／＆％＄＃＠！＾＊（）＝［］｛｝：；＂＇＜＞？／～｀！＠＃＄％＾＆＊（）＿＋－＝｛｝［］｜＼：；＂＇＜＞？／～｀]', '', cleaned)

            # 移除常见的中文字符（特别是在ISBN中出现的）
            cleaned = re.sub(r'[等含及与和其他等亦或又另有包括含]', '', cleaned)

            # 移除括号内容（如(1)、(第1册)等）
            cleaned = re.sub(r'\([^)]*\)', '', cleaned)

            # 移除常见的前缀（如ISBN:等）
            cleaned = re.sub(r'^(ISBN|isbn)[：:\s]*', '', cleaned)

            # 检查是否为纯数字或包含X的合法ISBN
            if self.isbn_pattern.fullmatch(cleaned):
                isbns.append(cleaned)
            else:
                # Debug: 记录为什么ISBN没有通过正则匹配
                self.logger.debug(f"ISBN '{cleaned}' (原始: '{part.strip()}') 未通过正则匹配")

        # Debug: 记录最终的ISBN列表
        self.logger.debug(f"原始ISBN: '{isbn_str}', 清理后: {isbns}")

        return isbns

    def _clean_title(self, title: str) -> str:
        """
        清理题名，提取适合检索的关键词
        规则：不论是逗号还是句号，只要有多个符号（2个或以上），就截取第二个符号前的文本
        Args:
            title: 原始题名
        Returns:
            清理后的题名
        """
        if not title:
            return ""
            
        title_cleaned = str(title).strip()
        self.logger.debug(f"原始题名: '{title_cleaned}'")
        
        # 统计逗号和句号的数量
        comma_count = title_cleaned.count(',')
        period_count = title_cleaned.count('.')
        total_symbols = comma_count + period_count
        
        self.logger.debug(f"题名包含逗号数量: {comma_count}, 句号数量: {period_count}, 总计: {total_symbols}")
        
        # 如果总共有2个或以上的符号，截取第二个符号前的文本
        if total_symbols >= 2:
            # 找到第二个符号的位置
            symbol_positions = []
            for i, char in enumerate(title_cleaned):
                if char in [',', '.']:
                    symbol_positions.append(i)
                    if len(symbol_positions) == 2:
                        break
            
            if len(symbol_positions) == 2:
                title_cleaned = title_cleaned[:symbol_positions[1]].strip()
                self.logger.debug(f"截取第二个符号前的文本: '{title_cleaned}'")
        # 如果只有1个符号，截取第一个符号前的文本（保持原有逻辑）
        elif total_symbols == 1:
            if ',' in title_cleaned:
                title_cleaned = title_cleaned.split(',')[0].strip()
            elif '.' in title_cleaned:
                title_cleaned = title_cleaned.split('.')[0].strip()
            self.logger.debug(f"截取第一个符号前的文本: '{title_cleaned}'")
        
        self.logger.debug(f"最终清理后的题名: '{title_cleaned}'")
        return title_cleaned

    def extract_keyword(self, isbn: str, title: str) -> Tuple[str, str]:
        """
        提取搜索关键词
        Args:
            isbn: ISBN列的值
            title: 题名列的值
        Returns:
            (keyword_type, keyword_value)
            keyword_type: 'isbn' 或 'title'
            keyword_value: 关键词值（ISBN列表或题名）
        """
        # 尝试清理ISBN（现在返回列表）
        cleaned_isbns = self.clean_isbn(isbn)
        if cleaned_isbns:
            self.logger.debug(f"使用ISBN作为关键词: {cleaned_isbns}")
            return 'isbn', ';'.join(cleaned_isbns)  # 用分号连接多个ISBN

        # 如果ISBN无效，使用题名
        if title and str(title).strip():
            title_cleaned = self._clean_title(title)
            self.logger.debug(f"使用题名作为关键词: '{title_cleaned}'")
            return 'title', title_cleaned

        # 如果都无效，返回空字符串
        self.logger.warning(f"无效的ISBN和题名: ISBN='{isbn}', Title='{title}'")
        return 'none', ''

    def extract_keywords_list(self, isbn: str, title: str) -> list[Tuple[str, str]]:
        """
        提取搜索关键词列表（每个ISBN作为一个关键词）
        Args:
            isbn: ISBN列的值
            title: 题名列的值
        Returns:
            关键词列表，每个元素为(keyword_type, keyword_value)
        """
        # 尝试清理ISBN（现在返回列表）
        cleaned_isbns = self.clean_isbn(isbn)
        if cleaned_isbns:
            self.logger.debug(f"使用多个ISBN作为关键词: {cleaned_isbns}")
            return [('isbn', isbn) for isbn in cleaned_isbns]

        # 如果ISBN无效，使用题名
        if title and str(title).strip():
            title_cleaned = self._clean_title(title)
            self.logger.debug(f"使用题名作为关键词: '{title_cleaned}'")
            return [('title', title_cleaned)]

        # 如果都无效，返回空列表
        self.logger.warning(f"无效的ISBN和题名: ISBN='{isbn}', Title='{title}'")
        return []

    def is_valid_isbn(self, isbn: str) -> bool:
        """
        检查ISBN是否有效（支持单个ISBN或包含分号隔开多个ISBN的字符串）
        Args:
            isbn: ISBN字符串
        Returns:
            是否为有效ISBN（至少有一个有效ISBN）
        """
        cleaned_isbns = self.clean_isbn(isbn)
        if not cleaned_isbns:
            return False

        # 只要有一个有效的ISBN就返回True
        return any(self._is_single_isbn_valid(cleaned_isbn) for cleaned_isbn in cleaned_isbns)

    def _is_single_isbn_valid(self, isbn: str) -> bool:
        """
        检查单个ISBN是否有效
        Args:
            isbn: 清理后的ISBN字符串
        Returns:
            是否为有效ISBN
        """
        # ISBN-10 或 ISBN-13
        if len(isbn) == 10:
            return self._is_valid_isbn10(isbn)
        elif len(isbn) == 13:
            return self._is_valid_isbn13(isbn)

        return False

    def _is_valid_isbn10(self, isbn: str) -> bool:
        """验证ISBN-10"""
        try:
            total = 0
            for i, char in enumerate(isbn[:-1]):
                total += (i + 1) * int(char)

            check_digit = isbn[-1].upper()
            if check_digit == 'X':
                expected = total % 11
                return expected == 10
            else:
                expected = total % 11
                return expected == int(check_digit)
        except (ValueError, IndexError):
            return False

    def _is_valid_isbn13(self, isbn: str) -> bool:
        """验证ISBN-13"""
        try:
            total = 0
            for i, char in enumerate(isbn[:-1]):
                digit = int(char)
                total += digit if i % 2 == 0 else digit * 3

            check_digit = int(isbn[-1])
            expected = (10 - (total % 10)) % 10
            return check_digit == expected
        except (ValueError, IndexError):
            return False