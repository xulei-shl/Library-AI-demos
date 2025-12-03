"""主流程控制模块 - 支持三阶段解耦运行"""

import yaml
import os
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dateutil import parser as date_parser
from src.utils.logger import get_logger
from .rss_fetcher import RSSFetcher
from .article_analyzer import ArticleProcessor
from .storage import StorageManager
from .content_extractors import ExtractorFactory

logger = get_logger(__name__)


class SubjectBibliographyPipeline:
    """模块7 主流程控制器 - 支持三阶段独立运行"""

    def __init__(self, config_path: str = "config/subject_bibliography.yaml"):
        self.config = self._load_config(config_path)
        
        # 初始化存储管理器
        output_conf = self.config.get("output", {})
        self.storage = StorageManager(
            output_dir=output_conf.get("base_dir", "runtime/outputs/subject_bibliography")
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
        
        # 初始化 RSS 抓取器
        user_agent = self.config.get("fetch_settings", {}).get("user_agent")
        fetcher = RSSFetcher(user_agent=user_agent)
        
        # 获取配置
        feeds = self.config.get("rss_feeds", [])
        fetch_conf = self.config.get("fetch_settings", {})
        hours_lookback = fetch_conf.get("hours_lookback", 24)
        start_time, end_time = self._extract_time_range(fetch_conf)
        
        # 抓取文章
        articles = fetcher.fetch_recent_articles(
            feeds,
            hours_lookback=hours_lookback,
            start_time=start_time,
            end_time=end_time,
        )
        
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
        
        # 确定输入文件
        if input_file is None:
            input_file = self.storage.find_latest_stage_file("fetch")
            if input_file is None:
                logger.error("未找到阶段1的输出文件，请先运行阶段1")
                return None
        
        logger.info(f"输入文件: {input_file}")
        
        # 加载数据
        articles = self.storage.load_stage_data("fetch", input_file)
        
        if not articles:
            logger.error("输入文件为空或加载失败")
            return None
        
        # 提取全文
        total = len(articles)
        logger.info(f"开始提取 {total} 篇文章的全文...")
        
        for i, article in enumerate(articles):
            source = article.get("source", "")
            title = article.get("title", "")
            
            logger.info(f"正在处理 ({i+1}/{total}): [{source}] {title}")
            
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
        logger.info(f"阶段2完成，输出文件: {output_file}")
        logger.info(f"提取统计: 成功={success_count}, 失败={failed_count}, 跳过={skipped_count}")
        logger.info("=" * 60)
        
        return output_file

    def run_stage_analyze(self, input_file: Optional[str] = None) -> Optional[str]:
        """
        阶段3: LLM评估
        
        Args:
            input_file: 输入文件路径，如果不指定则自动查找最新的 extract 文件
            
        Returns:
            输出文件路径，失败返回 None
        """
        logger.info("=" * 60)
        logger.info("开始执行阶段3: LLM评估")
        logger.info("=" * 60)
        
        # 确定输入文件
        if input_file is None:
            input_file = self.storage.find_latest_stage_file("extract")
            if input_file is None:
                logger.error("未找到阶段2的输出文件，请先运行阶段2")
                return None
        
        logger.info(f"输入文件: {input_file}")
        
        # 加载数据
        articles = self.storage.load_stage_data("extract", input_file)
        
        if not articles:
            logger.error("输入文件为空或加载失败")
            return None
        
        # 只处理提取成功的文章
        articles_to_analyze = [a for a in articles if a.get("extract_status") == "success"]
        
        if not articles_to_analyze:
            logger.warning("没有提取成功的文章需要分析")
            return None
        
        # 初始化 LLM 处理器
        llm_task_name = self.config.get("llm_analysis", {}).get("task_name", "subject_bibliography_analysis")
        processor = ArticleProcessor(task_name=llm_task_name)
        
        # LLM 分析
        total = len(articles_to_analyze)
        logger.info(f"开始分析 {total} 篇文章 (跳过 {len(articles) - total} 篇提取失败的文章)...")
        
        for i, article in enumerate(articles_to_analyze):
            logger.info(f"正在分析 ({i+1}/{total}): {article.get('title')}")
            analyzed = processor.analyze_article(article)
            # 更新原文章数据
            article.update(analyzed)
        
        # 保存结果
        output_file = self.storage.save_analyze_results(articles, input_file)
        
        logger.info("=" * 60)
        logger.info(f"阶段3完成，输出文件: {output_file}")
        logger.info("=" * 60)
        
        return output_file

    def run_all_stages(self):
        """执行完整流程: 阶段1 -> 阶段2 -> 阶段3"""
        logger.info("开始执行完整流程 (三阶段)")
        
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
        
        # 阶段3: LLM评估
        analyze_output = self.run_stage_analyze(extract_output)
        if analyze_output is None:
            logger.error("阶段3失败，流程终止")
            return
        
        logger.info("=" * 60)
        logger.info("完整流程执行完毕！")
        logger.info(f"最终结果文件: {analyze_output}")
        logger.info("=" * 60)


def run_pipeline(stage: str = "all", input_file: Optional[str] = None):
    """
    运行流程
    
    Args:
        stage: 阶段名称 (fetch/extract/analyze/all)
        input_file: 输入文件路径(可选)
    """
    pipeline = SubjectBibliographyPipeline()
    
    if stage == "fetch":
        pipeline.run_stage_fetch()
    elif stage == "extract":
        pipeline.run_stage_extract(input_file)
    elif stage == "analyze":
        pipeline.run_stage_analyze(input_file)
    elif stage == "all":
        pipeline.run_all_stages()
    else:
        logger.error(f"未知的阶段: {stage}，支持的阶段: fetch/extract/analyze/all")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="模块7: 主题书目每日追踪")
    parser.add_argument(
        "--stage",
        type=str,
        default="all",
        choices=["fetch", "extract", "analyze", "all"],
        help="运行阶段: fetch(RSS获取) / extract(全文解析) / analyze(LLM评估) / all(完整流程)"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="输入文件路径(用于阶段2、3)"
    )
    
    args = parser.parse_args()
    run_pipeline(args.stage, args.input)
