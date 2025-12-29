"""
文学策划主题生成器
负责调用 LLM 生成创意阅读主题
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

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

            # 5. 保存到 JSON 文件
            output_file = self._save_to_json(themes, direction)

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
        if direction:
            return f"""请根据策划方向「{direction}」生成 {count} 个阅读主题。

# Output Format

请严格遵守以下 JSON 格式，不要包含任何 Markdown 代码块标记（如 ```json），直接输出纯文本 JSON 列表：

[
  {{
    "theme_name": "主题名称",
    "slogan": "副标题/推荐语",
    "description": "情境描述",
    "target_vibe": "预期氛围"
  }}
]

请确保主题具有创意性和吸引力，能够激发读者的阅读兴趣。"""
        else:
            return f"""请随机生成 {count} 个创意阅读主题，覆盖不同的季节、情绪、生活场景。

# Output Format

请严格遵守以下 JSON 格式，不要包含任何 Markdown 代码块标记（如 ```json），直接输出纯文本 JSON 列表：

[
  {{
    "theme_name": "主题名称",
    "slogan": "副标题/推荐语",
    "description": "情境描述",
    "target_vibe": "预期氛围"
  }}
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
            return json.loads(response)
        return response

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
            logger.error("响应不是列表类型")
            return False

        if len(themes) == 0:
            logger.error("主题列表为空")
            return False

        for i, theme in enumerate(themes):
            if not all(key in theme for key in required_keys):
                logger.error(f"主题 {i+1} 缺少必需字段: {theme}")
                return False

        return True

    def _save_to_json(
        self,
        themes: List[Dict],
        direction: str
    ) -> str:
        """
        保存主题到 JSON 文件

        Args:
            themes: 主题列表
            direction: 策划方向

        Returns:
            str: 输出文件路径
        """
        # 获取输出目录配置
        output_config = self.config.get('output', {})
        output_dir = Path(output_config.get(
            'output_dir',
            'runtime/outputs/literary_theme_generation'
        ))
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名（包含时间戳和方向摘要）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        direction_suffix = direction[:10] if direction else 'random'
        # 清理文件名中的特殊字符
        direction_suffix = direction_suffix.replace('/', '_').replace('\\', '_').replace(':', '_')
        filename = f"themes_{timestamp}_{direction_suffix}.json"
        output_path = output_dir / filename

        # 保存文件（添加元数据）
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "direction": direction,
            "count": len(themes),
            "themes": themes
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ 主题已保存: {output_path}")
        return str(output_path)
