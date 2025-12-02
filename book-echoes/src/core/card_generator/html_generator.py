"""
HTML生成器模块
负责填充HTML模板并生成HTML文件
"""

import os
from typing import Dict, Optional, Tuple, Any
from src.utils.logger import get_logger
from .models import BookCardData
from .field_transformers import FieldTransformerFactory

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
        
        # 解析字段转换器配置
        # 允许配置中省略或留空字段转换器,避免None造成迭代异常
        self.field_transformers_config = config.get('field_transformers') or {}
        self._init_field_transformers()

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

    def _init_field_transformers(self):
        """
        初始化字段转换器
        根据配置创建转换器实例
        """
        self.transformers = {}
        
        for field_name, transformer_config in self.field_transformers_config.items():
            try:
                transformer_type = transformer_config.get('type', 'direct')
                transformer = FieldTransformerFactory.create(transformer_type)
                self.transformers[field_name] = {
                    'transformer': transformer,
                    'config': transformer_config
                }
                logger.debug(f"字段转换器初始化成功: {field_name} -> {transformer_type}")
            except Exception as e:
                logger.warning(f"字段转换器初始化失败: {field_name}, 错误: {e}")

    def _apply_field_transformer(self, field_name: str, book_data: BookCardData) -> str:
        """
        应用字段转换器
        
        Args:
            field_name: 字段名称
            book_data: 图书卡片数据
            
        Returns:
            str: 转换后的字段值
        """
        if field_name not in self.transformers:
            # 如果没有配置转换器,使用默认逻辑
            return self._get_default_field_value(field_name, book_data)
        
        transformer_info = self.transformers[field_name]
        transformer = transformer_info['transformer']
        config = transformer_info['config']
        
        # 获取源字段值
        source_field = config.get('source_field')
        if not source_field:
            logger.warning(f"字段转换器配置缺少source_field: {field_name}")
            return ""
        
        # 从book_data获取源字段值
        source_value = self._get_book_data_field(book_data, source_field)
        
        # 准备转换参数
        transform_kwargs = {
            'default': config.get('default', ''),
            'separator': config.get('separator', '/'),
            'suffix': config.get('suffix', ' 等'),
        }
        
        # 如果是完整标题转换器,需要传入副标题
        if config.get('type') == 'full_title':
            subtitle_field = config.get('subtitle_field')
            if subtitle_field:
                transform_kwargs['subtitle'] = self._get_book_data_field(book_data, subtitle_field)
        
        # 执行转换
        try:
            return transformer.transform(source_value, **transform_kwargs)
        except Exception as e:
            logger.error(f"字段转换失败: {field_name}, 错误: {e}")
            return config.get('default', '')

    def _get_book_data_field(self, book_data: BookCardData, field_name: str) -> Any:
        """
        从BookCardData对象获取字段值
        
        Args:
            book_data: 图书卡片数据
            field_name: 字段名称(支持中文字段名映射)
            
        Returns:
            Any: 字段值
        """
        # 字段名映射 (中文 -> 英文属性名)
        field_mapping = {
            '豆瓣作者': 'author',
            '豆瓣书名': 'title',
            '豆瓣副标题': 'subtitle',
            '豆瓣出版社': 'publisher',
            '豆瓣出版年': 'pub_year',
            '索书号': 'call_number',
            '豆瓣评分': 'douban_rating',
            '初评理由': 'final_review_reason',
        }
        
        # 转换字段名
        attr_name = field_mapping.get(field_name, field_name)
        
        # 获取属性值
        return getattr(book_data, attr_name, None)

    def _get_default_field_value(self, field_name: str, book_data: BookCardData) -> str:
        """
        获取字段的默认值(向后兼容旧逻辑)
        
        Args:
            field_name: 字段名称
            book_data: 图书卡片数据
            
        Returns:
            str: 字段值
        """
        # 默认映射逻辑(保持向后兼容)
        if field_name == 'AUTHOR':
            return self.handle_empty_field(book_data.author)
        elif field_name == 'TITLE':
            return book_data.full_title
        elif field_name == 'PUBLISHER':
            return self.handle_empty_field(book_data.publisher)
        elif field_name == 'PUB_YEAR':
            return self.handle_empty_field(book_data.pub_year)
        elif field_name == 'CALL_NUMBER':
            return book_data.call_number
        elif field_name == 'DOUBAN_RATING':
            return str(book_data.douban_rating)
        elif field_name == 'RECOMMENDATION':
            return book_data.truncated_reason
        else:
            return ""

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
        # 优先使用字段转换器,如果没有配置则使用默认逻辑
        replacements = {
            '{{AUTHOR}}': self._apply_field_transformer('AUTHOR', book_data),
            '{{TITLE}}': self._apply_field_transformer('TITLE', book_data),
            '{{PUBLISHER}}': self._apply_field_transformer('PUBLISHER', book_data),
            '{{PUB_YEAR}}': self._apply_field_transformer('PUB_YEAR', book_data),
            '{{CALL_NUMBER}}': self._apply_field_transformer('CALL_NUMBER', book_data),
            '{{DOUBAN_RATING}}': self._apply_field_transformer('DOUBAN_RATING', book_data),
            '{{RECOMMENDATION}}': self._apply_field_transformer('RECOMMENDATION', book_data),
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
