"""
HTML生成器模块
负责填充HTML模板并生成HTML文件
"""

import os
from typing import Dict, Optional, Tuple
from src.utils.logger import get_logger
from .models import BookCardData

logger = get_logger(__name__)


class HTMLGenerator:
    """HTML生成器类"""

    def __init__(self, config: Dict):
        """
        初始化HTML生成器

        Args:
            config: 配置字典
        """
        self.config = config
        self.template_path = config.get('template_path', 'config/card_template.html')
        self.template_cache = None

    def generate_html(
        self, book_data: BookCardData, output_path: str
    ) -> Tuple[bool, str]:
        """
        生成HTML文件

        Args:
            book_data: 图书卡片数据
            output_path: 输出路径

        Returns:
            Tuple[bool, str]: (是否成功, 输出路径)
        """
        try:
            # 加载模板
            template = self.load_template()

            if not template:
                logger.error("HTML模板加载失败")
                return False, ""

            # 填充模板
            html_content = self.fill_template(template, book_data)

            # 保存HTML文件
            if self.save_html(html_content, output_path):
                logger.debug(f"HTML生成成功：{output_path}")
                return True, output_path
            else:
                logger.error(f"HTML保存失败：{output_path}")
                return False, ""

        except Exception as e:
            logger.error(f"HTML生成失败，书目条码：{book_data.barcode}，错误：{e}")
            return False, ""

    def load_template(self) -> Optional[str]:
        """
        加载HTML模板文件（支持缓存）

        Returns:
            Optional[str]: 模板内容，失败返回None
        """
        # 如果已有缓存，直接返回
        if self.template_cache:
            return self.template_cache

        # 检查模板文件是否存在
        if not os.path.exists(self.template_path):
            logger.critical(f"错误：HTML模板文件不存在：{self.template_path}")
            return None

        try:
            # 读取模板文件
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()

            # 缓存模板
            self.template_cache = template

            logger.debug(f"HTML模板加载成功：{self.template_path}")
            return template

        except Exception as e:
            logger.critical(f"错误：无法加载HTML模板：{self.template_path}，错误：{e}")
            return None

    def fill_template(self, template: str, book_data: BookCardData) -> str:
        """
        填充HTML模板

        Args:
            template: 模板字符串
            book_data: 图书卡片数据

        Returns:
            str: 填充后的HTML内容
        """
        # 定义占位符映射
        replacements = {
            '{{AUTHOR}}': self.handle_empty_field(book_data.author),
            '{{TITLE}}': book_data.full_title,
            '{{PUBLISHER}}': self.handle_empty_field(book_data.publisher),
            '{{PUB_YEAR}}': self.handle_empty_field(book_data.pub_year),
            '{{CALL_NUMBER}}': book_data.call_number,
            '{{DOUBAN_RATING}}': str(book_data.douban_rating),
            '{{RECOMMENDATION}}': book_data.truncated_reason,
        }

        # 执行替换
        html = template
        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)

        return html

    def handle_empty_field(self, value: Optional[str], default: str = "") -> str:
        """
        处理空字段

        Args:
            value: 字段值
            default: 默认值

        Returns:
            str: 处理后的值
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        
        # 处理数字类型：如果是浮点数且为整数值，转换为整数
        if isinstance(value, (int, float)):
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value)
        
        # 处理字符串类型：如果是类似"2025.0"的字符串，转换为整数
        if isinstance(value, str):
            # 尝试转换为浮点数再判断是否为整数
            try:
                float_value = float(value)
                if float_value.is_integer():
                    return str(int(float_value))
                else:
                    return value  # 保持原值（如"2025.5"）
            except (ValueError, TypeError):
                # 无法转换为浮点数，保持原字符串
                return value
        
        return str(value)

    def save_html(self, content: str, output_path: str) -> bool:
        """
        保存HTML文件

        Args:
            content: HTML内容
            output_path: 输出路径

        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 保存文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

        except Exception as e:
            logger.error(f"保存HTML文件失败：{output_path}，错误：{e}")
            return False
