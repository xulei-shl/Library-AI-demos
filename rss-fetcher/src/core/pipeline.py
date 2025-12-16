"""主流程控制模块 - 支持三阶段解耦运行"""

import yaml
import os
import sys
import argparse
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dateutil import parser as date_parser
from src.utils.logger import get_logger
from .rss_fetcher import RSSFetcher
from .rsshub_fetcher import RSSHubFetcher
from .playwright_fetcher import PlaywrightSiteFetcher
from .article_summary_runner import ArticleSummaryRunner
from .article_analysis_runner import ArticleAnalysisRunner
from .storage import StorageManager
from .content_extractors import ExtractorFactory
from .score_statistics import ScoreStatistics
from .cross_analysis import CrossAnalysisManager
from .md_reader import MDReader

# Windows平台的输入超时处理
if sys.platform == 'win32':
    import msvcrt
    import time
else:
    import select

logger = get_logger(__name__)


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                               "config", "subject_bibliography.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}


def get_cross_analysis_config():
    """获取交叉分析配置"""
    config = load_config()
    cross_config = config.get("cross_analysis", {}) or {}
    return {
        "min_score": cross_config.get("min_score", cross_config.get("score_threshold", 90)),
        "batch_size": cross_config.get("batch_size", 10)
    }


def get_user_input_with_timeout(prompt: str, timeout: int = 10, default: str = "y") -> str:
    """
    获取用户输入，支持超时自动选择默认值
    
    Args:
        prompt: 提示信息
        timeout: 超时时间（秒）
        default: 默认值
        
    Returns:
        用户输入或默认值
    """
    print(f"\n{prompt}")
    print(f"(默认为 '{default}'，{timeout}秒内无输入将自动选择默认值)")
    print("请输入 (y/n): ", end="", flush=True)
    
    if sys.platform == 'win32':
        # Windows平台实现
        start_time = time.time()
        user_input = ""
        
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwche()
                if char in ('\r', '\n'):
                    print()  # 换行
                    break
                user_input += char
            
            if time.time() - start_time > timeout:
                print(f"\n超时，自动选择默认值: {default}")
                return default
            
            time.sleep(0.1)
        
        return user_input.strip().lower() if user_input.strip() else default
    else:
        # Unix/Linux平台实现
        import select
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        
        if rlist:
            user_input = sys.stdin.readline().strip().lower()
            return user_input if user_input else default
        else:
            print(f"\n超时，自动选择默认值: {default}")
            return default



