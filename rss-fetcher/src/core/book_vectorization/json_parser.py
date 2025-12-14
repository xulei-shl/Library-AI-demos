#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON文件解析器，用于从检索结果中提取book_id

该模块负责解析图书向量检索系统的JSON结果文件，
提取其中的书籍ID列表，供Excel导出使用。
"""

import json
from pathlib import Path
from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JsonParser:
    """JSON文件解析器，用于从检索结果中提取book_id"""
    
    def extract_book_ids(self, json_file_path: str) -> List[int]:
        """
        从JSON文件中提取所有book_id
        
        Args:
            json_file_path: JSON文件路径
            
        Returns:
            book_id列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: JSON格式错误或缺少必要字段
        """
        file_path = Path(json_file_path)
        
        # 检查文件是否存在
        if not file_path.exists():
            logger.error(f"JSON文件不存在: {json_file_path}")
            raise FileNotFoundError(f"JSON文件不存在: {json_file_path}")
        
        try:
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查JSON结构
            if 'results' not in data:
                logger.error("JSON文件缺少'results'字段")
                raise ValueError("JSON文件缺少'results'字段")
            
            results = data['results']
            if not isinstance(results, list):
                logger.error("'results'字段不是列表类型")
                raise ValueError("'results'字段不是列表类型")
            
            # 提取book_id
            book_ids = []
            for idx, item in enumerate(results):
                if not isinstance(item, dict):
                    logger.warning(f"跳过非字典类型的results项: 索引{idx}")
                    continue
                
                if 'book_id' not in item:
                    logger.warning(f"跳过缺少book_id的results项: 索引{idx}")
                    continue
                
                try:
                    book_id = int(item['book_id'])
                    book_ids.append(book_id)
                except (ValueError, TypeError) as e:
                    logger.warning(f"跳过无效的book_id: {item['book_id']}, 错误: {e}")
                    continue
            
            if not book_ids:
                logger.warning("未提取到任何有效的book_id")
            
            logger.info(f"从JSON文件提取到{len(book_ids)}个book_id")
            return book_ids
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON文件格式错误: {e}")
            raise ValueError(f"JSON文件格式错误: {e}")
        except Exception as e:
            logger.error(f"解析JSON文件时发生错误: {e}")
            raise ValueError(f"解析JSON文件时发生错误: {e}")