"""LLM 分析处理模块 - 双 Agent 架构

本模块实现了文章分析的双 Agent 架构:
- Agent 1 (Filter): 初筛守门员,过滤低价值内容
- Agent 2 (Analyst): 深度分析师,提取知识资产

ArticleProcessor 作为协调者(Orchestrator),编排两个 Agent 的工作流程。
"""

import json
from typing import Dict, Any
from src.utils.logger import get_logger
from src.core.analysis.filter import ArticleFilter
from src.core.analysis.analyst import ArticleAnalyst

logger = get_logger(__name__)


class ArticleProcessor:
    """文章分析协调者
    
    编排双 Agent 工作流程:
    1. 调用 ArticleFilter 进行初筛
    2. 如果通过初筛,调用 ArticleAnalyst 进行深度分析
    3. 合并结果并返回
    """

    def __init__(self):
        """初始化 ArticleProcessor"""
        self.filter_agent = ArticleFilter()
        self.analyst_agent = ArticleAnalyst()

    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用双 Agent 架构分析文章。

        Args:
            article: 文章数据字典,包含 title, full_text 或 content。

        Returns:
            包含分析结果的字典(合并了原始文章数据)。
        """
        title = article.get("title", "无标题")
        
        # 获取文章内容,优先使用 full_text,然后是 content
        full_text = article.get("full_text")
        content = article.get("content")
        
        # 检查是否有可用的内容进行分析
        if not full_text and not content:
            logger.info(f"文章 '{title}' 缺少 full_text 和 content 字段,跳过分析")
            processed_article = article.copy()
            processed_article["llm_status"] = "跳过"
            processed_article["llm_skip_reason"] = "缺少 full_text 和 content 字段"
            return processed_article
        
        # 优先使用 full_text,如果没有则使用 content
        text_content = full_text or content or ""
        
        # ========== 阶段 1: 初筛 (Agent 1: Filter) ==========
        logger.info(f"开始初筛文章: '{title}'")
        filter_result = self.filter_agent.filter(title, text_content)
        
        # 创建处理后的文章副本
        processed_article = article.copy()
        
        # 保存初筛结果
        processed_article["filter_pass"] = filter_result.get("pass", False)
        processed_article["filter_reason"] = filter_result.get("reason", "")
        processed_article["filter_status"] = filter_result.get("status", "")
        
        # 如果初筛失败,直接返回
        if filter_result.get("status") == "失败":
            logger.warning(f"文章 '{title}' 初筛失败: {filter_result.get('error')}")
            processed_article["llm_status"] = "初筛失败"
            processed_article["llm_error"] = filter_result.get("error", "")
            return processed_article
        
        # 如果未通过初筛,标记为拒绝
        if not filter_result.get("pass", False):
            logger.info(f"文章 '{title}' 未通过初筛,理由: {filter_result.get('reason')}")
            processed_article["llm_status"] = "已拒绝"
            # 设置默认值
            processed_article["llm_score"] = 0
            processed_article["llm_primary_dimension"] = ""
            processed_article["llm_summary"] = ""
            processed_article["llm_reason"] = filter_result.get("reason", "")
            processed_article["llm_tags"] = "[]"
            processed_article["llm_mentioned_books"] = "[]"
            processed_article["llm_thematic_essence"] = ""
            return processed_article
        
        # ========== 阶段 2: 深度分析 (Agent 2: Analyst) ==========
        logger.info(f"文章 '{title}' 通过初筛,开始深度分析")
        analysis_result = self.analyst_agent.analyze(text_content)
        
        # 保存深度分析结果
        if analysis_result.get("status") == "失败":
            logger.warning(f"文章 '{title}' 深度分析失败: {analysis_result.get('error')}")
            processed_article["llm_status"] = "分析失败"
            processed_article["llm_error"] = analysis_result.get("error", "")
            return processed_article
        
        # 成功完成分析
        processed_article["llm_status"] = "成功"
        processed_article["llm_score"] = self._safe_get_int(analysis_result, "score", 0)
        processed_article["llm_primary_dimension"] = self._safe_get_string(analysis_result, "primary_dimension", "")
        processed_article["llm_reason"] = self._safe_get_string(analysis_result, "reason", "")
        processed_article["llm_summary"] = self._safe_get_string(analysis_result, "summary", "")
        processed_article["llm_thematic_essence"] = self._safe_get_string(analysis_result, "thematic_essence", "")
        processed_article["llm_tags"] = json.dumps(
            self._safe_get_list(analysis_result, "tags", []), 
            ensure_ascii=False
        )
        processed_article["llm_mentioned_books"] = json.dumps(
            self._safe_get_list(analysis_result, "mentioned_books", []), 
            ensure_ascii=False
        )
        
        logger.info(f"文章 '{title}' 分析完成, 评分: {processed_article['llm_score']}")
        
        return processed_article

    # ========== 辅助方法 ==========
    
    def _safe_get_int(self, data: Dict[str, Any], key: str, default: int = 0) -> int:
        """安全地获取整数值"""
        value = data.get(key, default)
        try:
            if isinstance(value, str):
                return int(float(value))  # 先转float再转int,处理"85.0"这样的字符串
            return int(value)
        except (ValueError, TypeError):
            return default

    def _safe_get_string(self, data: Dict[str, Any], key: str, default: str = "") -> str:
        """安全地获取字符串值"""
        value = data.get(key, default)
        return str(value) if value is not None else default

    def _safe_get_list(self, data: Dict[str, Any], key: str, default: list = None) -> list:
        """安全地获取列表值"""
        if default is None:
            default = []
        value = data.get(key, default)
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            try:
                # 尝试解析JSON字符串
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            # 如果解析失败,尝试按逗号分割
            return [item.strip() for item in value.split(',') if item.strip()]
        else:
            return default
