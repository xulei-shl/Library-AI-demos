"""
查询意图转换器 (Query Translator)
负责将文学主题转换为结构化检索条件
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)


class QueryTranslator:
    """
    查询意图转换器

    将文学策展主题转换为三个检索要素：
    1. Tag Filters (结构化过滤条件)
    2. Keywords (BM25 全文检索关键词)
    3. Synthetic Query (向量检索的合成查询词)
    """

    # 定义有效的字段名（对应标签词表维度）
    VALID_FIELDS = {
        'reading_context',
        'reading_load',
        'text_texture',
        'spatial_atmosphere',
        'emotional_tone'
    }

    # 定义有效的操作符
    VALID_OPERATORS = {'SHOULD', 'MUST', 'MUST_NOT'}

    def __init__(self, config: dict = None, vocabulary_file: Optional[str] = None):
        """
        初始化转换器

        Args:
            config: 配置字典（从 literature_fm.yaml 读取）
            vocabulary_file: 标签词表文件路径，默认为 config/literary_tags_vocabulary.yaml
        """
        self.config = config or {}
        self.llm_client = UnifiedLLMClient()

        # 默认词表文件路径
        if vocabulary_file is None:
            vocabulary_file = "config/literary_tags_vocabulary.yaml"

        # 加载词表（用于用户提示词）
        self.vocabulary = self._load_vocabulary(vocabulary_file)

    def translate_theme(
        self,
        theme_name: str,
        slogan: str,
        description: str,
        target_vibe: str
    ) -> Dict:
        """
        转换单个主题为检索条件

        Args:
            theme_name: 主题名称
            slogan: 副标题/推荐语
            description: 情境描述
            target_vibe: 预期氛围

        Returns:
            {
                "filter_conditions": [...],
                "search_keywords": [...],
                "synthetic_query": "...",
                "original_theme": {...}
            }
        """
        try:
            # 1. 构建用户提示词（包含词表）
            user_prompt = self._build_user_prompt(
                theme_name, slogan, description, target_vibe
            )

            # 2. 调用 LLM
            logger.info(f"正在转换主题: {theme_name}")
            response = self.llm_client.call(
                task_name='literary_query_translation',
                user_prompt=user_prompt
            )

            # 3. 解析响应
            result = self._parse_response(response)

            # 4. 验证结果
            if not self._validate_result(result):
                raise ValueError("转换结果验证失败")

            # 5. 添加原始主题信息
            result['original_theme'] = {
                'theme_name': theme_name,
                'slogan': slogan,
                'description': description,
                'target_vibe': target_vibe
            }

            logger.info(f"✓ 主题转换成功: {theme_name}")
            logger.debug(f"  关键词: {result.get('search_keywords', [])}")
            logger.debug(f"  过滤条件: {len(result.get('filter_conditions', []))} 条")

            return result

        except Exception as e:
            logger.error(f"✗ 主题转换失败: {theme_name} - {str(e)}")
            # 返回默认结构作为兜底
            return self._get_fallback_result(
                theme_name, slogan, description, target_vibe, str(e)
            )

    def translate_from_excel(
        self,
        excel_path: str,
        status_column: str = "候选状态",
        status_value: str = "通过"
    ) -> Dict:
        """
        从 Excel 文件读取主题并批量转换

        Args:
            excel_path: Excel 文件路径
            status_column: 状态列名
            status_value: 要处理的状态值

        Returns:
            {
                "success": True/False,
                "processed": 处理数量,
                "results": [...],
                "output_file": "输出文件路径",
                "error": "错误信息"
            }
        """
        try:
            # 1. 读取 Excel
            excel_file = Path(excel_path)
            if not excel_file.exists():
                raise FileNotFoundError(f"Excel 文件不存在: {excel_path}")

            df = pd.read_excel(excel_file)
            logger.info(f"读取 Excel 成功: {len(df)} 行数据")

            # 2. 筛选候选状态为"通过"的记录
            if status_column not in df.columns:
                raise ValueError(f"Excel 中缺少列: {status_column}")

            filtered_df = df[df[status_column] == status_value].copy()
            if filtered_df.empty:
                logger.warning(f"没有候选状态为 '{status_value}' 的记录")
                return {
                    "success": True,
                    "processed": 0,
                    "results": [],
                    "output_file": None
                }

            logger.info(f"找到 {len(filtered_df)} 个待转换的主题")

            # 3. 批量转换
            results = []
            for idx, row in filtered_df.iterrows():
                theme_name = row.get('主题名称', '')
                slogan = row.get('副标题/推荐语', '')
                description = row.get('情境描述', '')
                target_vibe = row.get('预期氛围', '')

                result = self.translate_theme(
                    theme_name, slogan, description, target_vibe
                )
                results.append(result)

            # 4. 保存结果
            output_file = self._save_results(results, excel_file)

            logger.info(f"✓ 批量转换完成: {len(results)} 个主题")

            return {
                "success": True,
                "processed": len(results),
                "results": results,
                "output_file": str(output_file)
            }

        except Exception as e:
            logger.error(f"✗ 批量转换失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "processed": 0,
                "results": [],
                "error": str(e)
            }

    def translate_from_json(
        self,
        json_path: str,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        从 JSON 文件读取主题并批量转换

        Args:
            json_path: JSON 文件路径
            output_dir: 输出目录（默认与输入文件同目录）

        Returns:
            同 translate_from_excel
        """
        try:
            # 1. 读取 JSON
            json_file = Path(json_path)
            if not json_file.exists():
                raise FileNotFoundError(f"JSON 文件不存在: {json_path}")

            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            themes = data.get('themes', [])
            if not themes:
                raise ValueError("JSON 文件中没有 themes 数据")

            logger.info(f"读取 JSON 成功: {len(themes)} 个主题")

            # 2. 批量转换
            results = []
            for theme in themes:
                result = self.translate_theme(
                    theme_name=theme.get('theme_name', ''),
                    slogan=theme.get('slogan', ''),
                    description=theme.get('description', ''),
                    target_vibe=theme.get('target_vibe', '')
                )
                results.append(result)

            # 3. 保存结果
            output_file = self._save_results(results, json_file, output_dir)

            logger.info(f"✓ 批量转换完成: {len(results)} 个主题")

            return {
                "success": True,
                "processed": len(results),
                "results": results,
                "output_file": str(output_file)
            }

        except Exception as e:
            logger.error(f"✗ 批量转换失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "processed": 0,
                "results": [],
                "error": str(e)
            }

    def _load_vocabulary(self, vocabulary_file: str) -> dict:
        """加载标签词表"""
        vocab_path = Path(vocabulary_file)
        if not vocab_path.exists():
            raise FileNotFoundError(f"标签词表文件不存在: {vocabulary_file}")

        with open(vocab_path, 'r', encoding='utf-8') as f:
            vocabulary = yaml.safe_load(f)

        logger.info(f"✓ 标签词表加载成功: {vocabulary_file}")
        return vocabulary

    def _build_user_prompt(
        self,
        theme_name: str,
        slogan: str,
        description: str,
        target_vibe: str
    ) -> str:
        """
        构建用户提示词（包含词表和主题信息）

        Args:
            theme_name: 主题名称
            slogan: 副标题
            description: 情境描述
            target_vibe: 预期氛围

        Returns:
            str: 完整的用户提示词
        """
        # 1. 构建标签词表部分
        tags_section = self._build_tags_section()

        # 2. 构建主题 JSON
        theme_json = json.dumps({
            "theme_name": theme_name,
            "slogan": slogan,
            "description": description,
            "target_vibe": target_vibe
        }, ensure_ascii=False, indent=2)

        # 3. 组合用户提示词
        user_prompt = f"""# 标签词表

{tags_section}

# 待转换主题

{theme_json}

请根据以上主题，生成检索条件。"""

        return user_prompt

    def _build_tags_section(self) -> str:
        """构建标签候选词部分"""
        dimensions = self.vocabulary.get('tag_dimensions', {})
        prompt_config = self.vocabulary.get('prompt_config', {})
        include_desc = prompt_config.get('include_descriptions', True)

        # 维度名称映射
        dimension_names = {
            'reading_context': '阅读情境 (Reading Context) - 此时此刻适合读什么？',
            'reading_load': '阅读体感 (Reading Load) - 读起来累不累？',
            'text_texture': '文本质感 (Text Texture) - 文字风格如何？',
            'spatial_atmosphere': '时空氛围 (Spatial Atmosphere) - 场景与空间感',
            'emotional_tone': '情绪基调 (Emotional Tone) - 情感色彩与氛围'
        }

        sections = []

        for dim_key, dim_data in dimensions.items():
            dim_title = dimension_names.get(dim_key, dim_key)
            section_lines = [f"### {dim_title}"]
            section_lines.append("")

            for candidate in dim_data.get('candidates', []):
                label = candidate.get('label', '')
                desc = candidate.get('description', '')

                if include_desc and desc:
                    section_lines.append(f"- **{label}**: {desc}")
                else:
                    section_lines.append(f"- {label}")

            sections.append("\n".join(section_lines))

        return "\n\n".join(sections)

    def _parse_response(self, response: str) -> Dict:
        """
        解析 LLM 响应

        Args:
            response: LLM 返回的 JSON 字符串

        Returns:
            Dict: 解析后的检索条件
        """
        # UnifiedLLMClient 已启用 json_repair
        if isinstance(response, str):
            return json.loads(response)
        elif isinstance(response, dict):
            return response

        raise TypeError(f"不支持的响应类型: {type(response)}")

    def _validate_result(self, result: Dict) -> bool:
        """
        验证转换结果的有效性

        Args:
            result: 转换结果

        Returns:
            bool: 是否有效
        """
        # 检查必需字段
        required_keys = ['filter_conditions', 'search_keywords', 'synthetic_query']
        for key in required_keys:
            if key not in result:
                logger.warning(f"转换结果缺少字段: {key}")
                return False

        # 验证 filter_conditions 格式
        filters = result.get('filter_conditions', [])
        if not isinstance(filters, list):
            logger.warning("filter_conditions 必须是列表")
            return False

        for f in filters:
            if 'field' not in f or 'values' not in f or 'operator' not in f:
                logger.warning(f"过滤条件格式错误: {f}")
                return False
            if f['field'] not in self.VALID_FIELDS:
                logger.warning(f"无效的字段名: {f['field']}")
                return False
            if f['operator'] not in self.VALID_OPERATORS:
                logger.warning(f"无效的操作符: {f['operator']}")
                return False

        # 验证 search_keywords
        keywords = result.get('search_keywords', [])
        if not isinstance(keywords, list) or len(keywords) < 2:
            logger.warning("search_keywords 必须包含至少 2 个关键词")
            return False

        # 验证 synthetic_query
        query = result.get('synthetic_query', '')
        if not isinstance(query, str) or len(query.strip()) < 20:
            logger.warning("synthetic_query 必须至少 20 个字符")
            return False

        return True

    def _get_fallback_result(
        self,
        theme_name: str,
        slogan: str,
        description: str,
        target_vibe: str,
        error: str
    ) -> Dict:
        """获取失败时的兜底结果"""
        # 从描述中提取关键词作为兜底
        keywords = self._extract_keywords_from_text(description)

        return {
            "filter_conditions": [],
            "search_keywords": keywords,
            "synthetic_query": description,  # 直接使用描述作为查询
            "original_theme": {
                'theme_name': theme_name,
                'slogan': slogan,
                'description': description,
                'target_vibe': target_vibe
            },
            "error": error,
            "is_fallback": True
        }

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """从文本中简单提取关键词（兜底用）"""
        # 简单的分词和去停用词
        import re
        # 提取中文词汇
        words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        # 返回前 5 个
        return words[:5] if words else ["通用"]

    def _save_results(
        self,
        results: List[Dict],
        source_file: Path,
        output_dir: Optional[str] = None
    ) -> Path:
        """
        保存转换结果

        同时保存 JSON 和 Excel 格式：
        - JSON: 便于后续向量检索程序读取
        - Excel: 便于人工查看和调试

        Args:
            results: 转换结果列表
            source_file: 源文件路径
            output_dir: 输出目录

        Returns:
            Path: JSON 文件路径
        """
        # 确定输出目录
        if output_dir is None:
            output_path = source_file.parent
        else:
            output_path = Path(output_dir)

        output_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = source_file.stem

        # 1. 保存 JSON（推荐后续检索使用）
        json_filename = f"{base_name}_translated_{timestamp}.json"
        json_path = output_path / json_filename

        output_data = {
            "generated_at": datetime.now().isoformat(),
            "source_file": str(source_file),
            "count": len(results),
            "queries": results
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ JSON 已保存: {json_path}")

        # 2. 保存 Excel（便于人工查看）
        excel_filename = f"{base_name}_translated_{timestamp}.xlsx"
        excel_path = output_path / excel_filename

        # 展开结果为扁平结构
        flat_data = []
        for r in results:
            original = r.get('original_theme', {})
            flat_data.append({
                '主题名称': original.get('theme_name', ''),
                '副标题/推荐语': original.get('slogan', ''),
                '情境描述': original.get('description', ''),
                '预期氛围': original.get('target_vibe', ''),
                '关键词': ','.join(r.get('search_keywords', [])),
                '过滤条件数量': len(r.get('filter_conditions', [])),
                '过滤条件详情': json.dumps(
                    r.get('filter_conditions', []),
                    ensure_ascii=False
                ),
                '合成向量查询': r.get('synthetic_query', ''),
                '转换状态': '成功' if not r.get('is_fallback') else '兜底',
                '错误信息': r.get('error', '')
            })

        df = pd.DataFrame(flat_data)

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='查询条件')

            # 调整列宽
            worksheet = writer.sheets['查询条件']
            worksheet.column_dimensions['A'].width = 25  # 主题名称
            worksheet.column_dimensions['B'].width = 30  # 副标题
            worksheet.column_dimensions['C'].width = 50  # 情境描述
            worksheet.column_dimensions['D'].width = 15  # 预期氛围
            worksheet.column_dimensions['E'].width = 30  # 关键词
            worksheet.column_dimensions['F'].width = 15  # 过滤条件数量
            worksheet.column_dimensions['G'].width = 40  # 过滤条件详情
            worksheet.column_dimensions['H'].width = 60  # 合成向量查询
            worksheet.column_dimensions['I'].width = 12  # 转换状态
            worksheet.column_dimensions['J'].width = 30  # 错误信息

        logger.info(f"✓ Excel 已保存: {excel_path}")

        return json_path
