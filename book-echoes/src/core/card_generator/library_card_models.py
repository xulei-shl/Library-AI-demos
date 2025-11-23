"""
图书馆借书卡数据模型
用于生成复古风格的借书卡片
"""

from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class BorrowerRecord:
    """借阅者记录"""
    date: str  # YYYY-MM-DD格式
    name: str  # 借阅者姓名
    
    def format_date_for_display(self) -> str:
        """
        将YYYY-MM-DD格式转换为显示格式 "MMM DD 'YY"
        例如: "2023-05-15" -> "MAY 15 '23"
        """
        from datetime import datetime
        try:
            dt = datetime.strptime(self.date, "%Y-%m-%d")
            month = dt.strftime("%b").upper()
            day = dt.strftime("%d")
            year = dt.strftime("%y")
            return f"{month} {day} '{year}"
        except Exception:
            return self.date


@dataclass
class LibraryCardData:
    """图书馆借书卡数据"""
    barcode: str  # 书目条码
    author: str  # 作者
    title: str  # 书名（豆瓣书名）
    call_no: str  # 索书号
    year: str  # 出版年份
    borrower_records: List[BorrowerRecord]  # 借阅记录列表
    subtitle: Optional[str] = None  # 豆瓣副标题
    
    @property
    def full_title(self) -> str:
        """
        获取完整书名（书名 + 副标题）
        如果副标题存在，用 " : " 拼接
        """
        if self.subtitle and self.subtitle.strip():
            return f"{self.title} : {self.subtitle}"
        return self.title
    
    @property
    def card_number(self) -> str:
        """
        从索书号中提取卡片编号
        提取规则: 从'/'后面到其他符号之前的数字
        例如: "B512.59/5024-3" -> "5024"
        """
        match = re.search(r'/(\d+)', self.call_no)
        if match:
            return match.group(1)
        return "0000"
    
    @property
    def barcode_with_suffix(self) -> str:
        """
        返回带-S后缀的条码，用于文件命名
        例如: "123456" -> "123456-S"
        """
        return f"{self.barcode}-S"
    
    def validate(self) -> bool:
        """
        验证数据完整性
        
        Returns:
            bool: 数据有效返回True，否则返回False
        """
        if not self.barcode or not self.barcode.strip():
            return False
        
        if not self.call_no or not self.call_no.strip():
            return False
        
        if not self.title or not self.title.strip():
            return False
        
        if not self.borrower_records:
            return False
        
        return True
