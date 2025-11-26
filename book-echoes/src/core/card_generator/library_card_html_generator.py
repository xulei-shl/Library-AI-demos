"""
图书馆借书卡HTML生成器
负责生成复古风格的借书卡HTML
"""

import os
import random
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import radar
from faker import Faker
from src.utils.logger import get_logger
from .library_card_models import LibraryCardData, BorrowerRecord

logger = get_logger(__name__)


class LibraryCardHTMLGenerator:
    """图书馆借书卡HTML生成器"""
    
    def __init__(self, config: Dict):
        """
        初始化HTML生成器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.template_path = config.get('template_path', 'config/library_card_template.html')
        self.borrower_records_count = config.get('borrower_records_count', 3)
        self.chinese_name_ratio = config.get('chinese_name_ratio', 0.8)
        self.output_suffix = config.get('output_suffix', '-S')
        
        # 日期范围配置
        date_range = config.get('date_range', {})
        self.date_start = date_range.get('start', 'auto')
        self.date_end = date_range.get('end', 'auto')
        
        # 初始化Faker
        self.faker_cn = Faker('zh_CN')
        self.faker_en = Faker('en_US')
        self.handwriting_fonts = config.get(
            'handwriting_fonts',
            [
                'font-handwriting-cn',
                'font-handwriting-yunfeng',
                'font-handwriting-pingfang',
                'font-handwriting-hetang',
                'font-handwriting-jinnian',
                'font-handwriting-yangrendong',
                'font-handwriting-en',
            ],
        )
        
        # 模板缓存
        self.template_cache = None
    
    def generate_html(
        self, card_data: LibraryCardData, output_path: str
    ) -> Tuple[bool, str]:
        """
        生成HTML文件
        
        Args:
            card_data: 图书馆借书卡数据
            output_path: 输出路径（不含-S后缀，会自动添加）
        
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
            html_content = self.fill_template(template, card_data)
            
            # 添加-S后缀到输出路径
            output_path_with_suffix = self._add_suffix_to_path(output_path)
            
            # 保存HTML文件
            if self.save_html(html_content, output_path_with_suffix):
                logger.debug(f"借书卡HTML生成成功：{output_path_with_suffix}")
                return True, output_path_with_suffix
            else:
                logger.error(f"借书卡HTML保存失败：{output_path_with_suffix}")
                return False, ""
        
        except Exception as e:
            logger.error(f"借书卡HTML生成失败，书目条码：{card_data.barcode}，错误：{e}")
            return False, ""
    
    def _add_suffix_to_path(self, path: str) -> str:
        """
        在文件名中添加-S后缀
        例如: "path/123456.html" -> "path/123456-S.html"
        """
        base, ext = os.path.splitext(path)
        return f"{base}{self.output_suffix}{ext}"
    
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
            logger.critical(f"错误：借书卡HTML模板文件不存在：{self.template_path}")
            return None
        
        try:
            # 读取模板文件
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # 缓存模板
            self.template_cache = template
            
            logger.debug(f"借书卡HTML模板加载成功：{self.template_path}")
            return template
        
        except Exception as e:
            logger.critical(f"错误：无法加载借书卡HTML模板：{self.template_path}，错误：{e}")
            return None
    
    def fill_template(self, template: str, card_data: LibraryCardData) -> str:
        """
        填充HTML模板
        
        Args:
            template: 模板字符串
            card_data: 图书馆借书卡数据
        
        Returns:
            str: 填充后的HTML内容
        """
        # 生成借阅记录HTML
        borrower_records_html = self.generate_borrower_records_html(card_data.borrower_records)
        
        # 定义占位符映射
        replacements = {
            '{{CARD_NUMBER}}': card_data.card_number,
            '{{AUTHOR}}': self.handle_empty_field(card_data.author),
            '{{TITLE}}': card_data.full_title,
            '{{CALL_NO}}': card_data.call_no,
            '{{YEAR}}': self.handle_empty_field(card_data.year),
            '{{BORROWER_RECORDS}}': borrower_records_html,
        }
        
        # 执行替换
        html = template
        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)
        
        return html
    
    def handle_empty_field(self, value: Optional[str], default: str = "") -> str:
        """
        处理空字段,并将浮点数格式的整数转换为整数字符串
        
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
    
    def generate_borrower_records_html(self, records: List[BorrowerRecord]) -> str:
        """
        生成借阅记录的HTML
        
        Args:
            records: 借阅记录列表
        
        Returns:
            str: 借阅记录HTML
        """
        html_parts = []
        
        font_sequence = self._generate_font_sequence(len(records))
        
        for record, font_class in zip(records, font_sequence):
            display_date = record.format_date_for_display()
            
            # 随机选择字体样式和旋转角度
            rotation = random.choice(['', 'transform rotate-1', 'transform -rotate-2'])
            text_size = random.choice(['text-xl', 'text-2xl'])
            padding = random.choice(['pl-1', 'pl-2', 'pl-4', 'pl-6'])
            
            html = f'''
            <!-- 记录行 -->
            <div class="grid-row">
                <div class="col-date">
                    <span class="font-stamp stamp-text text-sm {rotation}">{display_date}</span>
                </div>
                <div class="col-name">
                    <span class="{font_class} {text_size} text-gray-600 {padding}">{record.name}</span>
                </div>
            </div>'''
            
            html_parts.append(html)
        
        # 添加空行
        empty_rows_count = max(0, 7 - len(records))  # 总共7行，减去已有记录
        for _ in range(empty_rows_count):
            html_parts.append('<div class="grid-row"></div>')
        
        return '\n'.join(html_parts)
    
    def _generate_font_sequence(self, count: int) -> List[str]:
        """
        为单张卡片生成字体序列，尽量保证不重复
        """
        fonts = list(self.handwriting_fonts) if self.handwriting_fonts else ['font-handwriting-cn']
        random.shuffle(fonts)
        sequence: List[str] = []
        
        while len(sequence) < count:
            if not fonts:
                fonts = list(self.handwriting_fonts) if self.handwriting_fonts else ['font-handwriting-cn']
                random.shuffle(fonts)
            sequence.append(fonts.pop())
        
        return sequence
    
    def _is_chinese_name(self, name: str) -> bool:
        """
        判断是否为中文名
        
        Args:
            name: 姓名
        
        Returns:
            bool: 是否为中文名
        """
        # 简单判断：如果包含中文字符，则认为是中文名
        for char in name:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
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
            logger.error(f"保存借书卡HTML文件失败：{output_path}，错误：{e}")
            return False
    
    def generate_random_borrower_records(self) -> List[BorrowerRecord]:
        """
        生成随机借阅记录
        
        Returns:
            List[BorrowerRecord]: 借阅记录列表
        """
        records = []
        
        # 计算日期范围
        start_date = self._get_start_date()
        end_date = self._get_end_date()
        
        # 随机生成1到borrower_records_count条记录
        actual_count = random.randint(1, self.borrower_records_count)
        
        for _ in range(actual_count):
            # 生成随机日期
            random_datetime = radar.random_date(start=start_date, stop=end_date)
            date_str = random_datetime.strftime("%Y-%m-%d")
            
            # 生成随机姓名（80%中文，20%英文）
            if random.random() < self.chinese_name_ratio:
                name = self.faker_cn.name()
            else:
                name = self.faker_en.name()
            
            records.append(BorrowerRecord(date=date_str, name=name))
        
        return records
    
    def _get_start_date(self) -> datetime:
        """
        获取开始日期
        
        Returns:
            datetime: 开始日期
        """
        if self.date_start == 'auto':
            # 当前年份的1月1日
            now = datetime.now()
            return datetime(now.year, 1, 1)
        else:
            # 解析指定日期
            return datetime.strptime(self.date_start, "%Y-%m-%d")
    
    def _get_end_date(self) -> datetime:
        """
        获取结束日期
        
        Returns:
            datetime: 结束日期
        """
        if self.date_end == 'auto':
            # 当前日期
            return datetime.now()
        else:
            # 解析指定日期
            return datetime.strptime(self.date_end, "%Y-%m-%d")
