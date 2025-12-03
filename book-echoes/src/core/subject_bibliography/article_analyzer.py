"""LLM 分析处理模块"""

import json
from typing import Dict, Any, Optional
from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)

class ArticleProcessor:
    """负责调用 LLM 对文章进行初评分析。"""

    def __init__(self, task_name: str = "network_article_initial_review"):
        self.llm_client = UnifiedLLMClient()
        self.task_name = task_name

    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 分析文章。

        Args:
            article: 文章数据字典，包含 title, full_text 或 content。

        Returns:
            包含 LLM 分析结果的字典（合并了原始文章数据）。
        """
        title = article.get("title", "无标题")
        source = article.get("source", "未知来源")
        pub_date = article.get("published_date", "未知时间")
        
        # 优先使用 full_text，如果没有则使用 content
        full_text = article.get("full_text") or article.get("content", "")
        
        # 简单的截断处理，防止超出 Context Window
        # 假设 1 token ~= 1.5 chars (中文), 4 chars (English)
        # 保守起见，截取前 8000 字符
        if len(full_text) > 8000:
            full_text = full_text[:8000] + "\n...(内容过长已截断)"

        user_prompt = (
            f"请分析以下文章：\n\n"
            f"标题：{title}\n"
            f"来源：{source}\n"
            f"发布时间：{pub_date}\n\n"
            f"内容：\n{full_text}"
        )

        try:
            # 调用 LLM
            # UnifiedLLMClient 会自动处理 System Prompt (从 config 加载)
            # 并应用 JSON Repair
            result = self.llm_client.call(self.task_name, user_prompt)
            
            # result 应该已经是解析好的 dict (因为配置了 json_repair output_format: json)
            # 但为了保险，检查一下类型
            if isinstance(result, str):
                try:
                    analysis_data = json.loads(result)
                except json.JSONDecodeError:
                    logger.error(f"LLM 返回的不是有效 JSON: {result[:100]}...")
                    analysis_data = {}
            else:
                analysis_data = result

        except Exception as e:
            logger.error(f"分析文章 '{title}' 失败: {e}")
            analysis_data = {
                "error": str(e)
            }

        # 保存原始响应
        raw_response = json.dumps(analysis_data, ensure_ascii=False)
        
        # 合并结果 - 先保留原始数据
        processed_article = article.copy()
        processed_article["llm_raw_response"] = raw_response
        
        # 安全地解析各个字段，如果解析失败则跳过
        try:
            processed_article["llm_decision"] = self._safe_get_boolean(analysis_data, "decision")
        except Exception as e:
            logger.warning(f"解析 decision 字段失败: {e}")
        
        try:
            processed_article["llm_score"] = self._safe_get_int(analysis_data, "score", default=0)
        except Exception as e:
            logger.warning(f"解析 score 字段失败: {e}")
            processed_article["llm_score"] = 0
            
        try:
            processed_article["llm_primary_dimension"] = self._safe_get_string(analysis_data, "primary_dimension", default="")
        except Exception as e:
            logger.warning(f"解析 primary_dimension 字段失败: {e}")
            
        try:
            processed_article["llm_summary"] = self._safe_get_string(analysis_data, "summary", default="")
        except Exception as e:
            logger.warning(f"解析 summary 字段失败: {e}")
            
        try:
            processed_article["llm_reason"] = self._safe_get_string(analysis_data, "reason", default="")
        except Exception as e:
            logger.warning(f"解析 reason 字段失败: {e}")
            
        try:
            processed_article["llm_tags"] = json.dumps(self._safe_get_list(analysis_data, "tags", []), ensure_ascii=False)
        except Exception as e:
            logger.warning(f"解析 tags 字段失败: {e}")
            processed_article["llm_tags"] = "[]"
            
        try:
            processed_article["llm_keywords"] = json.dumps(self._safe_get_list(analysis_data, "keywords", []), ensure_ascii=False)
        except Exception as e:
            logger.warning(f"解析 keywords 字段失败: {e}")
            processed_article["llm_keywords"] = "[]"
            
        try:
            processed_article["llm_mentioned_books"] = json.dumps(self._safe_get_list(analysis_data, "mentioned_books", []), ensure_ascii=False)
        except Exception as e:
            logger.warning(f"解析 mentioned_books 字段失败: {e}")
            processed_article["llm_mentioned_books"] = "[]"
            
        try:
            processed_article["llm_book_clues"] = json.dumps(self._safe_get_list(analysis_data, "book_clues", []), ensure_ascii=False)
        except Exception as e:
            logger.warning(f"解析 book_clues 字段失败: {e}")
            processed_article["llm_book_clues"] = "[]"

        return processed_article

    def _safe_get_boolean(self, data: Dict[str, Any], key: str, default: bool = False) -> bool:
        """安全地获取布尔值"""
        value = data.get(key, default)
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(value, int):
            return bool(value)
        else:
            return default

    def _safe_get_int(self, data: Dict[str, Any], key: str, default: int = 0) -> int:
        """安全地获取整数值"""
        value = data.get(key, default)
        try:
            if isinstance(value, str):
                return int(float(value))  # 先转float再转int，处理"85.0"这样的字符串
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
            # 如果解析失败，尝试按逗号分割
            return [item.strip() for item in value.split(',') if item.strip()]
        else:
            return default
