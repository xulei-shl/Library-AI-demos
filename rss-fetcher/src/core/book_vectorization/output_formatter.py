#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检索结果格式化器

提供将检索结果格式化为Markdown和JSON格式，并保存到文件的功能。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.utils.file_utils import (
    ensure_directory_exists,
    generate_filename,
    get_file_extension,
    safe_write_file
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def extract_md_filename(md_path: str) -> Optional[str]:
    """
    从MD文件路径中提取文件名（不含扩展名）
    
    Args:
        md_path: Markdown文件路径
        
    Returns:
        提取的文件名（不含扩展名），失败时返回None
    """
    try:
        if not md_path:
            logger.warning("MD文件路径为空")
            return None
            
        # 创建Path对象并获取文件名（不含扩展名）
        path_obj = Path(md_path)
        
        # 检查是否为文件（有文件名且以.md结尾）
        if path_obj.suffix.lower() != '.md':
            logger.warning(f"路径不是MD文件: {md_path}")
            return None
            
        filename_without_ext = path_obj.stem
        
        # 检查提取的文件名是否有效
        # 排除以点开头的隐藏文件（如.gitignore）和只有扩展名的情况
        if not filename_without_ext or filename_without_ext.startswith('.'):
            logger.warning(f"无法从路径中提取有效文件名: {md_path}")
            return None
            
        logger.debug(f"成功提取MD文件名: {filename_without_ext}")
        return filename_without_ext
        
    except Exception as e:
        logger.error(f"提取MD文件名失败: {md_path}, 错误: {e}")
        return None


class OutputFormatter:
    """检索结果格式化器"""
    
    def __init__(self, config: Dict):
        """
        初始化格式化器
        
        Args:
            config: 输出配置字典
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        self.formats = config.get('formats', ['markdown', 'json'])
        self.base_directory = config.get('base_directory', 'runtime/outputs/retrieval')
        self.filename_template = config.get('filename_template', 'books_{mode}_{timestamp}')
        self.include_timestamp = config.get('include_timestamp', True)
        self.timestamp_format = config.get('timestamp_format', '%Y%m%d_%H%M%S')
        self.auto_create_directory = config.get('auto_create_directory', True)
        
        logger.info(f"输出格式化器初始化完成，enabled={self.enabled}, formats={self.formats}")
    
    def format_as_markdown(self, results: List[Dict], metadata: Dict) -> str:
        """
        将结果格式化为Markdown
        
        Args:
            results: 检索结果列表
            metadata: 元数据（查询信息、时间等）
            
        Returns:
            格式化后的Markdown字符串
        """
        # 构建Markdown内容
        lines = []
        
        # 标题和基本信息
        mode = metadata.get('mode', 'unknown')
        query = metadata.get('query', '')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        lines.append(f"# 图书检索结果 - {mode.upper()}模式")
        lines.append("")
        lines.append(f"**检索时间**: {timestamp}")
        
        if query:
            lines.append(f"**查询内容**: {query}")
        
        if 'category' in metadata:
            lines.append(f"**分类**: {metadata['category']}")
        
        lines.append(f"**结果数量**: {len(results)}")
        lines.append("")
        
        # 检索参数
        lines.append("## 检索参数")
        lines.append("")
        for key, value in metadata.items():
            if key not in ['mode', 'query', 'category', 'results'] and value is not None:
                lines.append(f"- **{key}**: {value}")
        lines.append("")
        
        # 检索结果
        lines.append("## 检索结果")
        lines.append("")
        
        if not results:
            lines.append("😔 未找到匹配的书籍。")
        else:
            for idx, item in enumerate(results, start=1):
                title = item.get('title', item.get('douban_title', '未知'))
                author = item.get('author', item.get('douban_author', '未知'))
                rating = item.get('rating', item.get('douban_rating', '未知'))
                call_no = item.get('call_no', '-')
                summary = item.get('summary', '')
                
                lines.append(f"### [{idx}] {title}")
                lines.append("")
                lines.append(f"**作者**: {author}")
                lines.append(f"**评分**: {rating}")
                lines.append(f"**索书号**: {call_no}")
                
                # 相似度或融合分数
                similarity = item.get('similarity_score')
                fused_score = item.get('fused_score')
                
                if similarity is not None:
                    lines.append(f"**相似度**: {similarity:.4f}")
                
                if fused_score is not None:
                    lines.append(f"**融合分数**: {fused_score:.4f}")
                
                # 精确匹配标注
                if 'display_source' in item and item['display_source']:
                    lines.append(f"**匹配方式**: {item['display_source']}")
                
                # 简介
                if summary:
                    lines.append("")
                    lines.append("**简介**:")
                    lines.append("")
                    lines.append(summary)
                
                lines.append("")
                lines.append("---")
                lines.append("")
        
        return "\n".join(lines)
    
    def format_as_json(self, results: List[Dict], metadata: Dict) -> str:
        """
        将结果格式化为JSON
        
        Args:
            results: 检索结果列表
            metadata: 元数据（查询信息、时间等）
            
        Returns:
            格式化后的JSON字符串
        """
        # 构建JSON数据结构
        json_data = {
            "metadata": {
                "mode": metadata.get('mode', 'unknown'),
                "timestamp": datetime.now().isoformat(),
                "query": metadata.get('query', ''),
                "category": metadata.get('category'),
                "result_count": len(results)
            },
            "search_parameters": {},
            "results": results
        }
        
        # 添加检索参数
        for key, value in metadata.items():
            if key not in ['mode', 'query', 'category', 'results'] and value is not None:
                json_data["search_parameters"][key] = value
        
        # 确保所有结果都有必要的字段
        for result in results:
            # 统一字段名
            if 'douban_title' in result and 'title' not in result:
                result['title'] = result['douban_title']
            if 'douban_author' in result and 'author' not in result:
                result['author'] = result['douban_author']
            if 'douban_rating' in result and 'rating' not in result:
                result['rating'] = result['douban_rating']
        
        return json.dumps(json_data, ensure_ascii=False, indent=2)
    
    def save_results(self, results: List[Dict], metadata: Dict) -> Dict[str, str]:
        """
        保存结果到文件
        
        Args:
            results: 检索结果列表
            metadata: 元数据（查询信息、时间等）
            
        Returns:
            文件路径字典，键为格式名，值为文件路径
        """
        if not self.enabled:
            logger.info("文件输出功能已禁用，跳过保存")
            return {}
        
        if not self.formats:
            logger.warning("未配置输出格式，跳过保存")
            return {}
        
        # 确保输出目录存在
        if self.auto_create_directory:
            ensure_directory_exists(self.base_directory)
        
        # 检测是否为MD解析检索模式
        md_filename = None
        if 'from_md' in metadata and metadata['from_md']:
            md_filename = extract_md_filename(metadata['from_md'])
            if md_filename:
                logger.info(f"检测到MD解析检索模式，使用MD文件名: {md_filename}")
            else:
                logger.warning("MD文件名提取失败，将使用默认命名模板")
        
        # 准备文件名生成所需的元数据
        filename_metadata = {
            'mode': metadata.get('mode', 'unknown'),
            'timestamp': datetime.now().strftime(self.timestamp_format)
        }
        
        # 如果有查询内容，取前20个字符作为文件名的一部分
        if 'query' in metadata and metadata['query']:
            query_preview = metadata['query'][:20].replace(' ', '_')
            filename_metadata['query'] = query_preview
        
        # 生成基础文件名
        if md_filename:
            # MD解析检索模式：使用MD文件名作为前缀
            base_filename = f"{md_filename}_相关书目_{filename_metadata['timestamp']}"
            # 清理文件名中的非法字符
            base_filename = self._clean_filename(base_filename)
            logger.info(f"使用MD智能命名模板: {base_filename}")
        else:
            # 非MD解析或提取失败：使用原有命名模板
            base_filename = generate_filename(
                self.filename_template,
                filename_metadata,
                self.timestamp_format,
                self.include_timestamp
            )
        
        saved_files = {}
        
        # 保存各种格式
        for format_name in self.formats:
            try:
                if format_name == 'markdown':
                    content = self.format_as_markdown(results, metadata)
                    extension = get_file_extension('markdown')
                elif format_name == 'json':
                    content = self.format_as_json(results, metadata)
                    extension = get_file_extension('json')
                else:
                    logger.warning(f"不支持的输出格式: {format_name}")
                    continue
                
                # 构建完整文件路径
                filename = base_filename + extension
                file_path = f"{self.base_directory}/{filename}"
                
                # 写入文件
                safe_write_file(file_path, content)
                saved_files[format_name] = file_path
                
                logger.info(f"已保存{format_name}格式结果到: {file_path}")
                
            except Exception as e:
                logger.error(f"保存{format_name}格式结果失败: {e}")
                # 如果某个格式保存失败，继续尝试其他格式
                continue
        
        return saved_files
    
    def _clean_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            清理后的文件名
        """
        # 清理文件名中的非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        
        # 移除多余的连续下划线
        while "__" in filename:
            filename = filename.replace("__", "_")
        
        return filename