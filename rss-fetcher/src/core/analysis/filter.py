"""Agent 1: 文章初筛守门员

负责对文章进行初步筛选,过滤低价值内容。
"""

import json
from typing import Dict, Any
from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)


class ArticleFilter:
    """文章初筛守门员
    
    使用 LLM 对文章进行初步筛选,判断是否值得进行深度分析。
    """

    def __init__(self, task_name: str = "article_filter"):
        """初始化 ArticleFilter
        
        Args:
            task_name: LLM 任务名称,对应 config/llm.yaml 中的配置
        """
        self.llm_client = UnifiedLLMClient()
        self.task_name = task_name

    def filter(self, title: str, content: str) -> Dict[str, Any]:
        """对文章进行初筛
        
        Args:
            title: 文章标题
            content: 文章内容(会自动截取前 1000 字符)
        
        Returns:
            包含初筛结果的字典:
            {
                "pass": bool,  # 是否通过初筛
                "reason": str,  # 拒绝或放行的理由
                "status": str,  # 处理状态: "成功", "失败"
                "error": str,  # 错误信息(如果有)
            }
        """
        # 构造输入内容,只使用标题和前 1000 字符
        preview_content = content[:1000] if len(content) > 1000 else content
        
        user_prompt = (
            f"标题: {title}\n\n"
            f"内容预览:\n{preview_content}"
        )

        try:
            # 调用 LLM
            result = self.llm_client.call(self.task_name, user_prompt)
            
            # 解析返回结果
            if isinstance(result, str):
                try:
                    filter_data = json.loads(result)
                except json.JSONDecodeError as e:
                    logger.error(f"初筛结果 JSON 解析失败: {e}, 原始返回: {result[:200]}")
                    return {
                        "pass": False,
                        "reason": "JSON解析失败",
                        "status": "失败",
                        "error": f"JSON解析错误: {str(e)}"
                    }
            else:
                filter_data = result

            # 提取字段
            pass_filter = filter_data.get("pass", False)
            reason = filter_data.get("reason", "")

            logger.info(f"文章 '{title}' 初筛结果: {'通过' if pass_filter else '拒绝'}, 理由: {reason}")

            return {
                "pass": pass_filter,
                "reason": reason,
                "status": "成功",
                "error": None
            }

        except Exception as e:
            logger.error(f"初筛文章 '{title}' 失败: {e}")
            return {
                "pass": False,
                "reason": "LLM调用失败",
                "status": "失败",
                "error": str(e)
            }