class SubjectBibliographyPipeline:
    """主流程控制器 - 支持三阶段独立运行"""

    def __init__(self, config_path: str = "config/subject_bibliography.yaml"):
        self.config = self._load_config(config_path)
        
        # 初始化存储管理器 - 按月聚合版本
        output_conf = self.config.get("output", {})
        self.storage = StorageManager(
            output_dir=output_conf.get("base_dir", "runtime/outputs")
        )

    def _load_config(self, path: str) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(path):
            logger.error(f"配置文件未找到: {path}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def _extract_time_range(
        self, fetch_conf: Dict[str, Any]
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """解析抓取时间范围配置。"""
        if not fetch_conf:
            return None, None

        time_range_conf = fetch_conf.get("time_range") or {}
        start_time = self._parse_datetime(time_range_conf.get("start"))
        end_time = self._parse_datetime(time_range_conf.get("end"))

        if start_time and end_time and start_time > end_time:
            logger.warning("time_range.start 晚于 end，忽略该配置，回退到 hours_lookback。")
            return None, None

        return start_time, end_time

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """解析配置中的日期时间字符串。"""
        if not value or not isinstance(value, str):
            return None

        text = value.strip()
        if not text:
            return None

        try:
            # 去除时区信息，保持与抓取结果一致的本地时间
            parsed = date_parser.parse(text, fuzzy=True)
            return parsed.replace(tzinfo=None)
        except Exception:
            logger.warning(f"无法解析抓取时间配置: {value}")
            return None

    def run_stage_fetch(self) -> Optional[str]:
        """
        阶段1: RSS获取
        
        Returns:
            输出文件路径，失败返回 None
        """
        logger.info("=" * 60)
        logger.info("开始执行阶段1: RSS获取")
        logger.info("=" * 60)
        
        # 初始化抓取器
        user_agent = self.config.get("fetch_settings", {}).get("user_agent")
        fetcher = RSSFetcher(user_agent=user_agent)
        rsshub_fetcher = RSSHubFetcher(user_agent=user_agent)
        playwright_fetcher = PlaywrightSiteFetcher(user_agent=user_agent)
        
        # 获取配置
        feeds = self.config.get("rss_feeds", [])
        playwright_sites = self.config.get("playwright_sites", [])
        fetch_conf = self.config.get("fetch_settings", {})
        hours_lookback = fetch_conf.get("hours_lookback", 24)
        start_time, end_time = self._extract_time_range(fetch_conf)
        
        # 分离不同类型的源
        regular_feeds = []
        rsshub_feeds = []
        
        for feed in feeds:
            url = feed.get("url", "")
            if url.startswith("rsshub://"):
                rsshub_feeds.append(feed)
            else:
                regular_feeds.append(feed)
        
        logger.info(f"发现 {len(regular_feeds)} 个常规RSS源、{len(rsshub_feeds)} 个RSSHub源和 {len(playwright_sites)} 个Playwright网站")
        
        articles = []
        
        # 处理常规RSS源
        if regular_feeds:
            logger.info("开始抓取常规RSS源...")
            regular_articles = fetcher.fetch_recent_articles(
                regular_feeds,
                hours_lookback=hours_lookback,
                start_time=start_time,
                end_time=end_time,
            )
            articles.extend(regular_articles)
        
        # 处理RSSHub源
        if rsshub_feeds:
            logger.info("开始抓取RSSHub源...")
            for rsshub_feed in rsshub_feeds:
                rsshub_url = rsshub_feed.get("url")
                if rsshub_url:
                    logger.info(f"抓取RSSHub源: {rsshub_feed.get('name', rsshub_url)}")
                    try:
                        result = rsshub_fetcher.fetch_rsshub_feed(
                            rsshub_url=rsshub_url,
                            feed_config=rsshub_feed,
                            hours_lookback=hours_lookback,
                            start_time=start_time,
                            end_time=end_time,
                        )
                        
                        if result and result.get('articles'):
                            articles.extend(result['articles'])
                            logger.info(f"RSSHub源 {rsshub_url} 成功获取 {len(result['articles'])} 篇文章")
                        else:
                            logger.warning(f"RSSHub源 {rsshub_url} 未获取到文章")
                            
                    except Exception as e:
                        logger.error(f"抓取RSSHub源 {rsshub_url} 时出错: {e}")
        
        # 处理Playwright网站
        if playwright_sites:
            logger.info("开始抓取Playwright网站...")
            try:
                playwright_articles = playwright_fetcher.fetch_recent_articles(
                    playwright_sites,
                    hours_lookback=hours_lookback,
                    start_time=start_time,
                    end_time=end_time,
                )
                articles.extend(playwright_articles)
                logger.info(f"Playwright网站抓取完成，获取 {len(playwright_articles)} 篇文章")
            except Exception as e:
                logger.error(f"抓取Playwright网站时出错: {e}")
        
        if not articles:
            logger.info("未发现新文章，阶段1结束。")
            return None
        
        # 保存结果
        output_file = self.storage.save_fetch_results(articles)
        
        logger.info("=" * 60)
        logger.info(f"阶段1完成，输出文件: {output_file}")
        logger.info("=" * 60)
        
        return output_file

    def run_stage_extract(self, input_file: Optional[str] = None) -> Optional[str]:
        """
        阶段2: 全文解析
        
        Args:
            input_file: 输入文件路径，如果不指定则自动查找最新的 fetch 文件
            
        Returns:
            输出文件路径，失败返回 None
        """
        logger.info("=" * 60)
        logger.info("开始执行阶段2: 全文解析")
        logger.info("=" * 60)
        
        # 确定输入文件 - 智能检测策略
        if input_file is None:
            # 策略1: 查找最新修改的fetch文件
            logger.info("未指定输入文件，智能检测fetch文件...")
            input_file = self.storage.find_latest_stage_file("fetch")
            if input_file is None:
                logger.error("未找到任何阶段1的输出文件，请先运行阶段1")
                return None
            logger.info(f"自动选择最新文件: {input_file}")
        else:
            # 用户明确指定了输入文件
            if not os.path.exists(input_file):
                logger.error(f"指定的输入文件不存在: {input_file}")
                return None
            logger.info(f"使用用户指定的文件: {input_file}")
        
        logger.info(f"输入文件: {input_file}")
        
        # 加载数据
        articles = self.storage.load_stage_data("fetch", input_file)
        
        if not articles:
            logger.error("输入文件为空或加载失败")
            return None
        
        # 筛选需要重新提取的文章（full_text为空或提取失败的文章）
        articles_to_extract = []
        already_processed = 0
        
        for article in articles:
            full_text = article.get("full_text", "")
            extract_status = article.get("extract_status", "")
            
            # 处理NaN值：如果full_text为空字符串、NaN或None，或者提取失败，需要重新提取
            full_text_is_empty = (
                not full_text or 
                str(full_text).lower() == 'nan' or 
                str(full_text).lower() == 'none' or
                full_text is None
            )
            extract_failed = (
                extract_status == "failed" or 
                extract_status == "skipped" or
                str(extract_status).lower() == 'nan' or
                str(extract_status).lower() == 'none'
            )
            
            if full_text_is_empty or extract_failed:
                articles_to_extract.append(article)
            else:
                already_processed += 1
        
        total = len(articles)
        to_extract = len(articles_to_extract)
        logger.info(f"文章总数: {total}, 已处理: {already_processed}, 需要提取: {to_extract}")
        
        if to_extract == 0:
            logger.info("所有文章都已成功提取，跳过阶段2")
            return input_file
        
        # 提取全文
        logger.info(f"开始提取 {to_extract} 篇文章的全文...")
        
        for i, article in enumerate(articles_to_extract):
            source = article.get("source", "")
            title = article.get("title", "")
            
            logger.info(f"正在处理 ({i+1}/{to_extract}): [{source}] {title}")
            
            # 获取对应的提取器
            extractor = ExtractorFactory.get_extractor(source)
            
            if extractor is None:
                # 没有找到提取器，标记为跳过
                article["full_text"] = ""
                article["extract_status"] = "skipped"
                article["extract_error"] = f"未找到适合源 '{source}' 的提取器"
                logger.warning(f"未找到提取器: {source}")
            else:
                # 执行提取
                result = extractor.extract(article)
                article.update(result)
        
        # 保存结果
        output_file = self.storage.save_extract_results(articles, input_file)
        
        # 统计提取结果
        success_count = sum(1 for a in articles if a.get("extract_status") == "success")
        failed_count = sum(1 for a in articles if a.get("extract_status") == "failed")
        skipped_count = sum(1 for a in articles if a.get("extract_status") == "skipped")
        
        logger.info("=" * 60)
        logger.info(f"阶段2初次提取完成，输出文件: {output_file}")
        logger.info(f"提取统计: 成功={success_count}, 失败={failed_count}, 跳过={skipped_count}")
        logger.info("=" * 60)
        
        # ========== 兜底重试机制 ==========
        # 筛选提取失败的文章进行重试
        failed_articles = [article for article in articles if article.get("extract_status") == "failed"]
        
        if failed_articles:
            logger.info(f"开始兜底重试机制，对 {len(failed_articles)} 篇失败文章重新提取...")
            
            retry_success_count = 0
            retry_failed_count = 0
            
            for i, article in enumerate(failed_articles):
                source = article.get("source", "")
                title = article.get("title", "")
                original_error = article.get("extract_error", "")
                
                logger.info(f"兜底重试 ({i+1}/{len(failed_articles)}): [{source}] {title}")
                logger.debug(f"原始错误: {original_error}")
                
                # 获取对应的提取器
                extractor = ExtractorFactory.get_extractor(source)
                
                if extractor is None:
                    # 没有找到提取器，保持失败状态
                    article["extract_error"] = f"兜底重试失败: 未找到适合源 '{source}' 的提取器"
                    retry_failed_count += 1
                    logger.warning(f"兜底重试失败，未找到提取器: {source}")
                else:
                    # 清除之前的错误信息，重新执行提取
                    article["extract_error"] = ""
                    
                    try:
                        # 执行提取
                        result = extractor.extract(article)
                        article.update(result)
                        
                        # 检查重试结果
                        if article.get("extract_status") == "success":
                            retry_success_count += 1
                            logger.info(f"✓ 兜底重试成功: {title}")
                        else:
                            retry_failed_count += 1
                            # 在错误信息前添加"兜底重试失败"前缀
                            current_error = article.get("extract_error", "")
                            article["extract_error"] = f"兜底重试失败: {current_error}" if current_error else "兜底重试失败: 未知错误"
                            logger.warning(f"✗ 兜底重试失败: {title} - {article.get('extract_error', 'N/A')}")
                            
                    except Exception as e:
                        retry_failed_count += 1
                        article["extract_status"] = "failed"
                        article["extract_error"] = f"兜底重试异常: {str(e)}"
                        logger.error(f"✗ 兜底重试异常: {title} - {str(e)}")
            
            # 重新保存包含重试结果的数据
            output_file = self.storage.save_extract_results(articles, input_file)
            
            # 重新统计最终结果
            final_success_count = sum(1 for a in articles if a.get("extract_status") == "success")
            final_failed_count = sum(1 for a in articles if a.get("extract_status") == "failed")
            final_skipped_count = sum(1 for a in articles if a.get("extract_status") == "skipped")
            
            logger.info("=" * 60)
            logger.info("兜底重试完成")
            logger.info(f"重试统计: 成功={retry_success_count}, 失败={retry_failed_count}")
            logger.info(f"最终统计: 成功={final_success_count}, 失败={final_failed_count}, 跳过={final_skipped_count}")
            logger.info(f"最终输出文件: {output_file}")
            logger.info("=" * 60)
        else:
            logger.info("没有失败文章，跳过兜底重试机制")
        
        return output_file

    def run_stage_md_processing(self, md_directory: Optional[str] = None) -> Optional[str]:
        """
        MD文档处理阶段 - 读取本地MD文档并转换为标准格式

        Args:
            md_directory: MD文档目录路径，如果不指定则使用配置中的默认路径

        Returns:
            输出Excel文件路径，失败返回 None
        """
        logger.info("=" * 60)
        logger.info("开始执行MD文档处理阶段")
        logger.info("=" * 60)

        # 获取MD处理配置
        md_config = self.config.get("md_processing", {})

        # 确定MD文档目录
        if md_directory is None:
            # 使用配置中的默认路径
            md_directory = md_config.get("default_base_path", "data/md_documents")

        logger.info(f"MD文档目录: {md_directory}")

        # 验证目录存在
        if not os.path.exists(md_directory):
            logger.error(f"MD文档目录不存在: {md_directory}")
            return None

        if not os.path.isdir(md_directory):
            logger.error(f"指定路径不是目录: {md_directory}")
            return None

        try:
            # 初始化MDReader
            reader = MDReader(config=md_config)

            # 处理MD文档目录
            result = reader.process_directory(md_directory)

            if not result['success']:
                logger.error(f"MD文档处理失败: {result.get('error', '未知错误')}")
                return None

            articles = result['articles']
            logger.info(f"成功处理 {len(articles)} 个MD文档")

            # 保存到Excel
            excel_filename = result.get('excel_filename')
            output_file = self.storage.save_md_results(articles, excel_filename)

            if output_file:
                logger.info("=" * 60)
                logger.info(f"MD文档处理完成，输出文件: {output_file}")

                # 询问是否继续执行文章过滤
                try:
                    user_choice = get_user_input_with_timeout(
                        "是否继续执行文章过滤？",
                        timeout=10,
                        default="y"
                    )
                    if user_choice in ['y', 'yes', '是', '']:
                        logger.info("继续执行文章过滤...")
                        # 使用生成的Excel文件作为输入，执行过滤阶段
                        filter_output = self.run_stage_filter(output_file)
                        if filter_output:
                            logger.info(f"文章过滤完成，输出文件: {filter_output}")
                            output_file = filter_output
                    else:
                        logger.info("用户选择跳过文章过滤")
                except Exception as e:
                    logger.warning(f"用户交互失败，跳过过滤: {e}")

                logger.info("=" * 60)
                return output_file
            else:
                logger.error("保存MD文档结果失败")
                return None

        except Exception as e:
            logger.error(f"MD文档处理阶段失败: {e}", exc_info=True)
            return None

    def run_stage_filter(self, input_file: Optional[str] = None) -> Optional[str]:
        """
        阶段3: 文章过滤
        
        Args:
            input_file: 输入文件路径，如果不指定则自动查找最新的 extract 文件
            
        Returns:
            输出文件路径，失败返回 None
        """
        logger.info("=" * 60)
        logger.info("开始执行阶段3: 文章过滤")
        logger.info("说明: 本阶段将使用 article_filter 提示词对文章进行初筛")
        logger.info("=" * 60)
        
        # 确定输入文件 - 智能检测策略
        if input_file is None:
            # 策略1: 查找最新修改的extract文件
            logger.info("未指定输入文件，智能检测extract文件...")
            input_file = self.storage.find_latest_stage_file("extract")
            if input_file is None:
                logger.error("未找到任何阶段2的输出文件，请先运行阶段2")
                return None
            logger.info(f"自动选择最新文件: {input_file}")
        else:
            # 用户明确指定了输入文件
            if not os.path.exists(input_file):
                logger.error(f"指定的输入文件不存在: {input_file}")
                return None
            logger.info(f"使用用户指定的文件: {input_file}")
        
        logger.info(f"输入文件: {input_file}")
        
        # 加载数据
        articles = self.storage.load_stage_data("extract", input_file)
        
        if not articles:
            logger.error("输入文件为空或加载失败")
            return None
        
        # 过滤需要过滤的文章：提取成功且未处理过的文章
        unprocessed_articles = []
        already_processed = 0
        
        for article in articles:
            # 检查提取状态
            if article.get("extract_status") != "success":
                continue
                
            # 检查是否已经处理过过滤（优先检查filter_status）
            filter_status = article.get("filter_status", "")
            llm_raw_response = article.get("llm_raw_response", "")
            llm_status = article.get("llm_status", "")  # 保留用于向后兼容
            
            # 添加调试日志：记录当前状态字段值
            logger.debug(f"文章状态检查 - 标题: {article.get('title', 'N/A')[:50]}...")
            logger.debug(f"  filter_status: '{filter_status}'")
            logger.debug(f"  llm_status: '{llm_status}' (向后兼容)")
            logger.debug(f"  llm_raw_response存在: {bool(llm_raw_response)}")
            
            # 处理NaN值：将NaN视为空值
            filter_status_is_valid = (
                filter_status and
                str(filter_status).lower() not in ('nan', 'none', '')
            )
            llm_status_is_valid = (
                llm_status and
                str(llm_status).lower() not in ('nan', 'none', '')
            )
            llm_raw_response_is_valid = (
                llm_raw_response and
                str(llm_raw_response).lower() not in ('nan', 'none', '')
            )
            
            # 如果有有效的filter_status或llm_raw_response，认为已处理
            # 同时保留llm_status的检查以实现向后兼容
            if filter_status_is_valid or llm_status_is_valid or llm_raw_response_is_valid:
                already_processed += 1
                logger.debug(f"跳过已处理文章: {article.get('title', 'N/A')[:50]}... (filter_status: {filter_status}, llm_status: {llm_status})")
            else:
                unprocessed_articles.append(article)
        
        
        total = len(articles)
        to_filter = len(unprocessed_articles)
        logger.info(f"文章总数: {total}, 已处理: {already_processed}, 需要过滤: {to_filter}")
        
        # 初始化输出文件路径
        output_file = input_file
        
        if to_filter == 0:
            logger.info("所有文章都已成功过滤，跳过过滤步骤")
        else:
            # 初始化过滤器 (只执行过滤，不执行深度分析)
            from src.core.analysis.filter import ArticleFilter
            filter_agent = ArticleFilter()
            
            # 文章过滤 - 采用单条即时保存策略
            logger.info(f"开始过滤 {to_filter} 篇文章 (跳过 {len(articles) - to_filter} 篇提取失败或已处理的文章)...")
            logger.info("采用即时保存策略，每处理一条立即保存，确保不丢失数据")
            
            # 统计计数器
            saved_count = 0
            failed_count = 0
            
            for i, article in enumerate(unprocessed_articles):
                title = article.get("title", "无标题")
                logger.info(f"正在过滤 ({i+1}/{to_filter}): {title}")
                
                # 获取文章内容,优先使用 full_text,然后是 content
                full_text = article.get("full_text")
                content = article.get("content")
                
                # 检查是否有可用的内容进行过滤
                if not full_text and not content:
                    logger.info(f"文章 '{title}' 缺少 full_text 和 content 字段,跳过过滤")
                    processed_article = article.copy()
                    processed_article["filter_status"] = "跳过"
                    processed_article["llm_skip_reason"] = "缺少 full_text 和 content 字段"
                else:
                    # 优先使用 full_text,如果没有则使用 content
                    text_content = full_text or content or ""
                    
                    # 执行过滤
                    filter_result = filter_agent.filter(title, text_content)
                    
                    # 创建处理后的文章副本
                    processed_article = article.copy()
                    
                    # 保存过滤结果
                    processed_article["filter_pass"] = filter_result.get("pass", False)
                    processed_article["filter_reason"] = filter_result.get("reason", "")
                    filter_status_value = filter_result.get("status", "")
                    processed_article["filter_status"] = filter_status_value
                    
                    # 添加调试日志：记录状态字段设置
                    logger.debug(f"设置过滤状态 - 标题: {title}")
                    logger.debug(f"  filter_status: '{filter_status_value}'")
                    
                    # 如果过滤失败,标记状态
                    if filter_result.get("status") == "失败":
                        logger.warning(f"文章 '{title}' 过滤失败: {filter_result.get('error')}")
                        processed_article["filter_status"] = "失败"
                        processed_article["llm_error"] = filter_result.get("error", "")
                        logger.debug(f"  设置 filter_status: '失败'")
                    # 如果未通过过滤,标记为拒绝
                    elif not filter_result.get("pass", False):
                        logger.info(f"文章 '{title}' 未通过过滤,理由: {filter_result.get('reason')}")
                        processed_article["filter_status"] = "已拒绝"
                        # 设置默认值
                        processed_article["llm_score"] = 0
                        processed_article["llm_primary_dimension"] = ""
                        processed_article["llm_reason"] = filter_result.get("reason", "")
                        processed_article["llm_tags"] = "[]"
                        processed_article["llm_mentioned_books"] = "[]"
                        processed_article["llm_topic_focus"] = ""
                        processed_article["llm_thematic_essence"] = ""
                        logger.debug(f"  设置 filter_status: '已拒绝'")
                    else:
                        # 通过过滤，但暂不进行深度分析
                        logger.info(f"文章 '{title}' 通过过滤")
                        processed_article["filter_status"] = "成功"
                        processed_article["llm_score"] = 0  # 暂时设为0，等待后续分析
                        processed_article["llm_primary_dimension"] = ""
                        processed_article["llm_reason"] = ""
                        processed_article["llm_tags"] = "[]"
                        processed_article["llm_mentioned_books"] = "[]"
                        processed_article["llm_topic_focus"] = ""
                        processed_article["llm_thematic_essence"] = ""
                        logger.debug(f"  设置 filter_status: '成功'")
                
                # 立即保存当前文章的过滤结果
                try:
                    output_file = self.storage.save_analyze_results([processed_article], input_file)
                    saved_count += 1
                    logger.info(f"✓ 已保存 ({i+1}/{to_filter}): {processed_article.get('title', 'N/A')[:50]}... [状态: {processed_article.get('filter_status', 'N/A')}]")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"✗ 保存失败 ({i+1}/{to_filter}): {processed_article.get('title', 'N/A')[:50]}... 错误: {e}")
                    # 保存失败不中断流程，继续处理下一篇
            
            # 输出保存统计
            logger.info(f"即时保存统计: 成功={saved_count}, 失败={failed_count}")
        
        logger.info("=" * 60)
        logger.info(f"阶段3完成，输出文件: {output_file}")
        logger.info("=" * 60)
        
        return output_file

    def run_stage_summary(self, input_file: Optional[str] = None) -> Optional[str]:
        """
        阶段4: LLM总结

        Args:
            input_file: filter 阶段 Excel 路径，未提供则自动定位最新文件

        Returns:
            输出文件路径，失败返回 None
        """
        logger.info("=" * 60)
        logger.info("开始执行阶段4: 文章总结")
        logger.info("=" * 60)

        if input_file is None:
            logger.info("未指定输入文件，尝试定位最新 filter 文件...")
            input_file = self.storage.find_latest_stage_file("filter")
            if input_file is None:
                logger.error("未找到任何 filter 文件，请先完成前序流程")
                return None
            logger.info(f"自动选择文件: {input_file}")
        else:
            if not os.path.exists(input_file):
                logger.error(f"指定的输入文件不存在: {input_file}")
                return None
            logger.info(f"使用指定文件: {input_file}")

        runner = ArticleSummaryRunner(self.storage)
        output_file = runner.run(input_file)

        if output_file:
            logger.info(f"总结流程完成，输出文件: {output_file}")
        else:
            logger.error("总结流程执行失败")

        logger.info("=" * 60)
        return output_file

    def run_stage_analysis(self, input_file: Optional[str] = None) -> Optional[str]:
        """
        阶段5: 深度分析

        对总结成功的文章进行深度分析，提取评分、维度、母题等结构化信息。

        Args:
            input_file: summary 阶段 Excel 路径，未提供则自动定位最新文件

        Returns:
            输出文件路径，失败返回 None
        """
        logger.info("=" * 60)
        logger.info("开始执行阶段5: 深度分析")
        logger.info("=" * 60)

        if input_file is None:
            logger.info("未指定输入文件，尝试定位最新 summary 文件...")
            input_file = self.storage.find_latest_stage_file("summary")
            if input_file is None:
                logger.error("未找到任何 summary 文件，请先完成前序流程")
                return None
            logger.info(f"自动选择文件: {input_file}")
        else:
            if not os.path.exists(input_file):
                logger.error(f"指定的输入文件不存在: {input_file}")
                return None
            logger.info(f"使用指定文件: {input_file}")

        runner = ArticleAnalysisRunner(self.storage)
        output_file = runner.run(input_file)

        if output_file:
            logger.info(f"深度分析流程完成，输出文件: {output_file}")
            
            # 深度分析完成后，询问是否执行评分统计
            try:
                user_choice = get_user_input_with_timeout(
                    "是否对文章评分进行统计分析？",
                    timeout=10,
                    default="y"
                )
                if user_choice in ['y', 'yes', '是', '']:
                    # 执行评分统计
                    logger.info("开始执行评分统计分析...")
                    articles = self.storage.load_stage_data("analysis", output_file)
                    score_stats = ScoreStatistics()
                    report_path = score_stats.run_analysis(articles, output_file)
                    logger.info(f"评分统计报告已生成: {report_path}")
                else:
                    logger.info("用户跳过评分统计分析")
            except Exception as e:
                logger.warning(f"评分统计交互失败，跳过统计: {e}")
        else:
            logger.error("深度分析流程执行失败")

        logger.info("=" * 60)
        return output_file

    def run_all_stages(self):
        """执行完整流程: fetch -> extract -> filter -> summary -> analysis"""
        logger.info("开始执行完整流程")
        
        # 阶段1: RSS获取
        fetch_output = self.run_stage_fetch()
        if fetch_output is None:
            logger.error("阶段1失败，流程终止")
            return
        
        # 阶段2: 全文解析
        extract_output = self.run_stage_extract(fetch_output)
        if extract_output is None:
            logger.error("阶段2失败，流程终止")
            return
        
        # 阶段3: 文章过滤
        filter_output = self.run_stage_filter(extract_output)
        if filter_output is None:
            logger.error("阶段3失败，流程终止")
            return
        
        # 阶段4: 文章总结
        summary_output = self.run_stage_summary(filter_output)
        if summary_output is None:
            logger.error("阶段4失败，流程终止")
            return
        
        # 阶段5: 深度分析
        analysis_output = self.run_stage_analysis(summary_output)
        if analysis_output is None:
            logger.error("阶段5失败，流程终止")
            return
        
        logger.info("=" * 60)
        logger.info("完整流程执行完毕！")
        logger.info(f"最终结果文件: {analysis_output}")
        logger.info("=" * 60)

    async def run_stage_cross_analysis(
        self,
        input_file: Optional[str] = None,
        min_score: Optional[int] = None
    ) -> Optional[List[str]]:
        """
        阶段4: 文章交叉主题分析

        Args:
            input_file: 输入文件路径，如果不指定则自动查找最新的 analyze 文件
            min_score: 评分筛选阈值

        Returns:
            报告文件路径列表，失败返回 None
        """
        logger.info("=" * 60)
        logger.info("开始执行阶段4: 文章交叉主题分析")
        logger.info("=" * 60)

        # 确定输入文件
        if input_file is None:
            logger.info("未指定输入文件，智能检测analysis文件...")
            input_file = self.storage.find_latest_stage_file("analysis")
            if input_file is None:
                logger.error("未找到任何阶段5的输出文件，请先运行阶段5")
                return None
            logger.info(f"自动选择最新文件: {input_file}")
        else:
            if not os.path.exists(input_file):
                logger.error(f"指定的输入文件不存在: {input_file}")
                return None
            logger.info(f"使用用户指定的文件: {input_file}")

        logger.info(f"输入文件: {input_file}")

        # 若未提供外部阈值，则回退到配置
        config_threshold = self.config.get("cross_analysis", {}).get("min_score", 90)
        if min_score is None:
            min_score = config_threshold
        logger.info(f"评分筛选阈值: {min_score}")

        # 加载数据
        articles = self.storage.load_stage_data("analysis", input_file)

        if not articles:
            logger.error("输入文件为空或加载失败")
            return None

        # 筛选高质量文章
        high_quality_articles = [
            article for article in articles
            if article.get("llm_score", 0) >= min_score
            and article.get("llm_thematic_essence")
        ]

        logger.info(f"文章总数: {len(articles)}")
        logger.info(f"高质量文章数 (评分>={min_score}): {len(high_quality_articles)}")

        if len(high_quality_articles) < 3:
            logger.warning(f"高质量文章数量不足 ({len(high_quality_articles)} < 3)，建议降低评分阈值")
            # 但仍然继续分析

        # 初始化交叉分析器
        # 合并配置，确保CLI传入的阈值生效
        analyzer_config = self.config.copy()
        if "cross_analysis" not in analyzer_config:
            analyzer_config["cross_analysis"] = {}
        analyzer_config["cross_analysis"]["min_score"] = min_score
        analyzer_config["cross_analysis"].setdefault("batch_size", get_cross_analysis_config().get("batch_size", 10))
        
        manager = CrossAnalysisManager(config=analyzer_config)

        # 执行交叉分析
        logger.info("开始执行交叉主题分析...")
        report_paths = await manager.run(high_quality_articles)

        if not report_paths:
            logger.error("未能生成任何交叉分析报告")
            return None

        logger.info("=" * 60)
        logger.info("交叉分析完成，多份报告已生成:")
        for path in report_paths:
            logger.info(f"- {path}")
        logger.info("=" * 60)
        return report_paths


