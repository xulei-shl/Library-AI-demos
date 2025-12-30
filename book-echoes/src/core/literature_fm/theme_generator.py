"""
文学策划主题生成器
负责调用 LLM 生成创意阅读主题
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient

logger = get_logger(__name__)


class ThemeGenerator:
    """文学策划主题生成器"""

    def __init__(self, config: dict = None):
        """
        初始化生成器

        Args:
            config: 配置字典（从 literature_fm.yaml 读取）
        """
        self.config = config or {}
        self.llm_client = UnifiedLLMClient()

    def generate_themes(
        self,
        direction: str = "",
        count: int = 5
    ) -> Dict:
        """
        生成主题列表

        Args:
            direction: 策划方向/关键词（空字符串表示随机生成）
            count: 生成主题数量

        Returns:
            {
                "success": True/False,
                "themes": [...],
                "output_file": "路径",
                "error": "错误信息",
                "count": 生成数量
            }
        """
        try:
            # 1. 构建用户提示词
            user_prompt = self._build_user_prompt(direction, count)

            # 2. 调用 LLM
            logger.info(f"正在调用 LLM 生成主题，方向: {direction or '随机'}, 数量: {count}")
            response = self.llm_client.call(
                task_name='literary_theme_generation',
                user_prompt=user_prompt
            )

            # 3. 解析响应（JSON 列表）
            themes = self._parse_response(response)

            # 4. 验证主题数据
            if not self._validate_themes(themes):
                raise ValueError("主题数据验证失败")

            # 5. 保存到 JSON 和 Excel 文件
            output_file = self._save_themes(themes, direction)

            logger.info(f"✓ 主题生成成功: {len(themes)} 个主题")

            return {
                "success": True,
                "themes": themes,
                "output_file": output_file,
                "count": len(themes)
            }

        except Exception as e:
            logger.error(f"✗ 主题生成失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "themes": [],
                "error": str(e),
                "count": 0
            }

    def _build_user_prompt(self, direction: str, count: int) -> str:
        """
        构建用户提示词

        Args:
            direction: 策划方向/关键词
            count: 生成数量

        Returns:
            str: 完整的用户提示词
        """
        # 构建多个对象的示例
        example_count = min(3, count)
        examples = []
        for idx in range(example_count):
            examples.append(f'''  {{
    "theme_name": "示例主题{idx+1}",
    "slogan": "示例副标题{idx+1}",
    "description": "示例情境描述{idx+1}",
    "target_vibe": "示例氛围{idx+1}"
  }}''')

        example_items = ",\n".join(examples)

        if direction:
            return f"""请根据策划方向「{direction}」生成 {count} 个阅读主题。

# Output Format

请严格遵守以下 JSON 格式，不要包含任何 Markdown 代码块标记（如 ```json），直接输出纯文本 JSON 列表（必须包含 {count} 个对象）：

[
{example_items}
]

请确保主题具有创意性和吸引力，能够激发读者的阅读兴趣。"""
        else:
            return f"""请随机生成 {count} 个创意阅读主题，覆盖不同的季节、情绪、生活场景。

# Output Format

请严格遵守以下 JSON 格式，不要包含任何 Markdown 代码块标记（如 ```json），直接输出纯文本 JSON 列表（必须包含 {count} 个对象）：

[
{example_items}
]

请确保主题具有多样性和创意性，能够覆盖不同的阅读情境和情绪状态。"""

    def _parse_response(self, response) -> List[Dict]:
        """
        解析 LLM 响应

        Args:
            response: LLM 返回的 JSON 字符串或字典

        Returns:
            List[Dict]: 解析后的主题列表
        """
        # UnifiedLLMClient 已启用 json_repair，这里直接解析
        if isinstance(response, str):
            data = json.loads(response)
        else:
            data = response

        # 处理 LLM 返回单个对象而非数组的情况（兼容性处理）
        if isinstance(data, dict):
            logger.warning("LLM 返回单个对象而非数组，已转换为单元素数组")
            return [data]

        return data

    def _validate_themes(self, themes: List[Dict]) -> bool:
        """
        验证主题数据完整性

        Args:
            themes: 主题列表

        Returns:
            bool: 是否有效
        """
        required_keys = ['theme_name', 'slogan', 'description', 'target_vibe']

        if not isinstance(themes, list):
            logger.error(f"响应不是列表类型，实际类型: {type(themes)}")
            return False

        if len(themes) == 0:
            logger.error("主题列表为空")
            return False

        for i, theme in enumerate(themes):
            if not all(key in theme for key in required_keys):
                logger.error(f"主题 {i+1} 缺少必需字段: {theme}")
                return False

        return True

    def _save_themes(
        self,
        themes: List[Dict],
        direction: str
    ) -> str:
        """
        保存主题到 JSON 和 Excel 文件

        Args:
            themes: 主题列表
            direction: 策划方向

        Returns:
            str: JSON 文件路径
        """
        # 获取输出目录配置
        output_config = self.config.get('output', {})
        output_dir = Path(output_config.get(
            'output_dir',
            'runtime/outputs/theme_shelf'
        ))
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名（包含时间戳和方向摘要）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        direction_suffix = direction[:10] if direction else 'random'
        # 清理文件名中的特殊字符
        direction_suffix = direction_suffix.replace('/', '_').replace('\\', '_').replace(':', '_')

        # 保存 JSON 文件
        json_filename = f"themes_{timestamp}_{direction_suffix}.json"
        json_path = output_dir / json_filename

        output_data = {
            "generated_at": datetime.now().isoformat(),
            "direction": direction,
            "count": len(themes),
            "themes": themes
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ JSON 已保存: {json_path}")

        # 保存 Excel 文件
        excel_filename = f"themes_{timestamp}_{direction_suffix}.xlsx"
        excel_path = output_dir / excel_filename

        # 转换为 DataFrame
        df = pd.DataFrame(themes)

        # 新增候选状态列（空值）
        df['候选状态'] = ''

        # 设置列名（中文）
        df.columns = ['主题名称', '副标题/推荐语', '情境描述', '预期氛围', '候选状态']

        # 保存 Excel（禁用索引）
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='阅读主题')

            # 调整列宽
            worksheet = writer.sheets['阅读主题']
            worksheet.column_dimensions['A'].width = 25  # 主题名称
            worksheet.column_dimensions['B'].width = 30  # 副标题
            worksheet.column_dimensions['C'].width = 50  # 情境描述
            worksheet.column_dimensions['D'].width = 15  # 预期氛围
            worksheet.column_dimensions['E'].width = 12  # 候选状态

        logger.info(f"✓ Excel 已保存: {excel_path}")

        return str(json_path)
