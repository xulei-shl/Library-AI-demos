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