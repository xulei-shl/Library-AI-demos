"""
模块8主流程编排器
Phase 2: LLM打标功能
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
    """模块8主流程编排器"""
    
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
        theme_text: str,
        use_vector: bool = True,
        vector_weight: float = 0.5,
        randomness: float = 0.2,
        min_confidence: float = 0.65,
        final_top_k: int = 30,
        output_dir: str = "runtime/outputs/theme_shelf",
        config_path: str = "config/literature_fm_vector.yaml"
    ) -> Dict:
        """
        生成情境主题书架

        Args:
            theme_text: 用户输入的情境主题（如 "冬日暖阳，窝在沙发里阅读"）
            use_vector: 是否使用向量检索
            vector_weight: 向量检索权重
            randomness: 随机性因子（0-1）
            min_confidence: 最小置信度
            final_top_k: 最终输出数量
            output_dir: 输出目录
            config_path: 配置文件路径

        Returns:
            {
                "success": True,
                "theme": "冬日暖阳，窝在沙发里阅读",
                "conditions": {...},
                "books": [...],
                "output_file": "output/主题书架_xxx.xlsx",
                "stats": {...}
            }
        """
        try:
            logger.info("\n" + "="*80)
            logger.info("模块8 - Phase 3: 情境主题书架生成")
            logger.info("="*80 + "\n")

            # 1. 初始化组件
            from .theme_parser import ThemeParser
            from .theme_searcher import TagSearcher
            from .theme_merger import ThemeMerger
            from .theme_deduplicator import ThemeDeduplicator
            from .theme_exporter import ThemeExporter
            from .db_init import init_recommendation_history_table

            # 初始化历史表
            init_recommendation_history_table()

            theme_parser = ThemeParser()
            tag_searcher = TagSearcher()
            deduplicator = ThemeDeduplicator()
            exporter = ThemeExporter(output_dir)

            # 向量检索器（可选）
            vector_searcher = None
            if use_vector:
                try:
                    from .vector_searcher import VectorSearcher
                    vector_searcher = VectorSearcher(config_path)
                    logger.info("✓ 向量检索器初始化成功\n")
                except Exception as e:
                    logger.warning(f"✗ 向量检索器初始化失败: {str(e)}，将使用纯标签检索")
                    use_vector = False

            # 2. 主题解析
            logger.info("【步骤1】主题解析...")
            parsed = theme_parser.parse(theme_text)
            conditions = parsed.get('conditions', {})
            reason_text = parsed.get('reason', '')
            logger.info(f"  解析结果: {conditions}")
            logger.info(f"  解析理由: {reason_text[:100]}...\n")

            # 3. 去重检查
            logger.info("【步骤2】去重检查...")
            excluded_ids = deduplicator.get_excluded_book_ids(theme_text, conditions)
            logger.info(f"  需排除 {len(excluded_ids)} 本已推荐书目\n")

            # 4. 双路召回
            logger.info("【步骤3】双路召回...")
            vector_results = []
            tag_results = []

            if use_vector and vector_searcher:
                logger.info("  - 向量检索中...")
                # 使用解析理由作为向量检索查询（理由包含更丰富的语义描述）
                vector_query = reason_text if reason_text else theme_text
                vector_results = vector_searcher.search(
                    query_text=vector_query,
                    top_k=50,
                    min_confidence=min_confidence
                )
                vector_results = [r for r in vector_results if r['book_id'] not in excluded_ids]
                logger.info(f"    -> {len(vector_results)} 本")

            logger.info("  - 标签检索中...")
            tag_results = tag_searcher.search(
                conditions=conditions,
                min_confidence=min_confidence,
                randomness=randomness,
                limit=50
            )
            tag_results = [r for r in tag_results if r.book_id not in excluded_ids]
            logger.info(f"    -> {len(tag_results)} 本\n")

            # 5. 结果融合
            logger.info("【步骤4】结果融合...")
            merger = ThemeMerger(vector_weight=vector_weight)
            merged = merger.merge(vector_results, [
                {'book_id': r.book_id, 'title': r.title, 'author': r.author,
                 'call_no': r.call_no, 'tags_json': r.tags_json,
                 'vector_score': 0, 'tag_score': r.tag_score, 'sources': ['tag']}
                for r in tag_results
            ] if tag_results else [])

            # 合并向量结果
            merged_dicts = merger.to_dict_list(merged)
            for vr in vector_results:
                if vr['book_id'] not in [m['book_id'] for m in merged_dicts]:
                    merged_dicts.append({
                        'book_id': vr['book_id'],
                        'title': vr['title'],
                        'author': vr['author'],
                        'call_no': vr['call_no'],
                        'tags_json': vr.get('tags_json', ''),
                        'vector_score': vr['vector_score'],
                        'tag_score': 0,
                        'final_score': vr['vector_score'] * vector_weight,
                        'sources': ['vector']
                    })

            # 再次排序
            merged_dicts.sort(key=lambda x: x['final_score'], reverse=True)
            final_books = merged_dicts[:final_top_k]

            logger.info(f"  融合后共 {len(final_books)} 本\n")

            # 6. 保存推荐记录
            logger.info("【步骤5】保存推荐记录...")
            book_ids = [b['book_id'] for b in final_books]
            deduplicator.save_recommendation(
                user_input=theme_text,
                conditions=conditions,
                book_ids=book_ids,
                vector_weight=vector_weight,
                randomness=randomness
            )
            logger.info(f"  已保存 {len(book_ids)} 本推荐记录\n")

            # 7. 导出结果
            logger.info("【步骤6】导出结果...")
            output_file = exporter.export_excel(
                results=final_books,
                theme_text=theme_text,
                conditions=conditions
            )
            logger.info(f"  -> {output_file}\n")

            # 8. 输出统计
            logger.info("\n" + "="*80)
            logger.info("情境主题书架生成完成！")
            logger.info(f"  - 主题: {theme_text}")
            logger.info(f"  - 推荐数量: {len(final_books)}")
            logger.info(f"  - 向量检索: {len(vector_results)} 本")
            logger.info(f"  - 标签检索: {len(tag_results)} 本")
            logger.info(f"  - 排除数量: {len(excluded_ids)} 本")
            logger.info(f"  - 输出文件: {output_file}")
            logger.info("="*80 + "\n")

            return {
                "success": True,
                "theme": theme_text,
                "conditions": conditions,
                "reason": parsed.get('reason', ''),
                "books": final_books,
                "output_file": output_file,
                "stats": {
                    "vector_results": len(vector_results),
                    "tag_results": len(tag_results),
                    "excluded_count": len(excluded_ids),
                    "final_count": len(final_books)
                }
            }

        except Exception as e:
            logger.error(f"主题书架生成失败: {str(e)}", exc_info=True)
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