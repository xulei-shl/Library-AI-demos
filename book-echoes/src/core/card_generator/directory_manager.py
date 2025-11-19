"""
目录管理器模块
负责创建和管理输出目录结构
"""

import os
import re
import shutil
import random
from typing import Optional
from src.utils.logger import get_logger
from .models import OutputPaths

logger = get_logger(__name__)


class DirectoryManager:
    """目录管理器类"""

    def __init__(self, config: dict):
        """
        初始化目录管理器

        Args:
            config: 配置字典
        """
        self.config = config
        self.base_dir = config.get('output', {}).get('base_dir', 'runtime/outputs')
        self.html_extension = config.get('output', {}).get('html_extension', '.html')
        self.image_extension = config.get('output', {}).get('image_extension', '.png')
        self.logo_source_dir = config.get('logo', {}).get('source_dir', 'data/logo')
        self.cover_filename = config.get('image_download', {}).get('cover_filename', 'cover')

    def create_book_directory(self, barcode: str) -> Optional[OutputPaths]:
        """
        创建图书输出目录结构

        Args:
            barcode: 书目条码

        Returns:
            Optional[OutputPaths]: 输出路径集合,失败返回None
        """
        # 清理条码
        clean_barcode = self.clean_barcode(barcode)

        # 构建路径
        book_dir = os.path.join(self.base_dir, clean_barcode)
        pic_dir = os.path.join(book_dir, 'pic')
        html_file = os.path.join(book_dir, f"{clean_barcode}{self.html_extension}")
        image_file = os.path.join(book_dir, f"{clean_barcode}{self.image_extension}")
        cover_image = os.path.join(pic_dir, self.cover_filename)  # 扩展名后续根据实际下载确定
        qrcode_image = os.path.join(
            pic_dir,
            self.config.get('qrcode', {}).get('filename', 'qrcode.png')
        )

        # 创建目录
        try:
            if not self.ensure_directory_exists(book_dir):
                return None

            if not self.ensure_directory_exists(pic_dir):
                return None

            logger.debug(f"成功创建目录结构,书目条码:{barcode}")

            return OutputPaths(
                book_dir=book_dir,
                pic_dir=pic_dir,
                html_file=html_file,
                image_file=image_file,
                cover_image=cover_image,
                qrcode_image=qrcode_image
            )

        except Exception as e:
            logger.error(f"创建目录失败,书目条码:{barcode},错误:{e}")
            return None

    def copy_logo_files(self, pic_dir: str) -> bool:
        """
        复制Logo文件到pic目录

        Args:
            pic_dir: 目标pic目录路径

        Returns:
            bool: 复制成功返回True,否则返回False
        """
        if not os.path.exists(self.logo_source_dir):
            logger.warning(f"Logo源目录不存在:{self.logo_source_dir}")
            return False

        if not os.path.isdir(self.logo_source_dir):
            logger.warning(f"Logo源路径不是目录:{self.logo_source_dir}")
            return False

        try:
            # 获取所有Logo文件
            logo_files = os.listdir(self.logo_source_dir)

            if not logo_files:
                logger.warning(f"Logo目录为空:{self.logo_source_dir}")
                return False

            # 复制每个Logo文件(跳过 b-*.png 文件,这些文件将在后续随机选择一个复制为 b.png)
            copied_count = 0
            for filename in logo_files:
                source_path = os.path.join(self.logo_source_dir, filename)

                # 只复制文件,跳过目录
                if not os.path.isfile(source_path):
                    continue

                # 跳过所有 b-*.png 文件,这些文件将在后续随机选择
                if filename.startswith('b-') and filename.endswith('.png'):
                    continue

                dest_path = os.path.join(pic_dir, filename)

                try:
                    shutil.copy2(source_path, dest_path)
                    copied_count += 1
                    logger.debug(f"复制Logo文件:{filename} -> {dest_path}")
                except Exception as e:
                    logger.warning(f"复制Logo文件失败:{filename},错误:{e}")

            logger.debug(f"成功复制 {copied_count} 个Logo文件到:{pic_dir}")

            # 处理背景图 b.png 的随机选择逻辑
            # 从源目录中随机选择一个 b-*.png 文件复制为 b.png
            target_b_png = os.path.join(pic_dir, 'b.png')
            b_candidates = [
                f for f in logo_files 
                if f.startswith('b-') and f.endswith('.png') and os.path.isfile(os.path.join(self.logo_source_dir, f))
            ]
            
            if b_candidates:
                selected_b = random.choice(b_candidates)
                source_b_path = os.path.join(self.logo_source_dir, selected_b)
                try:
                    shutil.copy2(source_b_path, target_b_png)
                    logger.debug(f"从源目录随机选择 {selected_b} 复制为 b.png")
                except Exception as e:
                    logger.warning(f"复制随机b.png失败 ({selected_b}):{e}")
                    return False
            else:
                logger.warning("源目录未找到 b-*.png 候选文件,无法生成 b.png")
                return False

            return True

        except Exception as e:
            logger.error(f"Logo文件复制失败:{e}")
            return False

    def clean_barcode(self, barcode: str) -> str:
        """
        清理条码字符串(去除非法字符)

        Args:
            barcode: 原始条码

        Returns:
            str: 清理后的条码
        """
        # 移除Windows文件名非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        cleaned = re.sub(illegal_chars, '', barcode)

        # 去除首尾空格
        cleaned = cleaned.strip()

        # 如果清理后为空,使用默认值
        if not cleaned:
            cleaned = "unknown_barcode"

        return cleaned

    def ensure_directory_exists(self, directory: str) -> bool:
        """
        确保目录存在,不存在则创建

        Args:
            directory: 目录路径

        Returns:
            bool: 目录存在或创建成功返回True,否则返回False
        """
        if os.path.exists(directory):
            if os.path.isdir(directory):
                return True
            else:
                logger.error(f"路径存在但不是目录:{directory}")
                return False

        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"创建目录:{directory}")
            return True
        except Exception as e:
            logger.error(f"无法创建目录:{directory},错误:{e}")
            return False
