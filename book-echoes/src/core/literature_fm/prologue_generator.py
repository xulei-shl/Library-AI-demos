"""
卷首导读生成器
负责从 Excel 中提取人工评选通过的图书，调用 LLM 生成文学导读
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)


class PrologueGenerator:
    """卷首导读生成器"""

    def __init__(self, config: dict):
        """
        Args:
            config: literature_fm.yaml 中的 prologue_filter 配置节
        """
        self.config = config
        self.llm_client = UnifiedLLMClient()
        self.excluded_sheets = config.get('excluded_sheets', ['主题汇总', '元信息'])
        self.excel_fields = config.get('excel_fields', {})
        self.approval_value = config.get('approval_value', '通过')
        self.approval_column = config.get('approval_column', '人工评选')

    def generate_from_excel(self, excel_path: str) -> dict:
        """
        从 Excel 文件生成卷首导读

        Args:
            excel_path: Excel 文件路径

        Returns:
            {
                'success': True/False,
                'book_count': 图书数量,
                'output_file': '输出md文件路径',
                'error': '错误信息'
            }
        """
        try:
            # 1. 读取主题信息
            theme_info = self._read_theme_info(excel_path)
            if not theme_info:
                return {
                    'success': False,
                    'error': '未能读取到主题汇总信息，请确认 Excel 中存在「主题汇总」sheet'
                }

            logger.info(f"✓ 读取主题信息: {theme_info.get('theme_name', '')}")

            # 2. 读取人工评选通过的图书
            approved_books = self._read_approved_books(excel_path)
            if not approved_books:
                return {
                    'success': False,
                    'error': f'未找到「{self.approval_column}」列为「{self.approval_value}」的图书'
                }

            logger.info(f"✓ 读取到 {len(approved_books)} 本人工评选通过的图书")

            # 3. 构建用户提示词
            user_prompt = self._build_user_prompt(theme_info, approved_books)

            # 4. 调用 LLM 生成导读
            logger.info("✓ 正在调用 LLM 生成卷首导读...")
            prologue_content = self._call_llm_generate(user_prompt)

            # 5. 保存到 Markdown 文件
            output_file = self._save_to_markdown(
                prologue_content,
                excel_path,
                theme_info.get('theme_name', '')
            )

            return {
                'success': True,
                'book_count': len(approved_books),
                'output_file': output_file
            }

        except Exception as e:
            logger.error(f"卷首导读生成异常: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _read_theme_info(self, excel_path: str) -> dict:
        """
        从 '主题汇总' sheet 提取主题信息

        Returns:
            {
                'theme_name': 'xxx',
                'slogan': 'xxx',
                'description': 'xxx',
                'target_vibe': 'xxx'
            }
        """
        try:
            df = pd.read_excel(excel_path, sheet_name='主题汇总')

            if df.empty:
                return {}

            # 取第一行数据
            row = df.iloc[0]

            field_mapping = self.excel_fields.get('theme_summary', {})

            return {
                'theme_name': row.get(field_mapping.get('theme_name', '主题名称'), ''),
                'slogan': row.get(field_mapping.get('slogan', '副标题'), ''),
                'description': row.get(field_mapping.get('description', '情境描述'), ''),
                'target_vibe': row.get(field_mapping.get('target_vibe', '预期氛围'), '')
            }

        except Exception as e:
            logger.warning(f"读取主题汇总失败: {e}")
            return {}

    def _read_approved_books(self, excel_path: str) -> List[Dict]:
        """
        读取所有 sheet 中人工评选通过的图书

        Returns:
            List[Dict]: 通过评选的图书列表
        """
        try:
            xls = pd.ExcelFile(excel_path)
            all_sheets = xls.sheet_names

            # 过滤排除的sheet
            candidate_sheets = [s for s in all_sheets if s not in self.excluded_sheets]

            approved_books = []
            book_fields = self.excel_fields.get('book_fields', [])

            for sheet_name in candidate_sheets:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)

                # 检查是否存在评选列
                if self.approval_column not in df.columns:
                    logger.warning(f"Sheet '{sheet_name}' 中不存在 '{self.approval_column}' 列，跳过")
                    continue

                # 筛选通过的图书
                approved_df = df[df[self.approval_column] == self.approval_value]

                for _, row in approved_df.iterrows():
                    book_data = {}
                    for field in book_fields:
                        book_data[field] = row.get(field, '')
                    approved_books.append(book_data)

            return approved_books

        except Exception as e:
            logger.error(f"读取候选图书失败: {e}", exc_info=True)
            return []

    def _build_user_prompt(self, theme: dict, books: List[Dict]) -> str:
        """
        构建用户提示词（主题信息 + 图书列表）
        """
        # 主题信息
        theme_part = f"""# Target Theme（策划主题）
主题名称：{theme.get('theme_name', '')}
副标题：{theme.get('slogan', '')}
情境描述：{theme.get('description', '')}
预期氛围：{theme.get('target_vibe', '')}
"""

        # 图书列表（JSON格式）
        book_fields = self.excel_fields.get('book_fields', [])
        books_json = []
        for idx, book in enumerate(books, 1):
            book_data = {"序号": idx}
            for field in book_fields:
                book_data[field] = book.get(field, '')
            books_json.append(book_data)

        books_part = "\n# Reference Books（参考书目）\n" + json.dumps(
            books_json, ensure_ascii=False, indent=2
        )

        return theme_part + "\n" + books_part

    def _call_llm_generate(self, user_prompt: str) -> str:
        """
        调用 LLM 生成卷首导读

        Args:
            user_prompt: 用户提示词

        Returns:
            str: LLM 返回的导读内容
        """
        try:
            task_name = self.config.get('llm', {}).get('task_name', 'literary_writer')
            response = self.llm_client.call(
                task_name=task_name,
                user_prompt=user_prompt
            )

            # 直接返回文本内容（无需解析JSON）
            return response

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}", exc_info=True)
            raise

    def _save_to_markdown(self, content: str, excel_path: str, theme_name: str) -> str:
        """
        将导读内容保存为 Markdown 文件

        Args:
            content: 导读内容
            excel_path: Excel 文件路径
            theme_name: 主题名称

        Returns:
            str: 输出文件路径
        """
        # 构建输出文件路径
        excel_path_obj = Path(excel_path)
        output_dir = excel_path_obj.parent

        # 清理主题名称中的非法字符
        safe_theme_name = theme_name.replace('/', '-').replace('\\', '-').replace(':', '-')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"卷首导读_{safe_theme_name}_{timestamp}.md"

        output_path = output_dir / filename

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"✓ 卷首导读已保存: {output_path}")
        return str(output_path)
