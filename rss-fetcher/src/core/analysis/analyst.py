"""Agent 2: 深度分析师

负责对通过初筛的文章进行深度分析。
"""

import json
from typing import Dict, Any
from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)


class ArticleAnalyst:
    """文章深度分析师
    
    对通过初筛的文章进行深度分析,提取结构化的知识资产。
    """

    def __init__(self, task_name: str = "article_analysis"):
        """初始化 ArticleAnalyst
        
        Args:
            task_name: LLM 任务名称,对应 config/llm.yaml 中的配置
        """
        self.llm_client = UnifiedLLMClient()
        self.task_name = task_name

    def analyze(self, content: str) -> Dict[str, Any]:
        """对文章进行深度分析
        
        Args:
            content: 文章全文内容(会自动截断至 8000 字符)
        
        Returns:
            包含分析结果的字典:
            {
                "score": int,  # 评分 0-100
                "primary_dimension": str,  # 主要维度
                "reason": str,  # 评分理由
                "summary": str,  # 给用户看的摘要
                "thematic_essence": str,  # 给向量库看的母题本质
                "tags": list,  # 标签列表
                "mentioned_books": list,  # 提及的书籍
                "status": str,  # 处理状态: "成功", "失败"
                "error": str,  # 错误信息(如果有)
            }
        """
        # 截断处理,防止超出 Context Window
        if len(content) > 8000:
            content = content[:8000] + "\n...(内容过长已截断)"

        user_prompt = f"请深度分析以下文章:\n\n{content}"

        try:
            # 调用 LLM
            result = self.llm_client.call(self.task_name, user_prompt)
            
            # 解析返回结果
            if isinstance(result, str):
                try:
                    analysis_data = json.loads(result)
                except json.JSONDecodeError as e:
                    logger.error(f"分析结果 JSON 解析失败: {e}, 原始返回: {result[:200]}")
                    return {
                        "score": 0,
                        "primary_dimension": "",
                        "reason": "JSON解析失败",
                        "summary": "",
                        "thematic_essence": "",
                        "tags": [],
                        "mentioned_books": [],
                        "status": "失败",
                        "error": f"JSON解析错误: {str(e)}"
                    }
            else:
                analysis_data = result

            # 提取字段
            score = analysis_data.get("score", 0)
            primary_dimension = analysis_data.get("primary_dimension", "")
            reason = analysis_data.get("reason", "")
            summary = analysis_data.get("summary", "")
            thematic_essence = analysis_data.get("thematic_essence", "")
            tags = analysis_data.get("tags", [])
            mentioned_books = analysis_data.get("mentioned_books", [])

            logger.info(f"文章深度分析完成, 评分: {score}, 主要维度: {primary_dimension}")

            return {
                "score": score,
                "primary_dimension": primary_dimension,
                "reason": reason,
                "summary": summary,
                "thematic_essence": thematic_essence,
                "tags": tags,
                "mentioned_books": mentioned_books,
                "status": "成功",
                "error": None
            }

        except Exception as e:
            logger.error(f"深度分析文章失败: {e}")
            return {
                "score": 0,
                "primary_dimension": "",
                "reason": "LLM调用失败",
                "summary": "",
                "thematic_essence": "",
                "tags": [],
                "mentioned_books": [],
                "status": "失败",
                "error": str(e)
            }
