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

    def _get_filepath(self, stage: str, articles: Optional[List[Dict]] = None) -> str:
        """
        生成阶段文件路径 - 按月聚合版本
        
        Args:
            stage: 阶段名称 (fetch/extract/analyze)
            articles: 文章列表，用于确定月份范围
            
        Returns:
            文件完整路径 (格式: YYYY-MM.xlsx)
        """
        if articles and len(articles) > 0:
            # 根据文章发布时间确定月份
            from dateutil import parser as date_parser
            month_str = None
            
            for article in articles:
                # 尝试从published_date获取日期
                published_date = article.get("published_date", "")
                if published_date:
                    try:
                        if isinstance(published_date, str):
                            dt = date_parser.parse(published_date, fuzzy=True)
                        else:
                            dt = published_date
                        month_str = dt.strftime("%Y-%m")
                        break
                    except Exception:
                        continue
            
            # 如果无法解析文章日期，使用当前时间
            if not month_str:
                month_str = datetime.now().strftime("%Y-%m")
        else:
            # 默认使用当前月份
            month_str = datetime.now().strftime("%Y-%m")
        
        filename = f"{month_str}.xlsx"
        return os.path.join(self.output_dir, filename)

    def _get_existing_data(self, filepath: str) -> List[Dict]:
        """
        读取现有Excel文件数据，用于去重
        
        Args:
            filepath: Excel文件路径
            
        Returns:
            现有文章列表，读取失败返回空列表
        """
        if not os.path.exists(filepath):
            return []
        
        try:
            df = pd.read_excel(filepath)
            existing_articles = df.to_dict("records")
            logger.info(f"读取现有数据: {filepath} (共 {len(existing_articles)} 条记录)")
            return existing_articles
        except Exception as e:
            logger.warning(f"读取现有文件失败，将创建新文件: {filepath}, 错误: {e}")
            return []

    def _is_duplicate(self, new_article: Dict, existing_articles: List[Dict]) -> bool:
        """
        判断新文章是否为重复数据
        
        Args:
            new_article: 新文章数据
            existing_articles: 现有文章列表
            
        Returns:
            True表示重复，False表示不重复
        """
        new_link = str(new_article.get("link", "") or "").strip()
        new_title = str(new_article.get("title", "") or "").strip()
        
        if not new_link:
            # 如果没有URL，使用title + published_date作为唯一标识
            new_published_date = str(new_article.get("published_date", "") or "")
            new_key = f"{new_title}_{new_published_date}"
            
            for existing in existing_articles:
                existing_key = f"{str(existing.get('title', '') or '').strip()}_{str(existing.get('published_date', '') or '')}"
                if new_key == existing_key:
                    return True
        else:
            # 优先使用URL判断
            for existing in existing_articles:
                existing_link = str(existing.get("link", "") or "").strip()
                if new_link and existing_link and new_link == existing_link:
                    return True
            
            # 如果URL为空或不同，使用title + published_date
            if not new_link:
                new_published_date = str(new_article.get("published_date", "") or "")
                new_key = f"{new_title}_{new_published_date}"
                
                for existing in existing_articles:
                    existing_key = f"{str(existing.get('title', '') or '').strip()}_{str(existing.get('published_date', '') or '')}"
                    if new_key == existing_key:
                        return True
        
        return False

    def save_fetch_results(self, articles: List[Dict]) -> Optional[str]:
        """
        保存阶段1: RSS获取结果 - 按月聚合版本（带重复检测）
        
        Args:
            articles: 文章列表，每篇包含 source, title, link, published_date, fetch_date, summary, content
            
        Returns:
            保存的文件路径，失败返回 None
        """
        if not articles:
            logger.info("没有数据需要保存。")
            return None

        # 根据文章发布时间确定月份并生成文件路径
        filepath = self._get_filepath("fetch", articles)
        
        # 添加文章日期列 (YYYY-MM-DD格式)
        from dateutil import parser as date_parser
        for article in articles:
            published_date = article.get("published_date", "")
            if published_date:
                try:
                    if isinstance(published_date, str):
                        dt = date_parser.parse(published_date, fuzzy=True)
                    else:
                        dt = published_date
                    article["article_date"] = dt.strftime("%Y-%m-%d")
                except Exception:
                    article["article_date"] = ""
            else:
                article["article_date"] = ""
        
        # 读取现有数据，进行去重
        existing_articles = self._get_existing_data(filepath)
        filtered_articles = []
        duplicate_count = 0
        
        for article in articles:
            if not self._is_duplicate(article, existing_articles + filtered_articles):
                filtered_articles.append(article)
            else:
                duplicate_count += 1
                logger.debug(f"跳过重复文章: {article.get('title', 'N/A')[:50]}...")
        
        if duplicate_count > 0:
            logger.info(f"检测到并跳过 {duplicate_count} 条重复数据")
        
        if not filtered_articles:
            logger.info("没有新数据需要保存。")
            return filepath
        
        # 合并现有数据和新数据
        all_articles = existing_articles + filtered_articles
        
        # 定义列顺序 (新增article_date列)
        columns = ["source", "title", "article_date", "link", "published_date", "fetch_date", "summary", "content"]
        
        df = pd.DataFrame(all_articles)
        
        # 确保所有列都存在
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        
        # 重新排列列
        df = df[columns]
        
        try:
            df.to_excel(filepath, index=False)
            logger.info(f"阶段1结果已保存: {filepath} (总记录: {len(all_articles)}, 新增: {len(filtered_articles)})")
            return filepath
        except Exception as e:
            logger.error(f"保存阶段1结果失败: {e}")
            return None

    def save_extract_results(self, articles: List[Dict], input_file: Optional[str] = None) -> Optional[str]:
        """
        保存阶段2: 全文解析结果 - 按月聚合版本
        
        Args:
            articles: 文章列表，在阶段1基础上新增 full_text, extract_status, extract_error
            input_file: 输入文件路径(可选，用于验证)
            
        Returns:
            保存的文件路径，失败返回 None
        """
        if not articles:
            logger.info("没有数据需要保存。")
            return None

        # 根据文章发布时间确定月份并生成文件路径
        filepath = self._get_filepath("extract", articles)
        
        # 确保所有文章都有article_date列
        from dateutil import parser as date_parser
        for article in articles:
            if "article_date" not in article or not article["article_date"]:
                published_date = article.get("published_date", "")
                if published_date:
                    try:
                        if isinstance(published_date, str):
                            dt = date_parser.parse(published_date, fuzzy=True)
                        else:
                            dt = published_date
                        article["article_date"] = dt.strftime("%Y-%m-%d")
                    except Exception:
                        article["article_date"] = ""
                else:
                    article["article_date"] = ""
        
        # 读取现有数据，准备合并
        existing_articles = self._get_existing_data(filepath)
        
        # 为现有文章补充提取结果，只更新需要的列
        all_articles = []
        updated_count = 0
        
        # 创建处理结果索引，优先使用link匹配
        processed_index = {}
        for article in articles:
            # 优先使用link作为索引键
            link = article.get("link", "").strip()
            if link:
                processed_index[link] = article
            else:
                # 如果没有link，使用title+published_date组合
                title = article.get("title", "").strip()
                date = article.get("published_date", "").strip()
                if title and date:
                    key = f"{title}_{date}"
                    processed_index[key] = article
        
        for existing_article in existing_articles:
            updated_article = existing_article.copy()  # 复制原文章
            
            # 尝试找到对应的处理结果
            processed_article = None
            
            # 优先使用link匹配
            link = existing_article.get("link", "").strip()
            if link and link in processed_index:
                processed_article = processed_index[link]
            else:
                # 回退到title+published_date匹配
                title = existing_article.get("title", "").strip()
                date = existing_article.get("published_date", "").strip()
                key = f"{title}_{date}"
                if key in processed_index:
                    processed_article = processed_index[key]
            
            if processed_article:
                # 只更新需要的字段
                updated_article["full_text"] = processed_article.get("full_text", "")
                updated_article["extract_status"] = processed_article.get("extract_status", "")
                updated_article["extract_error"] = processed_article.get("extract_error", "")
                
                # 如果提取器更新了title，也更新title字段
                if "title" in processed_article and processed_article["title"]:
                    updated_article["title"] = processed_article["title"]
                
                updated_count += 1
                
            all_articles.append(updated_article)
        
        # 定义列顺序 (新增article_date列)
        columns = [
            "source", "title", "article_date", "link", "published_date", "fetch_date", "summary", 
            "content", "full_text", "extract_status", "extract_error"
        ]
        
        df = pd.DataFrame(all_articles)
        
        # 确保所有列都存在
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        
        # 重新排列列
        df = df[columns]
        
        try:
            df.to_excel(filepath, index=False)
            logger.info(f"阶段2结果已保存: {filepath} (总记录: {len(all_articles)}, 更新: {updated_count})")
            return filepath
        except Exception as e:
            logger.error(f"保存阶段2结果失败: {e}")
            return None

    def save_analyze_results(self, articles: List[Dict], input_file: Optional[str] = None, 
                             skip_processed: bool = True) -> Optional[str]:
        """
        保存阶段3: LLM评估结果 - 按月聚合版本（支持过滤已处理数据）
        
        Args:
            articles: 文章列表，在阶段2基础上新增 llm_decision, llm_score, llm_reason, llm_summary, llm_tags, llm_keywords, llm_primary_dimension, llm_mentioned_books, llm_book_clues, llm_raw_response
            input_file: 输入文件路径(可选，用于验证）
            skip_processed: 是否跳过已处理的数据，避免重复调用LLM（默认True）
            
        Returns:
            保存的文件路径，失败返回 None
        """
        # 确定输出文件路径 - 优先使用input_file，备选使用articles
        if input_file and os.path.exists(input_file):
            # 使用输入文件路径生成输出文件路径
            dirname = os.path.dirname(input_file)
            basename = os.path.basename(input_file)
            # 替换文件名为分析阶段的文件名格式
            if input_file.endswith('.xlsx'):
                filepath = os.path.join(dirname, basename)
            else:
                filepath = input_file
        elif articles:
            # 根据文章发布时间确定月份并生成文件路径
            filepath = self._get_filepath("analyze", articles)
        else:
            # 使用当前时间生成默认文件路径
            filepath = self._get_filepath("analyze", [])
        
        if not articles:
            # 没有新数据，但仍然需要确保现有文件存在且格式正确
            logger.info("没有新数据需要保存，检查现有文件...")
            if os.path.exists(filepath):
                logger.info(f"文件已存在: {filepath}")
                return filepath
            else:
                logger.info("没有现有文件，创建空文件...")
                # 创建空的DataFrame保存到文件
                columns = [
                    "source", "title", "article_date", "published_date", "link", "fetch_date", "summary", "extract_status", "extract_error",
                    "content", "full_text", "llm_status", "llm_decision", "llm_score", "llm_reason", "llm_summary", "llm_tags", "llm_keywords", 
                    "llm_primary_dimension", "llm_mentioned_books", "llm_book_clues", "llm_raw_response"
                ]
                df = pd.DataFrame(columns=columns)
                try:
                    df.to_excel(filepath, index=False)
                    logger.info(f"空文件已创建: {filepath}")
                    return filepath
                except Exception as e:
                    logger.error(f"创建空文件失败: {e}")
                    return None
        
        # 确保所有文章都有article_date列
        from dateutil import parser as date_parser
        for article in articles:
            if "article_date" not in article or not article["article_date"]:
                published_date = article.get("published_date", "")
                if published_date:
                    try:
                        if isinstance(published_date, str):
                            dt = date_parser.parse(published_date, fuzzy=True)
                        else:
                            dt = published_date
                        article["article_date"] = dt.strftime("%Y-%m-%d")
                    except Exception:
                        article["article_date"] = ""
                else:
                    article["article_date"] = ""
        
        # 读取现有数据，准备合并
        existing_articles = self._get_existing_data(filepath)
        
        # 过滤可写回的LLM结果，避免重复调用LLM
        ready_articles = []
        pending_count = 0
        if skip_processed:
            for article in articles:
                llm_raw_response = str(article.get("llm_raw_response", "") or "").strip()
                llm_status = str(article.get("llm_status", "") or "").strip()

                if llm_raw_response or llm_status:
                    ready_articles.append(article)
                else:
                    pending_count += 1
                    logger.debug(f"跳过尚未LLM处理的文章: {article.get('title', 'N/A')[:50]}...")

            logger.info(
                f"过滤结果: 总文章{len(articles)}篇，具备LLM结果{len(ready_articles)}篇，待处理{pending_count}篇"
            )
        else:
            logger.info("跳过过滤逻辑，处理所有文章")
            ready_articles = articles

        # 为现有文章补充分析结果，保留已成功分析的文章
        all_articles = []
        updated_count = 0
        
        # 创建已处理文章的映射，便于查找
        processed_articles_map = {}
        for article in ready_articles:
            # 优先使用link作为键
            link = article.get("link", "").strip()
            title = article.get("title", "").strip()
            
            if link:
                processed_articles_map[link] = article
            else:
                # 如果没有link，使用title+published_date组合
                published_date = article.get("published_date", "").strip()
                key = f"{title}_{published_date}"
                processed_articles_map[key] = article
        
        for existing_article in existing_articles:
            # 尝试找到对应的已处理文章
            processed_article = None
            
            # 优先使用link匹配
            link = existing_article.get("link", "").strip()
            if link and link in processed_articles_map:
                processed_article = processed_articles_map[link]
            else:
                # 回退到title+published_date匹配
                title = existing_article.get("title", "").strip()
                published_date = existing_article.get("published_date", "").strip()
                key = f"{title}_{published_date}"
                if key in processed_articles_map:
                    processed_article = processed_articles_map[key]
            
            if processed_article:
                # 使用已处理的数据更新现有文章
                all_articles.append(processed_article)
                updated_count += 1
                logger.debug(f"更新文章: {processed_article.get('title', 'N/A')[:50]}... (状态: {processed_article.get('llm_status', 'N/A')})")
            else:
                # 保留原有数据（包括已经处理的和不需要处理的）
                all_articles.append(existing_article)
        
        # 确保所有文章都有llm_status字段（向后兼容）
        for article in all_articles:
            if "llm_status" not in article:
                article["llm_status"] = ""
        
        # 定义列顺序 (把重要信息放前面，新增llm_status列)
        columns = [
            "source", "title", "article_date", "published_date", "link", "fetch_date", "summary", "extract_status", "extract_error",
            "content", "full_text", 
            "llm_status", "llm_decision", "llm_score", "llm_reason", "llm_summary", "llm_tags", "llm_keywords", 
            "llm_primary_dimension", "llm_mentioned_books", "llm_book_clues", "llm_raw_response"
        ]
        
        df = pd.DataFrame(all_articles)
        
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
            logger.info(f"阶段3结果已保存: {filepath} (总记录: {len(all_articles)}, 更新: {updated_count})")
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
        查找最新的阶段文件 - 按月聚合版本
        
        Args:
            stage: 阶段名称 (fetch/extract/analyze)
            
        Returns:
            最新文件路径，如果没有找到返回 None
        """
        if not os.path.exists(self.output_dir):
            return None
        
        # 按月聚合版本的文件格式: YYYY-MM.xlsx
        files = []
        
        for filename in os.listdir(self.output_dir):
            if filename.endswith(".xlsx"):
                # 验证文件名格式是否为YYYY-MM.xlsx
                if len(filename) == 12 and filename[:7].count("-") == 1:
                    try:
                        year_month = filename[:7]
                        year, month = map(int, year_month.split("-"))
                        # 构建完整文件路径
                        filepath = os.path.join(self.output_dir, filename)
                        files.append((filepath, os.path.getmtime(filepath), year, month))
                    except (ValueError, IndexError):
                        # 跳过不符合格式的文件
                        continue
        
        if not files:
            logger.warning(f"未找到按月聚合格式的Excel文件")
            return None
        
        # 按修改时间排序，返回最新的
        files.sort(key=lambda x: x[1], reverse=True)
        latest_file = files[0][0]
        logger.info(f"找到最新的按月聚合文件: {latest_file}")
        return latest_file

    def append_new_data(self, stage: str, new_articles: List[Dict]) -> Optional[str]:
        """
        追加新数据到现有的按月聚合Excel文件（推荐用法）
        
        Args:
            stage: 阶段名称 (fetch/extract/analyze)
            new_articles: 新文章列表
            
        Returns:
            保存的文件路径，失败返回 None
        """
        if not new_articles:
            logger.info("没有新数据需要追加。")
            return None

        # 根据文章发布时间确定月份并生成文件路径
        filepath = self._get_filepath(stage, new_articles)
        
        # 读取现有数据
        existing_articles = self._get_existing_data(filepath)
        
        # 对新数据进行去重
        filtered_articles = []
        duplicate_count = 0
        
        for article in new_articles:
            if not self._is_duplicate(article, existing_articles + filtered_articles):
                filtered_articles.append(article)
            else:
                duplicate_count += 1
                logger.debug(f"跳过重复文章: {article.get('title', 'N/A')[:50]}...")
        
        if duplicate_count > 0:
            logger.info(f"检测到并跳过 {duplicate_count} 条重复数据")
        
        if not filtered_articles:
            logger.info("没有新数据需要追加。")
            return filepath
        
        # 合并现有数据和新数据
        all_articles = existing_articles + filtered_articles
        
        # 根据不同阶段确定列顺序
        if stage == "fetch":
            columns = ["source", "title", "article_date", "link", "published_date", "fetch_date", "summary", "content"]
        elif stage == "extract":
            columns = [
                "source", "title", "article_date", "link", "published_date", "fetch_date", "summary", 
                "content", "full_text", "extract_status", "extract_error"
            ]
        elif stage == "analyze":
            columns = [
                "source", "title", "article_date", "published_date", 
                "llm_status", "llm_decision", "llm_score", "llm_reason", "llm_summary", "llm_tags", "llm_keywords", 
                "llm_primary_dimension", "llm_mentioned_books", "llm_book_clues", "llm_raw_response",
                "link", "fetch_date", "summary", "extract_status", "extract_error",
                "content", "full_text"
            ]
        else:
            columns = list(set().union(*(article.keys() for article in all_articles)))
        
        # 确保所有列都存在
        df = pd.DataFrame(all_articles)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        
        # 重新排列列
        existing_cols = [c for c in columns if c in df.columns]
        remaining_cols = [c for c in df.columns if c not in existing_cols]
        df = df[existing_cols + remaining_cols]
        
        try:
            df.to_excel(filepath, index=False)
            logger.info(f"{stage}阶段数据已追加保存: {filepath} (总记录: {len(all_articles)}, 新增: {len(filtered_articles)})")
            return filepath
        except Exception as e:
            logger.error(f"追加保存{stage}阶段数据失败: {e}")
            return None
