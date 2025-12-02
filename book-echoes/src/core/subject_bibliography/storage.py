"""数据存储模块"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StorageManager:
    """负责将各阶段结果保存到 Excel 文件"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
                logger.info(f"创建输出目录: {self.output_dir}")
            except Exception as e:
                logger.error(f"创建输出目录失败: {self.output_dir}, {e}")

    def _get_filepath(self, stage: str) -> str:
        """
        生成阶段文件路径
        
        Args:
            stage: 阶段名称 (fetch/extract/analyze)
            
        Returns:
            文件完整路径
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{stage}.xlsx"
        return os.path.join(self.output_dir, filename)

    def save_fetch_results(self, articles: List[Dict]) -> Optional[str]:
        """
        保存阶段1: RSS获取结果
        
        Args:
            articles: 文章列表，每篇包含 source, title, link, published_date, fetch_date, summary, content
            
        Returns:
            保存的文件路径，失败返回 None
        """
        if not articles:
            logger.info("没有数据需要保存。")
            return None

        filepath = self._get_filepath("fetch")
        
        # 定义列顺序
        columns = ["source", "title", "link", "published_date", "fetch_date", "summary", "content"]
        
        df = pd.DataFrame(articles)
        
        # 确保所有列都存在
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        
        # 重新排列列
        df = df[columns]
        
        try:
            df.to_excel(filepath, index=False)
            logger.info(f"阶段1结果已保存: {filepath} (共 {len(df)} 条记录)")
            return filepath
        except Exception as e:
            logger.error(f"保存阶段1结果失败: {e}")
            return None

    def save_extract_results(self, articles: List[Dict], input_file: Optional[str] = None) -> Optional[str]:
        """
        保存阶段2: 全文解析结果
        
        Args:
            articles: 文章列表，在阶段1基础上新增 full_text, extract_status, extract_error
            input_file: 输入文件路径(可选，用于验证)
            
        Returns:
            保存的文件路径，失败返回 None
        """
        if not articles:
            logger.info("没有数据需要保存。")
            return None

        filepath = self._get_filepath("extract")
        
        # 定义列顺序
        columns = [
            "source", "title", "link", "published_date", "fetch_date", "summary", 
            "content", "full_text", "extract_status", "extract_error"
        ]
        
        df = pd.DataFrame(articles)
        
        # 确保所有列都存在
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        
        # 重新排列列
        df = df[columns]
        
        try:
            df.to_excel(filepath, index=False)
            logger.info(f"阶段2结果已保存: {filepath} (共 {len(df)} 条记录)")
            return filepath
        except Exception as e:
            logger.error(f"保存阶段2结果失败: {e}")
            return None

    def save_analyze_results(self, articles: List[Dict], input_file: Optional[str] = None) -> Optional[str]:
        """
        保存阶段3: LLM评估结果
        
        Args:
            articles: 文章列表，在阶段2基础上新增 llm_score, llm_tags, llm_keywords, llm_summary, llm_logic, llm_raw_response
            input_file: 输入文件路径(可选，用于验证)
            
        Returns:
            保存的文件路径，失败返回 None
        """
        if not articles:
            logger.info("没有数据需要保存。")
            return None

        filepath = self._get_filepath("analyze")
        
        # 定义列顺序 (把重要信息放前面，长文本放后面)
        columns = [
            "source", "title", "published_date", "llm_score", 
            "llm_summary", "llm_logic", "llm_tags", "llm_keywords",
            "link", "fetch_date", "summary", "extract_status", "extract_error",
            "content", "full_text", "llm_raw_response"
        ]
        
        df = pd.DataFrame(articles)
        
        # 确保所有列都存在
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        
        # 重新排列列
        existing_cols = [c for c in columns if c in df.columns]
        remaining_cols = [c for c in df.columns if c not in existing_cols]
        df = df[existing_cols + remaining_cols]
        
        try:
            df.to_excel(filepath, index=False)
            logger.info(f"阶段3结果已保存: {filepath} (共 {len(df)} 条记录)")
            return filepath
        except Exception as e:
            logger.error(f"保存阶段3结果失败: {e}")
            return None

    def load_stage_data(self, stage: str, filepath: Optional[str] = None) -> List[Dict]:
        """
        加载指定阶段的数据
        
        Args:
            stage: 阶段名称 (fetch/extract/analyze)
            filepath: 指定文件路径(可选)，如果不指定则使用默认路径
            
        Returns:
            文章列表
        """
        if filepath is None:
            filepath = self._get_filepath(stage)
        
        if not os.path.exists(filepath):
            logger.error(f"文件不存在: {filepath}")
            return []
        
        try:
            df = pd.read_excel(filepath)
            articles = df.to_dict("records")
            logger.info(f"已加载 {stage} 阶段数据: {filepath} (共 {len(articles)} 条记录)")
            return articles
        except Exception as e:
            logger.error(f"加载文件失败: {filepath}, 错误: {e}")
            return []

    def find_latest_stage_file(self, stage: str) -> Optional[str]:
        """
        查找最新的阶段文件
        
        Args:
            stage: 阶段名称 (fetch/extract/analyze)
            
        Returns:
            最新文件路径，如果没有找到返回 None
        """
        if not os.path.exists(self.output_dir):
            return None
        
        pattern = f"*_{stage}.xlsx"
        files = []
        
        for filename in os.listdir(self.output_dir):
            if filename.endswith(f"_{stage}.xlsx"):
                filepath = os.path.join(self.output_dir, filename)
                files.append((filepath, os.path.getmtime(filepath)))
        
        if not files:
            return None
        
        # 按修改时间排序，返回最新的
        files.sort(key=lambda x: x[1], reverse=True)
        latest_file = files[0][0]
        logger.info(f"找到最新的 {stage} 阶段文件: {latest_file}")
        return latest_file
