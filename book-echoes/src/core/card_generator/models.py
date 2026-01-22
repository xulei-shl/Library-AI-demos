"""
数据模型定义模块
定义图书卡片所需的数据结构
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BookCardData:
    """图书卡片数据模型"""

    # 必填字段（无默认值）
    barcode: str                      # 书目条码
    call_number: str                  # 索书号
    douban_rating: float              # 豆瓣评分
    final_review_reason: str          # 初评理由（用于推荐语，智能截取）
    cover_image_url: str              # 豆瓣封面图片链接
    title: str                        # 书名（豆瓣书名或原书名）

    # 可选字段（有默认值）
    subtitle: Optional[str] = None    # 豆瓣副标题
    author: Optional[str] = None      # 豆瓣作者
    publisher: Optional[str] = None   # 豆瓣出版社
    pub_year: Optional[str] = None    # 豆瓣出版年
    douban_url: Optional[str] = None  # 豆瓣图书页面链接（用于提取真实图片URL）

    # 实例变量：截取长度（默认为50）
    max_length: int = 50

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
    def truncated_reason(self) -> str:
        """
        获取截取后的初评理由
        智能在标点符号处截断，避免语句中途截断
        使用实例变量 max_length 作为最大长度
        """
        text = self.final_review_reason
        max_length = self.max_length

        # 如果文本本身不超过最大长度，直接返回
        if len(text) <= max_length:
            return text

        # 定义中英文标点符号
        punctuation = '。！？；,.!?;，、'

        # 在最大长度范围内寻找最后一个标点符号
        search_end = max_length + 10  # 允许稍微超出一点以找到完整句子
        search_text = text[:min(search_end, len(text))]

        # 从后向前查找标点符号
        best_cut = -1
        for i in range(len(search_text) - 1, -1, -1):
            if search_text[i] in punctuation:
                best_cut = i + 1  # 包含标点符号
                break

        # 如果找到了合适的标点位置
        if best_cut > 0 and best_cut <= max_length + 10:
            return text[:best_cut].strip()

        # 如果没找到标点符号，退而求其次在空格处截断
        for i in range(min(max_length, len(text)) - 1, -1, -1):
            if text[i] == ' ':
                return text[:i].strip() + '...'

        # 最后的备选方案：直接在max_length处截断，并添加省略号
        return text[:max_length].strip() + '...'

    def validate(self) -> bool:
        """
        验证必填字段是否完整

        Returns:
            bool: 验证通过返回True，否则返回False
        """
        required_fields = [
            self.barcode,
            self.call_number,
            self.douban_rating,
            self.final_review_reason,
            self.cover_image_url
        ]
        return all(field is not None and str(field).strip() != "" for field in required_fields)


@dataclass
class OutputPaths:
    """输出路径集合"""

    book_dir: str           # 图书输出目录（以条码命名）
    pic_dir: str            # pic子目录
    html_file: str          # HTML文件路径
    image_file: str         # 图片文件路径
    cover_image: str        # 封面图片路径
    qrcode_image: str       # 二维码图片路径
