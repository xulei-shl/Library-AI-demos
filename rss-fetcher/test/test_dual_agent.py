"""测试双 Agent 架构重构

这个脚本用于验证重构后的双 Agent 架构是否正常工作。
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.article_analyzer import ArticleProcessor
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_article_processor():
    """测试 ArticleProcessor 的双 Agent 架构"""
    
    # 创建测试文章
    test_article = {
        "title": "测试文章:人工智能的哲学思考",
        "content": """
        这是一篇关于人工智能哲学思考的文章。
        
        人工智能的发展引发了许多深刻的哲学问题。我们需要思考:
        什么是智能?什么是意识?机器能否真正理解世界?
        
        这些问题不仅关乎技术,更关乎人类对自身的理解。
        通过探讨这些问题,我们可以更好地理解人类智能的本质,
        以及人工智能可能带来的社会影响。
        
        本文参考了《人工智能哲学》一书,作者玛格丽特·博登。
        """,
        "source": "测试来源",
        "published_date": "2025-12-05",
        "link": "https://example.com/test-article"
    }
    
    # 创建处理器
    processor = ArticleProcessor()
    
    # 分析文章
    logger.info("=" * 60)
    logger.info("开始测试双 Agent 架构")
    logger.info("=" * 60)
    
    result = processor.analyze_article(test_article)
    
    # 打印结果
    logger.info("\n" + "=" * 60)
    logger.info("分析结果:")
    logger.info("=" * 60)
    logger.info(f"标题: {result.get('title')}")
    logger.info(f"\n--- 初筛结果 (Agent 1: Filter) ---")
    logger.info(f"是否通过: {result.get('filter_pass')}")
    logger.info(f"初筛理由: {result.get('filter_reason')}")
    logger.info(f"初筛状态: {result.get('filter_status')}")
    
    if result.get('filter_pass'):
        logger.info(f"\n--- 深度分析结果 (Agent 2: Analyst) ---")
        logger.info(f"LLM状态: {result.get('llm_status')}")
        logger.info(f"评分: {result.get('llm_score')}")
        logger.info(f"主要维度: {result.get('llm_primary_dimension')}")
        logger.info(f"评分理由: {result.get('llm_reason')}")
        logger.info(f"摘要: {result.get('llm_summary')}")
        logger.info(f"母题本质: {result.get('llm_thematic_essence')}")
        logger.info(f"标签: {result.get('llm_tags')}")
        logger.info(f"提及书籍: {result.get('llm_mentioned_books')}")
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)
    
    return result


if __name__ == "__main__":
    test_article_processor()
