"""LLM 分析处理模块"""

import json
from typing import Dict, Any, Optional
from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)

class ArticleProcessor:
    """负责调用 LLM 对文章进行分析。"""

    def __init__(self, task_name: str = "subject_bibliography_analysis"):
        self.llm_client = UnifiedLLMClient()
        self.task_name = task_name

    def analyze_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 LLM 分析文章。

        Args:
            article: 文章数据字典，包含 title, source, published_date, content/summary。

        Returns:
            包含 LLM 分析结果的字典（合并了原始文章数据）。
        """
        title = article.get("title", "无标题")
        source = article.get("source", "未知来源")
        pub_date = article.get("published_date", "未知时间")
        
        # 优先使用 content，如果没有则使用 summary
        content = article.get("content") or article.get("summary", "")
        
        # 简单的截断处理，防止超出 Context Window
        # 假设 1 token ~= 1.5 chars (中文), 4 chars (English)
        # 保守起见，截取前 8000 字符
        if len(content) > 8000:
            content = content[:8000] + "\n...(内容过长已截断)"

        user_prompt = (
            f"请分析以下文章：\n\n"
            f"标题：{title}\n"
            f"来源：{source}\n"
            f"发布时间：{pub_date}\n\n"
            f"内容：\n{content}"
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

        # 合并结果
        processed_article = article.copy()
        processed_article.update({
            "llm_score": analysis_data.get("score", 0),
            "llm_tags": json.dumps(analysis_data.get("tags", []), ensure_ascii=False),
            "llm_keywords": json.dumps(analysis_data.get("keywords", []), ensure_ascii=False),
            "llm_summary": analysis_data.get("summary", ""),
            "llm_logic": analysis_data.get("logic", ""),
            "llm_raw_response": json.dumps(analysis_data, ensure_ascii=False) # 备份原始响应
        })

        return processed_article
