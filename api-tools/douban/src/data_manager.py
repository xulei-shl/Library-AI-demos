import logging
import os
import pandas as pd
from typing import Dict, List
"""
数据管理模块
负责保存图书信息到Excel文件
"""

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理类"""
    
    def __init__(self, filename: str = "豆瓣图书信息.xlsx"):
        """
        初始化数据管理器
        
        Args:
            filename: Excel文件名
        """
        self.filename = filename
        self.book_data = []
    
    def add_book_info(self, book_info: Dict, immediate_save: bool = False):
        """
        添加图书信息
        
        Args:
            book_info: 图书信息字典
            immediate_save: 是否立即保存到Excel，默认为False
        """
        if book_info:  # 只有当图书信息不为空时才添加
            self.book_data.append(book_info)
            logger.debug(f"添加图书信息: {book_info.get('题名', 'Unknown')}")
            
            # 如果需要立即保存
            if immediate_save:
                self._save_single_record(book_info)
    
    def _save_single_record(self, book_info: Dict):
        """
        保存单条记录到Excel文件
        
        Args:
            book_info: 单条图书信息字典
        """
        try:
            combined_data = []
            
            # 读取现有数据（如果文件存在）
            if os.path.exists(self.filename):
                try:
                    existing_df = pd.read_excel(self.filename, sheet_name='图书信息')
                    combined_data = existing_df.to_dict('records')
                    logger.debug(f"读取现有Excel文件，包含 {len(combined_data)} 条记录")
                except Exception as e:
                    logger.warning(f"读取现有Excel文件失败: {e}，将创建新文件")
            
            # 添加新记录
            combined_data.append(book_info)
            
            # 创建DataFrame并保存
            df = pd.DataFrame(combined_data)
            
            with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='图书信息', index=False)
                
                # 调整列宽
                worksheet = writer.sheets['图书信息']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"已保存图书信息到Excel: {book_info.get('题名', 'Unknown')}，总共 {len(combined_data)} 条记录")
            
        except Exception as e:
            logger.error(f"保存单条记录到Excel时发生错误: {e}")
    
    def get_book_data(self) -> List[Dict]:
        """
        获取所有图书数据
        
        Returns:
            图书信息列表
        """
        return self.book_data
    
    def clear_data(self):
        """清空所有数据"""
        self.book_data.clear()
        logger.info("已清空所有图书数据")
    
    def save_to_excel(self, filename: str = None, append: bool = True):
        """
        保存图书信息到Excel文件
        
        Args:
            filename: Excel文件名，如果为None则使用初始化时的文件名
            append: 是否追加到现有文件，默认为True
        """
        # 如果没有指定filename，使用实例初始化时的filename
        target_filename = filename or self.filename
        target_filename = target_filename or "豆瓣图书信息.xlsx"
        
        try:
            if not self.book_data:
                logger.warning("没有图书数据可保存")
                return
            
            combined_data = []
            
            # 如果是追加模式且文件存在，读取现有数据
            if append and os.path.exists(target_filename):
                try:
                    existing_df = pd.read_excel(target_filename, sheet_name='图书信息')
                    combined_data = existing_df.to_dict('records')
                    logger.info(f"已读取现有Excel文件，包含 {len(combined_data)} 条记录")
                except Exception as e:
                    logger.warning(f"读取现有Excel文件失败: {e}，将创建新文件")
            
            # 合并数据
            combined_data.extend(self.book_data)
            
            # 创建DataFrame
            df = pd.DataFrame(combined_data)
            
            # 保存到Excel
            with pd.ExcelWriter(target_filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='图书信息', index=False)
                
                # 调整列宽
                worksheet = writer.sheets['图书信息']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            action = "追加保存" if append and os.path.exists(target_filename) else "保存"
            logger.info(f"图书信息已{action}到 {target_filename}，共 {len(combined_data)} 条记录")
            
        except Exception as e:
            logger.error(f"保存Excel文件时发生错误: {e}")
    
    def get_data_count(self) -> int:
        """
        获取当前数据条数
        
        Returns:
            数据条数
        """
        return len(self.book_data)
    
    def is_empty(self) -> bool:
        """
        检查是否没有数据
        
        Returns:
            是否为空
        """
        return len(self.book_data) == 0