def run_pipeline(stage: str = "all", input_file: Optional[str] = None, min_score: Optional[int] = None, md_directory: Optional[str] = None):
    """
    运行流程

    Args:
        stage: 阶段名称 (fetch/extract/filter/summary/analysis/cross/md_processing/all)
        input_file: 输入文件路径(可选)
        min_score: 交叉分析的评分阈值(仅对cross有效)，如果不指定则使用配置文件中的默认值
        md_directory: MD文档目录路径(仅对md_processing有效)
    """
    # 如果未指定阈值，从配置文件读取
    if stage == "cross":
        cross_config = get_cross_analysis_config()
        if min_score is None:
            min_score = cross_config.get("min_score", cross_config.get("score_threshold", 90))
            logger.info(f"使用配置文件中的评分阈值: {min_score}")
    pipeline = SubjectBibliographyPipeline()

    if stage == "fetch":
        pipeline.run_stage_fetch()
    elif stage == "extract":
        pipeline.run_stage_extract(input_file)
    elif stage == "filter":
        pipeline.run_stage_filter(input_file)
    elif stage == "summary":
        pipeline.run_stage_summary(input_file)
    elif stage == "analysis":
        pipeline.run_stage_analysis(input_file)
    elif stage == "cross":
        # cross 是异步函数，需要特殊处理
        import asyncio
        report_paths = asyncio.run(pipeline.run_stage_cross_analysis(input_file, min_score))
        if report_paths:
            for path in report_paths:
                logger.info(f"交叉分析报告已生成: {path}")
    elif stage == "md_processing":
        pipeline.run_stage_md_processing(md_directory)
    elif stage == "all":
        pipeline.run_all_stages()
    else:
        logger.error(f"未知的阶段: {stage}，支持的阶段: fetch/extract/filter/summary/analysis/cross/md_processing/all")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="模块7: 主题书目每日追踪")
    parser.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["fetch", "extract", "filter", "summary", "analysis", "cross", "md_processing", "all"],
        help="运行阶段: fetch(RSS获取) / extract(全文解析) / filter(文章过滤) / summary(LLM总结) / analysis(深度分析) / cross(交叉主题分析) / md_processing(MD文档处理) / all(完整流程)"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="输入文件路径(用于阶段2、3、4、5、6)"
    )
    # 获取默认阈值
    default_threshold = get_cross_analysis_config().get("min_score", 90)

    parser.add_argument(
        "--min-score",
        type=int,
        default=None,
        help=f"交叉分析的评分筛选阈值(仅对cross有效，默认从配置文件读取，当前为{default_threshold})"
    )

    parser.add_argument(
        "--md-dir",
        type=str,
        default=None,
        help="MD文档目录路径(仅对md_processing有效)"
    )

    args = parser.parse_args()
    run_pipeline(args.stage, args.input, args.min_score, args.md_dir)
