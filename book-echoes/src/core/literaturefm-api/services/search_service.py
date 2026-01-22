"""
文学检索服务
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径 (从 literaturefm-api/services/search_service.py 到项目根)
# search_service.py -> services -> literaturefm-api -> literature_fm -> core -> src -> book-echoes
root_dir = Path(__file__).absolute().parent.parent.parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# 添加 literaturefm-api 目录到路径（用于导入models和config）
api_dir = Path(__file__).absolute().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from src.utils.logger import get_logger

# 复用现有检索组件（使用绝对导入）
from src.core.literature_fm.hybrid_vector_searcher import HybridVectorSearcher
from src.core.literature_fm.bm25_searcher import BM25Searcher
from src.core.literature_fm.rrf_fusion import RRFFusion
from src.core.literature_fm.vector_searcher import VectorSearcher
from src.core.literature_fm.cross_encoder_reranker import CrossEncoderReranker
from models.requests import SearchRequest, FilterCondition
from models.responses import BookResult, SearchMetadata, RetrievalStats

logger = get_logger(__name__)


class LiterarySearchService:
    """文学检索服务"""

    def __init__(self, config_path: str = None):
        """
        初始化检索服务

        Args:
            config_path: 配置文件路径，默认使用 literature_fm_vector.yaml
        """
        # 加载配置（绝对导入）
        from config import load_config
        self.config = load_config()

        # 获取默认配置
        default_config = self.config.get('default', {})
        db_config = self.config.get('database', {})
        bm25_config = self.config.get('bm25', {})
        rrf_config = self.config.get('rrf', {})
        reranker_config = self.config.get('reranker', {})

        # 初始化向量检索器
        if default_config.get('use_vector', True):
            # 传递项目根目录下的配置文件路径
            vector_config_path = str(root_dir / "config" / "literature_fm_vector.yaml")
            base_vector_searcher = VectorSearcher(config_path=vector_config_path)
            self.vector_searcher = HybridVectorSearcher(base_vector_searcher)
            logger.info("✓ 向量检索器初始化成功")
        else:
            self.vector_searcher = None
            logger.info("向量检索未启用")

        # 初始化BM25检索器
        if default_config.get('use_bm25', True) and bm25_config.get('enabled', True):
            self.bm25_searcher = BM25Searcher(
                db_path=db_config.get('path', 'runtime/database/books_history.db'),
                table=db_config.get('table', 'literary_tags'),
                k1=bm25_config.get('k1', 1.5),
                b=bm25_config.get('b', 0.75),
                field_weights=bm25_config.get('field_weights', {})
            )
            logger.info("✓ BM25检索器初始化成功")
        else:
            self.bm25_searcher = None
            logger.info("BM25检索未启用")

        # 初始化RRF融合器
        self.rrf_fusion = RRFFusion(k=rrf_config.get('k', 60))
        logger.info(f"✓ RRF融合器初始化成功 (k={self.rrf_fusion.get_k()})")

        # 初始化重排序器（可选）
        self.reranker = None
        if reranker_config.get('enabled', False):
            self.reranker = CrossEncoderReranker(config=reranker_config)
            logger.info(f"✓ Reranker初始化成功")

    def search(self, request: SearchRequest) -> Dict[str, Any]:
        """
        执行单主题检索

        Args:
            request: 检索请求

        Returns:
            检索结果字典
        """
        try:
            # 转换过滤条件格式
            filter_conditions = self._convert_filter_conditions(request.filter_conditions)

            # 1. 向量检索
            vector_results = []
            if self.vector_searcher:
                try:
                    vector_results = self.vector_searcher.search(
                        query_text=request.synthetic_query,
                        filter_conditions=filter_conditions,
                        top_k=request.top_k,
                        min_confidence=request.min_confidence
                    )
                    logger.info(f"向量检索召回 {len(vector_results)} 本")
                except Exception as e:
                    logger.warning(f"向量检索失败: {str(e)}")

            # 2. BM25检索
            bm25_results = []
            if self.bm25_searcher:
                try:
                    bm25_results = self.bm25_searcher.search_with_randomness(
                        keywords=request.search_keywords,
                        top_k=request.top_k,
                        randomness=request.bm25_randomness
                    )
                    logger.info(f"BM25检索召回 {len(bm25_results)} 本")
                except Exception as e:
                    logger.warning(f"BM25检索失败: {str(e)}")

            # 3. RRF融合（自动去重）
            if vector_results and bm25_results:
                merged = self.rrf_fusion.merge(
                    results_a=vector_results,
                    results_b=bm25_results
                )
            elif vector_results:
                merged = vector_results
            elif bm25_results:
                merged = bm25_results
            else:
                merged = []
                logger.warning("无检索结果")

            # 4. 可选重排序
            if request.enable_rerank and self.reranker and merged:
                try:
                    merged = self.reranker.rerank(
                        query=request.synthetic_query,
                        results=merged,
                        top_k=request.top_k
                    )
                    logger.info(f"重排序后 {len(merged)} 本")
                except Exception as e:
                    logger.warning(f"重排序失败: {str(e)}")

            # 5. 截取TopK
            final_results = merged[:request.top_k]

            # 6. 格式化响应
            return self._format_response(
                results=final_results,
                vector_count=len(vector_results),
                bm25_count=len(bm25_results),
                filter_conditions=request.filter_conditions,
                response_detail=request.response_detail
            )

        except Exception as e:
            logger.error(f"检索失败: {str(e)}", exc_info=True)
            raise

    def batch_search(self, queries: List[Dict[str, Any]], top_k: int,
                     response_detail: str, enable_rerank: bool) -> Dict[str, Any]:
        """
        执行批量检索

        Args:
            queries: 查询列表
            top_k: 每个查询返回数量
            response_detail: 响应详细程度
            enable_rerank: 是否启用重排序

        Returns:
            批量检索结果
        """
        results_list = []
        metadata_list = []

        for idx, query_item in enumerate(queries):
            logger.info(f"处理查询 {idx + 1}/{len(queries)}")

            # 构造SearchRequest
            request = SearchRequest(
                filter_conditions=query_item.get('filter_conditions', []),
                search_keywords=query_item.get('search_keywords', []),
                synthetic_query=query_item.get('synthetic_query', ''),
                top_k=top_k,
                response_detail=response_detail,
                enable_rerank=enable_rerank
            )

            # 执行检索
            result = self.search(request)
            results_list.append(result['results'])
            metadata_list.append(result['metadata'])

        return {
            "results": results_list,
            "metadata_list": metadata_list
        }

    def _convert_filter_conditions(self, conditions: List[FilterCondition]) -> List[Dict[str, Any]]:
        """
        转换过滤条件格式

        Args:
            conditions: Pydantic过滤条件列表

        Returns:
            字典格式的过滤条件列表
        """
        return [
            {
                "field": c.field,
                "values": c.values,
                "operator": c.operator
            }
            for c in conditions
        ]

    def _format_response(self, results: List[Dict], vector_count: int,
                         bm25_count: int, filter_conditions: List[FilterCondition],
                         response_detail: str) -> Dict[str, Any]:
        """
        格式化响应数据

        Args:
            results: 检索结果列表
            vector_count: 向量检索数量
            bm25_count: BM25检索数量
            filter_conditions: 过滤条件
            response_detail: 响应详细程度

        Returns:
            格式化的响应字典
        """
        # 格式化书籍结果
        formatted_results = []
        for item in results:
            book_result = BookResult(
                book_id=item.get('book_id'),
                title=item.get('title', ''),
                author=item.get('author', ''),
                call_no=item.get('call_no', ''),
                vector_score=item.get('vector_score'),
                bm25_score=item.get('bm25_score'),
                rrf_score=item.get('rrf_score'),
                sources=item.get('sources', []),
                tags_json=item.get('tags_json') if response_detail in ('standard', 'rich') else None
            )
            formatted_results.append(book_result.model_dump())

        # 构建元数据
        metadata_dict = {
            "total_count": len(formatted_results)
        }

        # standard 和 rich 模式包含过滤条件
        if response_detail in ('standard', 'rich') and filter_conditions:
            metadata_dict["filter_conditions_applied"] = [
                c.model_dump() for c in filter_conditions
            ]

        # rich 模式包含检索统计
        if response_detail == 'rich':
            metadata_dict["retrieval_stats"] = RetrievalStats(
                vector_count=vector_count,
                bm25_count=bm25_count,
                final_count=len(formatted_results)
            ).model_dump()

        return {
            "results": formatted_results,
            "metadata": metadata_dict
        }
