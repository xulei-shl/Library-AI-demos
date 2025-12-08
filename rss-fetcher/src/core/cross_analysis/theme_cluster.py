"""主题聚类器模块

负责识别多篇文章间的共同主题
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)


class ThemeCluster:
    """主题聚类器

    识别多篇文章之间的共同主题，提取主要母题和候选主题列表
    """

    def __init__(self, task_name: str = "article_cross_analysis"):
        """初始化主题聚类器

        Args:
            task_name: LLM 任务名称，对应 config/llm.yaml 中的配置
        """
        self.llm_client = UnifiedLLMClient()
        self.task_name = task_name

    async def cluster_themes(
        self,
        articles: List[Dict[str, Any]],
        batch_size: int = 10,
        score_threshold: int = 90
    ) -> Dict[str, Any]:
        """聚类文章主题

        Args:
            articles: 文章列表
            batch_size: 每批次处理的文章数量

        Returns:
            {
                "success": bool,
                "has_common_theme": bool,
                "main_theme": Optional[Dict],  # 主要主题
                "candidate_themes": List[Dict],  # 候选主题
                "error": Optional[str]  # 错误信息
            }
        """
        try:
            # 筛选高质量文章
            filtered_articles = self._filter_articles(articles, score_threshold=score_threshold)

            if not filtered_articles:
                logger.warning("没有高质量的文章可用于主题聚类")
                return {
                    "success": False,
                    "has_common_theme": False,
                    "main_theme": None,
                    "candidate_themes": [],
                    "error": "没有高质量的文章可用于主题聚类"
                }

            logger.info(f"筛选出 {len(filtered_articles)} 篇高质量文章用于分析")

            # 如果文章数量较少，直接分析
            if len(filtered_articles) <= batch_size:
                return await self._analyze_batch(filtered_articles)
            
            # 否则进行分批处理 (Map-Reduce)
            return await self._process_batches(filtered_articles, batch_size)

        except Exception as e:
            logger.error(f"主题聚类失败: {str(e)}")
            return {
                "success": False,
                "has_common_theme": False,
                "main_theme": None,
                "candidate_themes": [],
                "error": str(e)
            }

    async def _analyze_batch(self, articles: List[Dict[str, Any]], max_retries: int = 2) -> Dict[str, Any]:
        """分析单批次文章，支持重试机制"""
        # 准备LLM输入
        llm_input = self._prepare_llm_input(articles)

        # 重试机制
        for attempt in range(max_retries + 1):
            try:
                # 调用LLM进行主题聚类
                response = self.llm_client.call(
                    task_name=self.task_name,
                    user_prompt=llm_input
                )

                # 解析响应
                result = self._parse_response(response)
                self._attach_theme_articles(result, articles)

                main_theme = result.get('main_theme')
                if main_theme and isinstance(main_theme, dict):
                    theme_name = main_theme.get('name', '无')
                else:
                    theme_name = '无'
                logger.info(f"批次分析完成，识别到主要主题: {theme_name}")
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 2  # 指数退避：2s, 4s
                    logger.warning(f"批次分析失败 (尝试 {attempt + 1}/{max_retries + 1})，{wait_time}秒后重试: {str(e)}")
                    import asyncio
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"批次分析最终失败，已用尽所有重试机会: {str(e)}")
                    # 返回失败结果，但不抛出异常，让流程继续
                    return {
                        "success": False,
                        "has_common_theme": False,
                        "main_theme": None,
                        "candidate_themes": [],
                        "error": f"批次分析失败: {str(e)}"
                    }

    async def _process_batches(self, articles: List[Dict[str, Any]], batch_size: int) -> Dict[str, Any]:
        """分批处理文章并合并结果 (Map-Reduce)"""
        batches = [articles[i:i + batch_size] for i in range(0, len(articles), batch_size)]
        logger.info(f"文章数量 {len(articles)} > {batch_size}，分为 {len(batches)} 批处理")

        batch_results = []
        failed_batches = []
        
        for i, batch in enumerate(batches):
            logger.info(f"正在处理第 {i+1}/{len(batches)} 批...")
            try:
                result = await self._analyze_batch(batch)
                if result.get("success"):
                    batch_results.append(result)
                    logger.info(f"第 {i+1}/{len(batches)} 批处理成功")
                else:
                    failed_batches.append(i+1)
                    logger.warning(f"第 {i+1}/{len(batches)} 批处理失败: {result.get('error', '未知错误')}")
            except Exception as e:
                failed_batches.append(i+1)
                logger.error(f"第 {i+1}/{len(batches)} 批处理异常: {str(e)}")
        
        if not batch_results:
            return {
                "success": False,
                "has_common_theme": False,
                "error": f"所有批次分析均失败，失败的批次: {failed_batches}"
            }

        if failed_batches:
            logger.warning(f"部分批次处理失败，失败的批次: {failed_batches}，将使用成功批次的结果进行合并")

        # Reduce: 合并结果
        return await self._merge_results(batch_results)

    async def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个批次的分析结果"""
        logger.info("正在合并多批次分析结果...")
        
        # 提取所有识别出的主题
        all_themes = []
        for res in results:
            if res.get("main_theme"):
                all_themes.append({"type": "main", "content": res["main_theme"]})
            for theme in res.get("candidate_themes", []):
                all_themes.append({"type": "candidate", "content": theme})
        
        if not all_themes:
             return {
                "success": True,
                "has_common_theme": False,
                "main_theme": None,
                "candidate_themes": []
            }

        # 构造合并任务的输入
        # 为了复用 _analyze_batch，我们将主题转换为"虚拟文章"
        virtual_articles = []
        for i, item in enumerate(all_themes, 1):
            theme = item["content"]
            virtual_articles.append({
                "title": f"主题片段: {theme.get('name', '未命名')}",
                "llm_thematic_essence": theme.get('description', ''),
                "llm_tags": theme.get('keywords', []),
                "llm_score": 90 # 假分数，确保通过筛选
            })
            
        return await self._analyze_batch(virtual_articles)

    def _filter_articles(self, articles: List[Dict[str, Any]],
                        score_threshold: int = 90) -> List[Dict[str, Any]]:
        """筛选高质量文章"""
        filtered = []
        for article in articles:
            if article.get("llm_score", 0) >= score_threshold:
                if article.get("llm_thematic_essence"):
                    filtered.append(article)

        # 按分数降序排序
        filtered.sort(key=lambda x: x.get("llm_score", 0), reverse=True)
        
        # 提取关键字段
        processed_articles = []
        for article in filtered:
            processed_articles.append({
                "id": article.get("id", ""),  # 保留文章唯一ID
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "llm_thematic_essence": article.get("llm_thematic_essence", ""),
                "llm_tags": article.get("llm_tags", []),
                "llm_score": article.get("llm_score", 0),
                "published_date": article.get("published_date", ""),
                "url": article.get("url") or article.get("link", ""),
                "link": article.get("link", "")
            })
            
        return processed_articles

    def _prepare_llm_input(self, articles: List[Dict[str, Any]]) -> str:
        """准备LLM输入"""
        input_data = []
        for article in articles:
            input_data.append({
                "id": article.get("id", ""),  # 文章唯一ID
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "url": article.get("url", "") or article.get("link", ""),
                "thematic_essence": article.get("llm_thematic_essence", ""),
                "tags": article.get("llm_tags", []),
                "score": article.get("llm_score", 0),
                "published_date": article.get("published_date", "")
            })

        return json.dumps(input_data, ensure_ascii=False, indent=2)

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            result = json.loads(response)
            if not isinstance(result, dict):
                raise ValueError("响应格式错误：期望字典类型")

            result.setdefault("success", True)
            result.setdefault("has_common_theme", False)
            result.setdefault("main_theme", None)
            result.setdefault("candidate_themes", [])

            return result

        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {e}")
            return {
                "success": False,
                "has_common_theme": False,
                "main_theme": None,
                "candidate_themes": [],
                "error": f"解析响应失败: {str(e)}"
            }

    def _attach_theme_articles(self, result: Dict[str, Any], articles: List[Dict[str, Any]]):
        """根据article_ids回填主题关联文章"""
        if not isinstance(result, dict) or not articles:
            return

        # 创建文章ID到文章对象的映射，支持多种ID类型
        id_map = {}
        for article in articles:
            article_id = article.get("id", "")
            if article_id:
                # 同时存储原始类型和字符串类型，确保匹配成功
                id_map[str(article_id)] = article
                id_map[article_id] = article

        def build_article_list(article_ids: Any) -> List[Dict[str, Any]]:
            mapped = []
            if not isinstance(article_ids, list):
                return mapped

            seen = set()
            for article_id in article_ids:
                # 标准化ID为字符串进行比较
                article_id_str = str(article_id) if article_id is not None else ""
                if not article_id_str:
                    continue
                if article_id_str in seen:
                    continue
                
                # 尝试多种匹配方式
                article = id_map.get(article_id_str) or id_map.get(article_id)
                if not article:
                    logger.warning(f"主题文章ID {article_id} 未匹配到文章")
                    continue
                seen.add(article_id_str)
                mapped.append({
                    "id": article.get("id", ""),
                    "title": article.get("title", ""),
                    "source": article.get("source", ""),
                    "published_date": article.get("published_date", ""),
                    "url": article.get("url") or article.get("link", "")
                })
            return mapped

        main_theme = result.get("main_theme")
        if isinstance(main_theme, dict):
            article_list = build_article_list(main_theme.get("article_ids"))
            main_theme["articles"] = article_list
            main_theme["article_count"] = len(article_list)

        candidate_themes = result.get("candidate_themes", [])
        if isinstance(candidate_themes, list):
            for theme in candidate_themes:
                if not isinstance(theme, dict):
                    continue
                article_list = build_article_list(theme.get("article_ids"))
                theme["articles"] = article_list
                theme["article_count"] = len(article_list)
