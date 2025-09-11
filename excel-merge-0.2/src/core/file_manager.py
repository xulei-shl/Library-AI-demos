"""
文件管理模块
负责文件移动和目录管理

作者: Qoder AI
"""
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..utils.logger import logger
from ..config.settings import get_processed_folder_path


class FileManager:
    """
    文件管理器
    负责文件移动和目录管理
    
    Author: Qoder AI
    """
    
    def __init__(self, base_directory: Path):
        """
        初始化文件管理器
        
        Args:
            base_directory: 基础目录路径（源Excel文件目录）
            
        Author: Qoder AI
        """
        self.base_directory = base_directory
        # 使用绝对路径配置的已处理文件夹
        self.processed_folder = get_processed_folder_path()
        logger.debug(f"FileManager: 初始化文件管理器，基础目录: {base_directory}")
        logger.debug(f"FileManager: 已处理文件夹: {self.processed_folder}")
    
    def ensure_directories(self) -> bool:
        """
        确保必要的目录存在，如果不存在则自动创建
        
        Returns:
            是否成功创建目录
            
        Author: Qoder AI
        """
        try:
            # 创建已处理文件夹
            if not self.processed_folder.exists():
                self.processed_folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"FileManager: 已创建已处理目录: {self.processed_folder}")
            else:
                logger.debug(f"FileManager: 已处理目录已存在: {self.processed_folder}")
            
            return True
            
        except Exception as e:
            logger.exception(f"FileManager: 创建目录失败: {str(e)}")
            return False
    
    def move_to_processed(self, file_path: Path) -> bool:
        """
        将文件移动到已处理文件夹
        
        Args:
            file_path: 要移动的文件路径
            
        Returns:
            是否移动成功
        """
        try:
            if not file_path.exists():
                logger.error(f"FileManager: 文件不存在，无法移动: {file_path}")
                return False
            
            # 确保已处理目录存在
            self.processed_folder.mkdir(exist_ok=True)
            
            # 目标路径
            target_path = self.processed_folder / file_path.name
            
            # 如果目标文件已存在，添加时间戳
            if target_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = file_path.stem, timestamp, file_path.suffix
                new_name = f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                target_path = self.processed_folder / new_name
                logger.info(f"FileManager: 目标文件已存在，重命名为: {new_name}")
            
            # 移动文件
            shutil.move(str(file_path), str(target_path))
            logger.info(f"FileManager: 文件移动成功: {file_path.name} -> {target_path}")
            
            return True
            
        except Exception as e:
            logger.exception(f"FileManager: 移动文件失败: {file_path}, 错误: {str(e)}")
            return False
    
    def get_processed_files(self) -> List[Path]:
        """
        获取已处理文件夹中的所有文件
        
        Returns:
            已处理文件列表
        """
        try:
            if not self.processed_folder.exists():
                return []
            
            processed_files = []
            for pattern in ['*.xlsx', '*.xls']:
                processed_files.extend(self.processed_folder.glob(pattern))
            
            logger.debug(f"FileManager: 已处理文件夹中有 {len(processed_files)} 个文件")
            return processed_files
            
        except Exception as e:
            logger.exception(f"FileManager: 获取已处理文件列表失败: {str(e)}")
            return []
    
    def is_file_processed(self, filename: str) -> bool:
        """
        检查文件是否已被处理过
        
        Args:
            filename: 文件名
            
        Returns:
            是否已处理
        """
        try:
            processed_files = self.get_processed_files()
            
            # 检查是否有同名文件或带时间戳的文件
            for processed_file in processed_files:
                if processed_file.name == filename:
                    return True
                # 检查是否是带时间戳的同名文件
                if processed_file.name.startswith(Path(filename).stem):
                    return True
            
            return False
            
        except Exception as e:
            logger.exception(f"FileManager: 检查文件处理状态失败: {filename}, 错误: {str(e)}")
            return False