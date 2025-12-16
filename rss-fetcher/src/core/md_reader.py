#!/usr/bin/env python3
"""MD文档读取模块

该模块负责扫描指定路径下的MD文档，提取标题和内容，
并转换为标准的文章数据结构，为后续处理流程提供统一的输入格式。

Author: Assistant
Date: 2025-12-16
"""

import os
import glob
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import re

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MDDocument:
    """MD文档数据模型"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.title = self._extract_title()
        self.content = ""
        self.size = 0
        self.modified_time = None
        
    def _extract_title(self) -> str:
        """从文件名提取标题"""
        # 去除文件扩展名
        title = os.path.splitext(self.filename)[0]
        
        # 应用标题清理规则
        title = self._cleanup_title(title)
        
        return title
        
    def _cleanup_title(self, title: str) -> str:
        """清理标题中的特殊字符"""
        # 移除或替换常见的特殊字符
        cleanup_rules = [
            (r'[_\-]+', ' '),  # 下划线和连字符替换为空格
            (r'\s+', ' '),     # 多个空格合并为一个
            (r'^\s+|\s+$', ''), # 去除首尾空格
        ]
        
        for pattern, replacement in cleanup_rules:
            title = re.sub(pattern, replacement, title)
            
        return title.strip()
        
    def read_content(self) -> bool:
        """读取文件内容"""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.content = f.read()
            self.size = len(self.content)
            
            # 获取文件修改时间
            file_stat = os.stat(self.filepath)
            self.modified_time = datetime.fromtimestamp(file_stat.st_mtime)
            
            logger.debug(f"成功读取MD文件: {self.filename}, 大小: {self.size} 字符")
            return True
            
        except Exception as e:
            logger.error(f"读取MD文件失败 {self.filepath}: {e}")
            return False
            
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'filename': self.filename,
            'title': self.title,
            'content': self.content,
            'full_text': self.content,  # 兼容字段
            'source': '本地MD文档',
            'url': '',  # MD文档无URL
            'file_size': self.size,
            'modified_time': self.modified_time.isoformat() if self.modified_time else '',
            # 以下字段由后续处理步骤填充
            'filter_status': '',
            'filter_pass': False,
            'filter_reason': '',
            'llm_score': 0,
            'llm_summary': '',
            'llm_analysis': '',
            'llm_tags': '[]',
            'llm_mentioned_books': '[]',
            'llm_topic_focus': '',
            'llm_thematic_essence': '',
            'llm_primary_dimension': '',
            'llm_reason': '',
            'llm_error': '',
            'llm_raw_response': '',
            'llm_status': ''
        }


class MDReader:
    """MD文档读取器"""
    
    SUPPORTED_EXTENSIONS = ['.md', '.markdown']
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化MD读取器
        
        Args:
            config: 配置字典，包含扫描规则和输出设置
        """
        self.config = config or {}
        self.recursive_scan = self.config.get('recursive_scan', True)
        self.supported_extensions = self.config.get('supported_extensions', self.SUPPORTED_EXTENSIONS)
        
    def scan_directory(self, base_path: str) -> List[MDDocument]:
        """扫描目录下的所有MD文件
        
        Args:
            base_path: 要扫描的根目录路径
            
        Returns:
            MDDocument对象列表
            
        Raises:
            FileNotFoundError: 如果指定路径不存在
            PermissionError: 如果没有访问权限
        """
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"指定的路径不存在: {base_path}")
            
        if not os.path.isdir(base_path):
            raise NotADirectoryError(f"指定的路径不是目录: {base_path}")
            
        if not os.access(base_path, os.R_OK):
            raise PermissionError(f"没有读取权限: {base_path}")
            
        logger.info(f"开始扫描目录: {base_path}")
        logger.info(f"递归扫描: {self.recursive_scan}")
        logger.info(f"支持的文件扩展名: {self.supported_extensions}")
        
        md_documents = []
        pattern = "**/*" if self.recursive_scan else "*"
        
        for ext in self.supported_extensions:
            search_pattern = os.path.join(base_path, pattern + ext)
            matching_files = glob.glob(search_pattern, recursive=self.recursive_scan)
            
            for filepath in matching_files:
                if os.path.isfile(filepath):
                    try:
                        doc = MDDocument(filepath)
                        if doc.read_content():
                            md_documents.append(doc)
                        else:
                            logger.warning(f"跳过无法读取的文件: {filepath}")
                    except Exception as e:
                        logger.error(f"处理文件时出错 {filepath}: {e}")
                        continue
        
        logger.info(f"扫描完成，找到 {len(md_documents)} 个有效的MD文件")
        return md_documents
        
    def convert_to_article_structure(self, md_documents: List[MDDocument]) -> List[Dict[str, Any]]:
        """将MD文档转换为标准文章数据结构
        
        Args:
            md_documents: MD文档对象列表
            
        Returns:
            标准化的文章数据字典列表
        """
        logger.info(f"开始转换 {len(md_documents)} 个MD文档为标准结构")
        
        articles = []
        for doc in md_documents:
            try:
                article = doc.to_dict()
                articles.append(article)
                logger.debug(f"转换文档: {doc.filename} -> {article['title']}")
            except Exception as e:
                logger.error(f"转换文档失败 {doc.filename}: {e}")
                continue
                
        logger.info(f"成功转换 {len(articles)} 个文档为标准结构")
        return articles
        
    def generate_excel_filename(self) -> str:
        """生成Excel文件名
        
        Returns:
            格式化的Excel文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pattern = self.config.get('excel_filename_pattern', '文章汇总分析_{timestamp}')
        
        filename = pattern.format(timestamp=timestamp)
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
            
        return filename
        
    def process_directory(self, base_path: str) -> Dict[str, Any]:
        """完整的目录处理流程
        
        Args:
            base_path: MD文档目录路径
            
        Returns:
            处理结果字典，包含文章列表和统计信息
        """
        logger.info("=" * 60)
        logger.info("开始MD文档处理流程")
        logger.info("=" * 60)
        
        try:
            # 扫描目录
            md_documents = self.scan_directory(base_path)
            
            if not md_documents:
                logger.warning("未找到任何MD文档")
                return {
                    'success': False,
                    'articles': [],
                    'count': 0,
                    'error': '未找到MD文档'
                }
                
            # 转换为标准结构
            articles = self.convert_to_article_structure(md_documents)
            
            # 生成Excel文件名
            excel_filename = self.generate_excel_filename()
            
            # 统计信息
            total_size = sum(doc.size for doc in md_documents)
            avg_size = total_size / len(md_documents) if md_documents else 0
            
            result = {
                'success': True,
                'articles': articles,
                'count': len(articles),
                'excel_filename': excel_filename,
                'statistics': {
                    'total_documents': len(md_documents),
                    'total_size': total_size,
                    'average_size': avg_size,
                    'base_path': base_path
                }
            }
            
            logger.info("=" * 60)
            logger.info("MD文档处理完成")
            logger.info(f"处理文档数: {result['count']}")
            logger.info(f"Excel文件名: {excel_filename}")
            logger.info(f"总大小: {total_size} 字符")
            logger.info(f"平均大小: {avg_size:.0f} 字符")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"MD文档处理失败: {e}", exc_info=True)
            return {
                'success': False,
                'articles': [],
                'count': 0,
                'error': str(e)
            }


# 便利函数
def read_md_directory(base_path: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """便利函数：读取MD目录
    
    Args:
        base_path: MD文档目录路径
        config: 配置选项
        
    Returns:
        处理结果字典
    """
    reader = MDReader(config)
    return reader.process_directory(base_path)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python md_reader.py <MD文档目录路径>")
        sys.exit(1)
        
    base_path = sys.argv[1]
    
    try:
        result = read_md_directory(base_path)
        
        if result['success']:
            print(f"✅ 成功处理 {result['count']} 个MD文档")
            print(f"📄 Excel文件名: {result['excel_filename']}")
            print(f"📊 统计信息:")
            stats = result['statistics']
            print(f"   - 总文档数: {stats['total_documents']}")
            print(f"   - 总大小: {stats['total_size']} 字符")
            print(f"   - 平均大小: {stats['average_size']:.0f} 字符")
        else:
            print(f"❌ 处理失败: {result['error']}")
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        sys.exit(1)
