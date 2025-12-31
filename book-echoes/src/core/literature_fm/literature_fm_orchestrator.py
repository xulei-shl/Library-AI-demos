"""
文学情境推荐模块 - 主流程编排器
协调 LLM打标、主题生成、查询转换、混合检索等功能
"""

from pathlib import Path
import sys

# 添加项目根目录到路径
root_dir = Path(__file__).absolute().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from datetime import datetime
import pandas as pd
import sqlite3
import yaml
from typing import List, Dict

from src.utils.logger import get_logger
from src.core.literature_fm.llm_tagger import LLMTagger
from src.core.literature_fm.tag_manager import TagManager

logger = get_logger(__name__)


class LiteratureFMPipeline:
    """文学情境推荐模块主流程编排器"""
    
    def __init__(self):
        self.config = self._load_config()
        self.tag_manager = TagManager()
        self.llm_tagger = None  # 延迟初始化
    
    def _load_config(self) -> dict:
        """加载配置"""
        try:
            # 直接读取 literature_fm.yaml 配置文件
            config_path = root_dir / 'config' / 'literature_fm.yaml'
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            logger.info("✓ 配置加载成功: literature_fm.yaml")
            return config
        except Exception as e:
            logger.error(f"✗ 配置加载失败: {str(e)}")
            raise
    
    def run_llm_tagging(self) -> bool:
        """
        运行LLM打标流程
        
        Returns:
            bool: 是否成功
        """
        try:
            logger.info("\n" + "="*80)
            logger.info("模块8 - Phase 2: LLM打标功能")
            logger.info("="*80 + "\n")
            
            # 1. 检查是否启用
            llm_config = self.config.get('llm_tagging', {})
            if not llm_config.get('enabled', False):
                logger.warning("LLM打标功能未启用，请在配置文件中设置 llm_tagging.enabled = true")
                return False
            
            # 2. 初始化LLM打标器
            logger.info("【步骤1】初始化LLM打标器...")
            self.llm_tagger = LLMTagger(llm_config)
            logger.info("✓ LLM打标器初始化成功\n")
            
            # 3. 筛选待打标书目
            logger.info("【步骤2】筛选待打标书目...")
            books_to_tag = self._get_books_to_tag()
            
            if not books_to_tag:
                logger.info("没有需要打标的书目")
                return True
            
            logger.info(f"✓ 筛选完成，共 {len(books_to_tag)} 本书待打标\n")
            
            # 4. 批量打标
            logger.info("【步骤3】开始批量打标...")
            stats = self.llm_tagger.tag_books(books_to_tag)
            logger.info(f"✓ 批量打标完成\n")
            
            # 5. 兜底重试
            logger.info("【步骤4】兜底重试...")
            retry_stats = self.llm_tagger.fallback_retry()
            logger.info(f"✓ 兜底重试完成\n")
            
            # 6. 导出结果
            if llm_config.get('output', {}).get('export_to_excel', False):
                logger.info("【步骤5】导出打标结果...")
                self._export_results()
                logger.info(f"✓ 结果导出完成\n")
            
            # 7. 输出最终统计
            total_success = stats['success'] + retry_stats['success']
            total_failed = stats['failed'] + retry_stats['failed'] - retry_stats['success']
            
            logger.info("\n" + "="*80)
            logger.info("LLM打标流程完成！")
            logger.info(f"  - 成功打标: {total_success} 本")
            logger.info(f"  - 失败: {total_failed} 本")
            logger.info("="*80 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"LLM打标流程失败: {str(e)}", exc_info=True)
            return False
    
    def _get_books_to_tag(self) -> List[Dict]:
        """
        从 books 表筛选待打标书目
        
        Returns:
            List[Dict]: 待打标书目列表
        """
        try:
            llm_config = self.config.get('llm_tagging', {})
            filter_conditions = llm_config.get('filter_conditions', {})
            
            # 获取已成功打标的 book_id
            tagged_ids = self.tag_manager.get_tagged_book_ids(status='success')
            
            # 构建SQL查询
            db_path = self.config.get('logging', {}).get('database', {}).get('db_path', 'runtime/database/books_history.db')
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 基础查询
            query = "SELECT id, book_title, douban_author, call_no, douban_summary, douban_rating, douban_pub_year FROM books WHERE 1=1"
            params = []
            
            # 索书号前缀过滤
            call_no_prefix = filter_conditions.get('call_no_prefix')
            if call_no_prefix:
                query += " AND call_no LIKE ?"
                params.append(f"{call_no_prefix}%")
            
            # 最低评分过滤
            min_rating = filter_conditions.get('min_douban_rating')
            if min_rating:
                query += " AND douban_rating >= ?"
                params.append(min_rating)
            
            # 必填字段过滤
            required_fields = filter_conditions.get('required_fields', [])
            for field in required_fields:
                query += f" AND {field} IS NOT NULL AND {field} != ''"
            
            # 排除已打标的书目
            if tagged_ids:
                placeholders = ','.join('?' * len(tagged_ids))
                query += f" AND id NOT IN ({placeholders})"
                params.extend(tagged_ids)

            # 限制处理数量（用于测试，节省大模型调用费用）
            max_items = llm_config.get('max_items', 0)
            if max_items > 0:
                query += f" LIMIT {max_items}"

            cursor.execute(query, params)
            books = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            logger.info(f"  - 数据库总书目: {len(books) + len(tagged_ids)}")
            logger.info(f"  - 已打标: {len(tagged_ids)}")
            logger.info(f"  - 待打标: {len(books)}")
            
            return books
            
        except Exception as e:
            logger.error(f"筛选待打标书目失败: {str(e)}")
            return []
    
    def _export_results(self) -> bool:
        """
        导出打标结果到Excel
        
        Returns:
            bool: 是否成功
        """
        try:
            llm_config = self.config.get('llm_tagging', {})
            output_config = llm_config.get('output', {})
            
            # 获取输出目录
            output_dir = Path(output_config.get('output_dir', 'runtime/outputs/literary_tagging'))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            filename_template = output_config.get('filename_template', '文学标签结果_{timestamp}.xlsx')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = filename_template.replace('{timestamp}', timestamp)
            output_path = output_dir / filename
            
            # 导出数据
            df = self.tag_manager.export_to_dataframe()
            
            if df.empty:
                logger.warning("没有可导出的数据")
                return False
            
            # 解析 tags_json 列，展开为多列
            df = self._expand_tags_json(df)
            
            # 保存到Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            
            logger.info(f"  - 导出文件: {output_path}")
            logger.info(f"  - 记录数: {len(df)}")
            
            return True
            
        except Exception as e:
            logger.error(f"导出结果失败: {str(e)}")
            return False
    
    def _expand_tags_json(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        展开 tags_json 列为多列
        
        Args:
            df: 原始DataFrame
            
        Returns:
            pd.DataFrame: 展开后的DataFrame
        """
        try:
            import json
            
            # 解析 tags_json
            tags_list = []
            for tags_json in df['tags_json']:
                try:
                    tags = json.loads(tags_json)
                    tags_list.append(tags)
                except:
                    tags_list.append({})
            
            # 提取各维度标签
            df['阅读情境'] = [', '.join(t.get('reading_context', [])) for t in tags_list]
            df['阅读体感'] = [', '.join(t.get('reading_load', [])) for t in tags_list]
            df['文本质感'] = [', '.join(t.get('text_texture', [])) for t in tags_list]
            df['时空氛围'] = [', '.join(t.get('spatial_atmosphere', [])) for t in tags_list]
            df['情绪基调'] = [', '.join(t.get('emotional_tone', [])) for t in tags_list]
            
            # 提取置信度
            df['置信度_阅读情境'] = [t.get('confidence_scores', {}).get('reading_context', 0) for t in tags_list]
            df['置信度_阅读体感'] = [t.get('confidence_scores', {}).get('reading_load', 0) for t in tags_list]
            df['置信度_文本质感'] = [t.get('confidence_scores', {}).get('text_texture', 0) for t in tags_list]
            df['置信度_时空氛围'] = [t.get('confidence_scores', {}).get('spatial_atmosphere', 0) for t in tags_list]
            df['置信度_情绪基调'] = [t.get('confidence_scores', {}).get('emotional_tone', 0) for t in tags_list]
            
            # 删除原始 tags_json 列
            df = df.drop(columns=['tags_json'])
            
            return df

        except Exception as e:
            logger.error(f"展开 tags_json 失败: {str(e)}")
            return df

    def generate_theme_shelf(
        self,
        translated_queries: List[Dict],
        output_dir: str = "runtime/outputs/theme_shelf",
        config_path: str = "config/literature_fm_vector.yaml"
    ) -> Dict:
        """
        Phase 3增强版：混合检索 + RRF融合

        Args:
            translated_queries: QueryTranslator输出的查询列表，格式：
                [
                    {
                        "filter_conditions": [
                            {"field": "reading_context", "values": ["A", "B"], "operator": "SHOULD"},
                            {"field": "reading_load", "values": ["C"], "operator": "MUST_NOT"}
                        ],
                        "search_keywords": ["荒野", "星空", "海洋"],
                        "synthetic_query": "这本书非常适合那些被信息过载压垮的读者...",
                        "original_theme": {
                            "theme_name": "...",
                            "slogan": "...",
                            "description": "...",
                            "target_vibe": "..."
                        }
                    }
                ]
            output_dir: 输出目录
            config_path: 配置文件路径

        Returns:
            {
                "success": True,
                "themes": [...],
                "total_books": 100,
                "output_file": "..."
            }
        """
        try:
            import yaml
            from pathlib import Path

            logger.info("\n" + "="*80)
            logger.info("模块8 - Phase 3: 混合检索 + RRF融合")
            logger.info("="*80 + "\n")

            # 加载配置
            config_file = Path(root_dir) / config_path
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            default_config = config.get('default', {})
            db_config = config.get('database', {})
            bm25_config = config.get('bm25', {})
            rrf_config = config.get('rrf', {})
            reranker_config = config.get('reranker', {})

            # 1. 初始化组件
            from .vector_searcher import VectorSearcher
            from .hybrid_vector_searcher import HybridVectorSearcher
            from .bm25_searcher import BM25Searcher
            from .rrf_fusion import RRFFusion
            from .theme_deduplicator import ThemeDeduplicator
            from .theme_exporter import ThemeExporter
            from .db_init import init_recommendation_history_table

            # 初始化历史表
            init_recommendation_history_table()

            deduplicator = ThemeDeduplicator()
            exporter = ThemeExporter(output_dir)

            # 向量检索器
            if default_config.get('use_vector', True):
                base_vector_searcher = VectorSearcher(config_path)
                vector_searcher = HybridVectorSearcher(base_vector_searcher)
                logger.info("✓ 向量检索器初始化成功")
            else:
                vector_searcher = None
                logger.info("向量检索未启用")

            # BM25检索器
            if default_config.get('use_bm25', True) and bm25_config.get('enabled', True):
                bm25_searcher = BM25Searcher(
                    db_path=db_config['path'],
                    table=db_config['table'],
                    k1=bm25_config.get('k1', 1.5),
                    b=bm25_config.get('b', 0.75),
                    field_weights=bm25_config.get('field_weights', {})
                )
                logger.info("✓ BM25检索器初始化成功（懒加载模式）")
            else:
                bm25_searcher = None
                logger.info("BM25检索未启用")

            # RRF融合器
            rrf_fusion = RRFFusion(k=rrf_config.get('k', 60))
            logger.info(f"✓ RRF融合器初始化成功 (k={rrf_fusion.get_k()})")

            # CrossEncoder重排序器（可选）
            reranker = None
            if reranker_config.get('enabled', False):
                from .cross_encoder_reranker import CrossEncoderReranker
                reranker = CrossEncoderReranker(
                    model_name=reranker_config.get('model', 'BAAI/bge-reranker-v2-m3'),
                    device=reranker_config.get('device', 'cpu')
                )
                logger.info(f"✓ CrossEncoder重排序器初始化成功")

            logger.info("")

            # 2. 处理每个主题
            all_results = []

            for idx, query_item in enumerate(translated_queries, start=1):
                filter_conditions = query_item.get('filter_conditions', [])
                search_keywords = query_item.get('search_keywords', [])
                synthetic_query = query_item.get('synthetic_query', '')
                original_theme = query_item.get('original_theme', {})

                theme_name = original_theme.get('theme_name', f'主题{idx}')

                logger.info(f"\n{'─'*60}")
                logger.info(f"处理主题 {idx}/{len(translated_queries)}: {theme_name}")
                logger.info(f"{'─'*60}")

                # 2.1 去重检查
                logger.info("【步骤1】去重检查...")
                excluded_ids = deduplicator.get_excluded_book_ids(
                    theme_name,
                    {"filter_conditions": filter_conditions}
                )
                logger.info(f"  需排除 {len(excluded_ids)} 本已推荐书目")

                # 2.2 并行双路检索
                logger.info("【步骤2】并行双路召回...")

                vector_results = []
                bm25_results = []

                # 路A: 向量检索（带过滤条件）
                if vector_searcher:
                    logger.info("  - 向量检索中...")
                    try:
                        vector_results = vector_searcher.search(
                            query_text=synthetic_query,
                            filter_conditions=filter_conditions,
                            top_k=default_config.get('vector_top_k', 50),
                            min_confidence=default_config.get('min_confidence', 0.80),
                            excluded_ids=excluded_ids
                        )
                        logger.info(f"    -> 召回 {len(vector_results)} 本")
                    except Exception as e:
                        logger.warning(f"    向量检索失败: {str(e)}")

                # 路B: BM25检索（关键词匹配）
                if bm25_searcher and search_keywords:
                    logger.info("  - BM25检索中...")
                    try:
                        bm25_results = bm25_searcher.search(
                            keywords=search_keywords,
                            top_k=default_config.get('bm25_top_k', 50),
                            excluded_ids=excluded_ids
                        )
                        logger.info(f"    -> 召回 {len(bm25_results)} 本")
                    except Exception as e:
                        logger.warning(f"    BM25检索失败: {str(e)}")

                # 2.3 RRF融合
                logger.info("【步骤3】RRF融合...")
                if default_config.get('use_rrf', True) and vector_results and bm25_results:
                    merged = rrf_fusion.merge(
                        results_a=vector_results,
                        results_b=bm25_results,
                        rank_key_a="vector_score",
                        rank_key_b="bm25_score"
                    )
                    logger.info(f"  -> 融合后 {len(merged)} 本")
                elif vector_results:
                    # 仅向量检索
                    merged = vector_results
                    logger.info(f"  -> 仅向量结果 {len(merged)} 本")
                elif bm25_results:
                    # 仅BM25检索
                    merged = bm25_results
                    logger.info(f"  -> 仅BM25结果 {len(merged)} 本")
                else:
                    merged = []
                    logger.warning("  无检索结果")

                # 2.4 [可选] CrossEncoder重排序
                if reranker and merged:
                    logger.info("【步骤4】CrossEncoder重排序...")
                    try:
                        merged = reranker.rerank(
                            query=synthetic_query,
                            results=merged,
                            top_k=reranker_config.get('top_k', 50),
                            batch_size=reranker_config.get('batch_size', 32)
                        )
                        logger.info(f"  -> 重排序后取 {len(merged)} 本")
                    except Exception as e:
                        logger.warning(f"    重排序失败: {str(e)}")

                # 2.5 最终截断
                final_top_k = default_config.get('final_top_k', 30)
                final_books = merged[:final_top_k]

                # 2.6 保存推荐记录
                if final_books:
                    logger.info("【步骤5】保存推荐记录...")
                    book_ids = [b['book_id'] for b in final_books]
                    deduplicator.save_recommendation(
                        user_input=original_theme.get('description', ''),
                        conditions={"filter_conditions": filter_conditions},
                        book_ids=book_ids
                    )
                    logger.info(f"  已保存 {len(book_ids)} 本推荐记录")

                # 收集结果
                all_results.append({
                    "theme": original_theme,
                    "books": final_books,
                    "filter_conditions": filter_conditions,
                    "search_keywords": search_keywords,
                    "stats": {
                        "vector_count": len(vector_results),
                        "bm25_count": len(bm25_results),
                        "final_count": len(final_books)
                    }
                })

            # 3. 导出结果
            logger.info("\n【步骤6】导出结果...")
            output_file = exporter.export_theme_batch(all_results)

            # 4. 输出统计
            total_books = sum(len(r["books"]) for r in all_results)

            logger.info("\n" + "="*80)
            logger.info("混合检索流程完成！")
            logger.info(f"  - 主题数量: {len(all_results)}")
            logger.info(f"  - 总推荐书籍: {total_books}")
            logger.info(f"  - 输出文件: {output_file}")
            logger.info("="*80 + "\n")

            return {
                "success": True,
                "themes": all_results,
                "total_books": total_books,
                "output_file": output_file
            }

        except Exception as e:
            logger.error(f"混合检索流程失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """主函数入口"""
    pipeline = LiteratureFMPipeline()
    success = pipeline.run_llm_tagging()
    
    if success:
        logger.info("✓ 流程执行成功")
    else:
        logger.error("✗ 流程执行失败")
    
    return success


if __name__ == "__main__":
    main()