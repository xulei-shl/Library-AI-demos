"""
统一JSON处理工具

提供JSON解析、修复、验证和格式化功能，支持多种输出格式。
集成原有的json_repair功能，提供更完善的JSON处理能力。
"""

import json
import re
from typing import Optional, Dict, Any, Union, List, Tuple
from pathlib import Path

from .json_repair import repair_json_output, is_valid_json
from .logger import get_logger

logger = get_logger(__name__)


class JSONHandler:
    """统一JSON处理工具

    功能：
    1. 自动检测和修复JSON格式错误
    2. 支持多种输出格式（text/json/markdown/yaml）
    3. 智能提取JSON片段
    4. 错误处理和日志记录
    5. JSON路径提取和验证
    """

    @staticmethod
    def parse_response(
        text: str,
        enable_repair: bool = True,
        strict_mode: bool = False,
        return_raw_on_error: bool = True
    ) -> Optional[Union[Dict[str, Any], str]]:
        """解析LLM响应，支持自动修复

        处理流程：
        1. 直接尝试解析JSON
        2. 提取文本中的JSON片段
        3. 使用json_repair修复
        4. 严格模式下返回None，非严格模式下返回原文

        Args:
            text: LLM响应文本
            enable_repair: 是否启用自动修复
            strict_mode: 严格模式，修复失败时返回None
            return_raw_on_error: 非严格模式下是否返回原文

        Returns:
            解析后的JSON对象，或修复失败时的原始文本/None
        """
        if not text or not text.strip():
            logger.warning("空响应文本，无法解析JSON")
            return None

        original_text = text.strip()

        # 记录原始文本长度
        original_len = len(original_text)
        logger.debug(f"开始解析JSON | 原文长度={original_len}")

        # 步骤1: 直接尝试解析
        try:
            result = json.loads(original_text)
            logger.info("直接解析JSON成功")
            return result
        except json.JSONDecodeError:
            logger.info("直接解析失败，尝试修复")

        # 步骤2: 提取JSON片段
        extracted = JSONHandler._extract_json_from_text(original_text)
        if extracted:
            logger.info(f"提取到JSON片段 | 长度={len(extracted)}")
            text = extracted

        # 步骤3: 尝试修复
        if enable_repair:
            logger.info("使用JSON修复工具")
            try:
                # 尝试使用原生的json_repair
                result = repair_json_output(text)
                if result is not None:
                    logger.info("JSON修复成功")
                    return result
                else:
                    logger.warning("JSON修复失败")
            except Exception as e:
                logger.warning(f"JSON修复异常: {e}")

        # 步骤4: 严格模式处理
        if strict_mode:
            logger.error("严格模式下解析失败，返回None")
            return None

        # 步骤5: 非严格模式返回原文或提取的文本
        result_text = extracted if extracted else original_text
        if return_raw_on_error:
            logger.warning("返回原始文本（非严格模式）")
            return result_text
        else:
            logger.error("拒绝返回原始文本")
            return None

    @staticmethod
    def _extract_json_from_text(text: str) -> Optional[str]:
        """从文本中提取JSON片段

        支持多种提取策略：
        1. 代码块标记 ```json ... ```
        2. 花括号平衡提取JSON对象
        3. 方括号平衡提取JSON数组
        4. 寻找第一个 { 或 [

        Args:
            text: 原始文本

        Returns:
            提取的JSON片段，未找到则返回None
        """
        # 策略1: 提取代码块中的JSON
        code_block_pattern = r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
            logger.debug("从代码块中提取JSON")
            return json_str

        # 策略2: 寻找第一个 { 或 [
        start_idx = text.find('{')
        bracket_idx = text.find('[')

        # 选择最早出现的标记
        if start_idx == -1 and bracket_idx == -1:
            return None

        if bracket_idx != -1 and (start_idx == -1 or bracket_idx < start_idx):
            start_char = '['
            end_char = ']'
            start_idx = bracket_idx
        else:
            start_char = '{'
            end_char = '}'
            start_idx = start_idx

        # 使用括号平衡找到完整结构
        return JSONHandler._extract_balanced_braces(text, start_idx, start_char, end_char)

    @staticmethod
    def _extract_balanced_braces(
        text: str,
        start_idx: int,
        start_char: str,
        end_char: str
    ) -> Optional[str]:
        """提取平衡的花括号或方括号内容

        正确处理字符串中的转义字符和引号。

        Args:
            text: 原始文本
            start_idx: 开始位置
            start_char: 开始字符（{ 或 [）
            end_char: 结束字符（} 或 ]）

        Returns:
            平衡的字符串，未找到则返回None
        """
        if start_idx == -1:
            return None

        brace_count = 0
        in_string = False
        escape_next = False

        for i in range(start_idx, len(text)):
            char = text[i]

            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == start_char:
                    brace_count += 1
                elif char == end_char:
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start_idx:i+1]

        return None

    @staticmethod
    def format_output(
        data: Any,
        output_format: str = "text",
        ensure_ascii: bool = False,
        indent: int = 2
    ) -> str:
        """格式化输出

        Args:
            data: 要格式化的数据
            output_format: 输出格式 (text|json|markdown|yaml)
            ensure_ascii: JSON中是否转义非ASCII字符
            indent: JSON缩进

        Returns:
            格式化后的字符串
        """
        if output_format == "json":
            return json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
        elif output_format == "markdown":
            if isinstance(data, (dict, list)):
                return "```json\n" + json.dumps(data, ensure_ascii=ensure_ascii, indent=indent) + "\n```"
            else:
                return str(data)
        elif output_format == "yaml":
            try:
                import yaml
                return yaml.dump(data, allow_unicode=not ensure_ascii, indent=indent)
            except ImportError:
                logger.warning("YAML库未安装，回退到JSON格式")
                return json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
        else:  # text
            if isinstance(data, (dict, list)):
                return json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
            else:
                return str(data)

    @staticmethod
    def validate_json(data: Any) -> bool:
        """验证数据是否为有效JSON

        Args:
            data: 要验证的数据

        Returns:
            是否为有效JSON
        """
        try:
            json.dumps(data)
            return True
        except (TypeError, ValueError):
            return False

    @staticmethod
    def extract_json_paths(data: Dict[str, Any], prefix: str = "") -> List[str]:
        """提取JSON中的所有路径

        例如: {'a': {'b': 1}} -> ['a', 'a.b']

        Args:
            data: JSON数据
            prefix: 路径前缀（内部使用）

        Returns:
            所有路径列表
        """
        paths = []

        def _extract(obj: Any, current_prefix: str):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{current_prefix}.{key}" if current_prefix else key
                    _extract(value, new_prefix)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_prefix = f"{current_prefix}[{i}]"
                    _extract(item, new_prefix)
            else:
                paths.append(current_prefix)

        _extract(data, prefix)
        return paths

    @staticmethod
    def get_json_value(data: Dict[str, Any], path: str) -> Any:
        """根据路径获取JSON值

        Args:
            data: JSON数据
            path: 路径，如 "a.b[0].c"

        Returns:
            对应的值，不存在则返回None
        """
        try:
            keys = []
            # 解析路径
            for part in re.finditer(r'(\w+)|\[(\d+)\]', path):
                if part.group(1):
                    keys.append(part.group(1))
                else:
                    keys.append(int(part.group(2)))

            # 获取值
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                elif isinstance(value, list) and isinstance(key, int) and 0 <= key < len(value):
                    value = value[key]
                else:
                    return None

            return value
        except Exception:
            return None

    @staticmethod
    def set_json_value(data: Dict[str, Any], path: str, value: Any) -> bool:
        """根据路径设置JSON值

        Args:
            data: JSON数据（将被修改）
            path: 路径，如 "a.b[0].c"
            value: 要设置的值

        Returns:
            是否设置成功
        """
        try:
            keys = []
            parts = re.finditer(r'(\w+)|\[(\d+)\]', path)

            for part in parts:
                if part.group(1):
                    keys.append(part.group(1))
                else:
                    keys.append(int(part.group(2)))

            # 导航到目标位置
            current = data
            for key in keys[:-1]:
                if isinstance(key, str):
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                else:  # int
                    if not isinstance(current, list):
                        return False
                    while len(current) <= key:
                        current.append({})
                    current = current[key]

            # 设置值
            last_key = keys[-1]
            if isinstance(last_key, str):
                current[last_key] = value
            else:
                if not isinstance(current, list):
                    return False
                while len(current) <= last_key:
                    current.append(None)
                current[last_key] = value

            return True
        except Exception:
            return False

    @staticmethod
    def merge_json(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """合并两个JSON对象

        Args:
            base: 基础JSON对象
            update: 更新JSON对象

        Returns:
            合并后的JSON对象
        """
        result = base.copy()

        def _merge(base_obj: dict, update_obj: dict):
            for key, value in update_obj.items():
                if key in base_obj and isinstance(base_obj[key], dict) and isinstance(value, dict):
                    _merge(base_obj[key], value)
                else:
                    base_obj[key] = value

        _merge(result, update)
        return result

    @staticmethod
    def find_json_in_files(file_paths: List[str]) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
        """从多个文件中查找并解析JSON

        Args:
            file_paths: 文件路径列表

        Returns:
            (文件路径, JSON对象) 的列表，解析失败时JSON对象为None
        """
        results = []

        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"文件不存在: {path}")
                results.append((file_path, None))
                continue

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                json_obj = JSONHandler.parse_response(
                    content,
                    enable_repair=True,
                    strict_mode=False
                )

                results.append((file_path, json_obj))
                logger.info(f"成功解析文件: {path}")
            except Exception as e:
                logger.error(f"解析文件失败: {path}, 错误: {e}")
                results.append((file_path, None))

        return results