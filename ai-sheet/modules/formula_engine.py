"""
公式行号调整器
专注于处理Excel公式中的单元格引用行号调整
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class FormulaRowAdjuster:
    """公式行号调整器 - 处理公式中的行号引用"""
    
    def __init__(self):
        # 单元格引用模式：匹配 $A$1, A1, $A1, A$1 等格式
        self.cell_pattern = re.compile(r'(\$?)([A-Z]+)(\$?)(\d+)')
        # 范围引用模式：匹配 A1:B10, $A$1:$B$10 等格式
        self.range_pattern = re.compile(r'(\$?[A-Z]+\$?\d+):(\$?[A-Z]+\$?\d+)')
        # 字符串字面量模式：避免处理字符串内的内容
        self.string_pattern = re.compile(r'"[^"]*"')
    
    def adjust_formula_for_row(self, formula: str, target_row: int) -> str:
        """
        将公式调整到指定行
        
        Args:
            formula: 原始公式，如 "=H2" 或 "=SUM(H2:H10)"
            target_row: 目标行号（1-based，对应Excel行号）
            
        Returns:
            调整后的公式
            
        Examples:
            adjust_formula_for_row("=H2", 3) -> "=H3"
            adjust_formula_for_row("=SUM(H2:H10)", 5) -> "=SUM(H5:H13)"
            adjust_formula_for_row("=$H$2", 10) -> "=$H$2" (绝对引用不变)
        """
        if not formula or target_row < 1:
            return formula
        
        logger.debug(f"调整公式 '{formula}' 到第 {target_row} 行")
        
        # 去掉开头的=号
        formula_body = formula.lstrip('=')
        
        # 保护字符串字面量
        string_literals = []
        def replace_string_literal(match):
            string_literals.append(match.group(0))
            return f"__STRING_LITERAL_{len(string_literals)-1}__"
        
        # 临时替换字符串字面量
        protected_formula = self.string_pattern.sub(replace_string_literal, formula_body)
        
        # 先处理范围引用，再处理单个单元格引用
        adjusted_formula = self._adjust_range_references(protected_formula, target_row)
        adjusted_formula = self._adjust_cell_references(adjusted_formula, target_row)
        
        # 恢复字符串字面量
        for i, literal in enumerate(string_literals):
            adjusted_formula = adjusted_formula.replace(f"__STRING_LITERAL_{i}__", literal)
        
        # 重新添加=号
        result = f"={adjusted_formula}"
        
        logger.debug(f"调整结果: '{result}'")
        return result
    
    def _adjust_range_references(self, formula: str, target_row: int) -> str:
        """调整范围引用中的行号"""
        def adjust_range(match):
            start_cell = match.group(1)
            end_cell = match.group(2)
            
            adjusted_start = self._adjust_single_cell(start_cell, target_row)
            adjusted_end = self._adjust_single_cell(end_cell, target_row)
            
            return f"{adjusted_start}:{adjusted_end}"
        
        return self.range_pattern.sub(adjust_range, formula)
    
    def _adjust_cell_references(self, formula: str, target_row: int) -> str:
        """调整单个单元格引用中的行号"""
        def adjust_cell(match):
            return self._adjust_single_cell(match.group(0), target_row)
        
        return self.cell_pattern.sub(adjust_cell, formula)
    
    def _adjust_single_cell(self, cell_ref: str, target_row: int) -> str:
        """
        调整单个单元格引用
        
        规则说明：
        - H2 -> 相对引用，根据目标行调整 (H2在第2行，目标第3行 -> H3)
        - $H2 -> 绝对列引用，行号仍需调整
        - H$2 -> 绝对行引用，行号不变
        - $H$2 -> 完全绝对引用，都不变
        
        Args:
            cell_ref: 单元格引用，如 "H2", "$H2", "H$2", "$H$2"
            target_row: 目标行号
            
        Returns:
            调整后的单元格引用
        """
        match = self.cell_pattern.match(cell_ref)
        if not match:
            return cell_ref
        
        col_abs, col, row_abs, row_num = match.groups()
        
        # 如果行号是绝对引用($)，不调整
        if row_abs == '$':
            logger.debug(f"绝对行引用 '{cell_ref}' 不调整")
            return cell_ref
        
        # 相对引用需要调整
        original_row = int(row_num)
        
        # 计算行号偏移：假设原公式是基于第2行设计的
        # 如果用户输入 =H2，意思是引用当前行的H列
        # 那么在第3行就应该是 =H3，在第4行就是 =H4
        base_row = 2  # 假设原始公式基于第2行（第一行数据）
        offset = target_row - base_row
        new_row = original_row + offset
        
        # 确保行号不小于1
        new_row = max(1, new_row)
        
        result = f"{col_abs}{col}{row_abs}{new_row}"
        logger.debug(f"相对引用调整: '{cell_ref}' -> '{result}' (原始行:{original_row}, 目标行:{target_row}, 偏移:{offset})")
        
        return result
    
    def validate_formula_syntax(self, formula: str) -> Tuple[bool, str]:
        """
        简单的公式语法验证
        
        Args:
            formula: 要验证的公式
            
        Returns:
            (是否有效, 验证消息)
        """
        try:
            if not formula or not formula.strip():
                return False, "公式不能为空"
            
            # 简单检查：应该以=开头
            if not formula.strip().startswith('='):
                return False, "公式应该以 '=' 开头"
            
            # 检查是否包含基本的单元格引用模式
            formula_body = formula.lstrip('=')
            if not (self.cell_pattern.search(formula_body) or self.range_pattern.search(formula_body)):
                logger.warning(f"公式 '{formula}' 中未检测到单元格引用，可能是常量公式")
            
            return True, "语法验证通过"
            
        except Exception as e:
            return False, f"语法验证异常: {str(e)}"
    
    def get_referenced_cells(self, formula: str) -> list:
        """
        获取公式中引用的所有单元格
        
        Args:
            formula: Excel公式
            
        Returns:
            引用的单元格列表
        """
        cells = []
        
        if not formula:
            return cells
        
        formula_body = formula.lstrip('=')
        
        # 查找所有单元格引用
        for match in self.cell_pattern.finditer(formula_body):
            cells.append(match.group(0))
        
        # 查找所有范围引用
        for match in self.range_pattern.finditer(formula_body):
            cells.append(match.group(0))
        
        return list(set(cells))  # 去重


# 创建全局实例，方便直接使用
default_adjuster = FormulaRowAdjuster()


def adjust_formula_for_row(formula: str, target_row: int) -> str:
    """
    便捷函数：调整公式到指定行
    
    Args:
        formula: 原始公式
        target_row: 目标行号
        
    Returns:
        调整后的公式
    """
    return default_adjuster.adjust_formula_for_row(formula, target_row)


def validate_formula_syntax(formula: str) -> Tuple[bool, str]:
    """
    便捷函数：验证公式语法
    
    Args:
        formula: 要验证的公式
        
    Returns:
        (是否有效, 验证消息)
    """
    return default_adjuster.validate_formula_syntax(formula)


# 示例用法和测试
if __name__ == "__main__":
    adjuster = FormulaRowAdjuster()
    
    # 测试用例
    test_cases = [
        ("=H2", 3, "=H3"),
        ("=H2", 10, "=H10"),
        ("=SUM(H2:H10)", 5, "=SUM(H5:H13)"),
        ("=$H$2", 10, "=$H$2"),
        ("=H$2", 10, "=H$2"),
        ("=$H2", 5, "=$H5"),
        ("=H2+I2*2", 4, "=H4+I4*2"),
        ("=IF(A2>0,B2,C2)", 6, "=IF(A6>0,B6,C6)"),
    ]
    
    print("公式行号调整测试：")
    for formula, target_row, expected in test_cases:
        result = adjuster.adjust_formula_for_row(formula, target_row)
        status = "✓" if result == expected else "✗"
        print(f"{status} {formula} -> 第{target_row}行 -> {result} (期望: {expected})")