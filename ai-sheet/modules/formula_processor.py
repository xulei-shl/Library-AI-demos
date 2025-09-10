"""
公式处理核心引擎 - 简化版
专注于将公式填入Excel单元格，正确处理行号引用
"""

import logging
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import time
import re
from pathlib import Path

try:
    from .excel_formula_reader import ExcelFormulaReader
    from .formula_engine import FormulaRowAdjuster
except ImportError:
    from excel_formula_reader import ExcelFormulaReader
    from formula_engine import FormulaRowAdjuster

# 配置日志
logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """处理状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"

class ErrorStrategy(Enum):
    """错误处理策略"""
    SKIP = "skip"          # 跳过错误行
    DEFAULT = "default"    # 使用默认值
    STOP = "stop"          # 停止处理
    RETRY = "retry"        # 重试处理

@dataclass
class ProcessingConfig:
    """处理配置"""
    preview_rows: int = 10
    batch_size: int = 1000
    error_strategy: ErrorStrategy = ErrorStrategy.SKIP
    backup_enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300
    memory_limit_mb: int = 512


@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool
    total_rows: int
    processed_rows: int
    success_rows: int
    error_rows: int
    errors: List[Dict[str, Any]]
    execution_time: float
    result_data: Optional[pd.DataFrame] = None


@dataclass
class ProgressInfo:
    """进度信息"""
    current_row: int
    total_rows: int
    success_count: int
    error_count: int
    progress_percent: float
    processing_speed: float  # 行/秒
    estimated_remaining: float  # 秒


class FormulaProcessor:
    """公式处理核心引擎 - 简化版"""
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        self.excel_reader = ExcelFormulaReader()
        self.row_adjuster = FormulaRowAdjuster()
        
        # 状态管理
        self.status = ProcessingStatus.IDLE
        self.current_task = None
        self.stop_requested = False
        self.pause_requested = False
        
        # 进度回调
        self.progress_callback: Optional[Callable[[ProgressInfo], None]] = None
        self.log_callback: Optional[Callable[[str, str], None]] = None  # (level, message)
        
        # 处理统计
        self.processing_stats = {
            'start_time': None,
            'total_rows': 0,
            'processed_rows': 0,
            'success_rows': 0,
            'error_rows': 0,
            'errors': []
        }
        
        logger.info("公式处理器初始化完成")
    
    def set_progress_callback(self, callback: Callable[[ProgressInfo], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_log_callback(self, callback: Callable[[str, str], None]):
        """设置日志回调函数"""
        self.log_callback = callback
    
    def _log(self, level: str, message: str):
        """内部日志方法"""
        logger.log(getattr(logging, level.upper()), message)
        if self.log_callback:
            self.log_callback(level, message)
    
    def _update_progress(self):
        """更新进度信息"""
        if not self.progress_callback or not self.processing_stats['start_time']:
            return
        
        elapsed_time = time.time() - self.processing_stats['start_time']
        processed = self.processing_stats['processed_rows']
        total = self.processing_stats['total_rows']
        
        if processed > 0 and elapsed_time > 0:
            speed = processed / elapsed_time
            remaining_rows = total - processed
            estimated_remaining = remaining_rows / speed if speed > 0 else 0
        else:
            speed = 0
            estimated_remaining = 0
        
        progress_info = ProgressInfo(
            current_row=processed,
            total_rows=total,
            success_count=self.processing_stats['success_rows'],
            error_count=self.processing_stats['error_rows'],
            progress_percent=(processed / total * 100) if total > 0 else 0,
            processing_speed=speed,
            estimated_remaining=estimated_remaining
        )
        
        self.progress_callback(progress_info)
    
    def validate_formula(self, formula: str) -> Tuple[bool, str]:
        """验证公式语法"""
        try:
            self._log("info", f"验证公式: {formula}")
            is_valid, message = self.row_adjuster.validate_formula_syntax(formula)
            
            if is_valid:
                self._log("info", "公式语法验证通过")
            else:
                self._log("warning", f"公式语法验证失败: {message}")
            
            return is_valid, message
            
        except Exception as e:
            error_msg = f"公式验证异常: {str(e)}"
            self._log("warning", error_msg)
            return False, error_msg
    
    def preview_processing(self, file_path: str, formula: str, target_column: str, 
                        sheet_name: Optional[str] = None) -> ProcessingResult:
        """预处理功能 - 处理前N行样本数据"""
        try:
            self._log("info", f"开始预处理: {file_path}")
            self.status = ProcessingStatus.RUNNING
            start_time = time.time()
            
            # 验证公式语法（记录日志但不阻断）
            is_valid, validation_msg = self.validate_formula(formula)
            if not is_valid:
                self._log("warning", f"公式验证失败但继续处理: {validation_msg}")
            
            # 读取样本数据
            self._log("info", f"读取前 {self.config.preview_rows} 行数据")
            data = self.excel_reader.read_sample_data(
                file_path, 
                max_rows=self.config.preview_rows,
                sheet_name=sheet_name
            )
            
            if data is None or data.empty:
                return ProcessingResult(
                    success=False,
                    total_rows=0,
                    processed_rows=0,
                    success_rows=0,
                    error_rows=0,
                    errors=[{"row": 0, "error": "无法读取数据或数据为空"}],
                    execution_time=0
                )
            
            # 初始化统计
            self.processing_stats.update({
                'start_time': start_time,
                'total_rows': len(data),
                'processed_rows': 0,
                'success_rows': 0,
                'error_rows': 0,
                'errors': []
            })
                        
            # 生成公式列
            formulas = []
            success_count = 0
            error_count = 0
            
            for i, row_idx in enumerate(data.index):
                try:
                    # 计算实际Excel行号（假设数据从第2行开始，第1行是表头）
                    excel_row = i + 2
                    adjusted_formula = self.row_adjuster.adjust_formula_for_row(formula, excel_row)
                    formulas.append(adjusted_formula)
                    success_count += 1
                    
                    # 更新进度
                    self.processing_stats['processed_rows'] = i + 1
                    self.processing_stats['success_rows'] = success_count
                    self.processing_stats['error_rows'] = error_count
                    self._update_progress()
                    
                except Exception as e:
                    error_msg = f"处理行 {i+2} 失败: {str(e)}"
                    self._log("warning", error_msg)
                    formulas.append("")
                    error_count += 1
                    self.processing_stats['errors'].append({
                        "row": i + 2,
                        "error": str(e)
                    })
                    
                    # 更新进度
                    self.processing_stats['processed_rows'] = i + 1
                    self.processing_stats['success_rows'] = success_count
                    self.processing_stats['error_rows'] = error_count
                    self._update_progress()
            
            # 添加公式列到数据中
            data[target_column] = formulas
            
            execution_time = time.time() - start_time
            self._log("info", f"预处理完成，成功 {success_count} 个，失败 {error_count} 个")
            
            return ProcessingResult(
                success=True,
                total_rows=len(data),
                processed_rows=len(data),
                success_rows=success_count,
                error_rows=error_count,
                errors=self.processing_stats['errors'],
                execution_time=execution_time,
                result_data=data
            )
                
        except Exception as e:
            error_msg = f"预处理异常: {str(e)}"
            self._log("error", error_msg)
            return ProcessingResult(
                success=False,
                total_rows=0,
                processed_rows=0,
                success_rows=0,
                error_rows=0,
                errors=[{"row": 0, "error": error_msg}],
                execution_time=time.time() - start_time if 'start_time' in locals() else 0
            )
        finally:
            self.status = ProcessingStatus.IDLE
    
    def process_full_file(self, file_path: str, formula: str, target_column: str,
                        sheet_name: Optional[str] = None, 
                        overwrite_strategy: str = "overwrite") -> ProcessingResult:
        """全量处理功能 - 处理整个文件"""
        try:
            self._log("info", f"开始全量处理: {file_path}")
            self.status = ProcessingStatus.RUNNING
            self.stop_requested = False
            self.pause_requested = False
            start_time = time.time()
            
            # 验证公式语法（记录日志但不阻断）
            is_valid, validation_msg = self.validate_formula(formula)
            if not is_valid:
                self._log("warning", f"公式验证失败但继续处理: {validation_msg}")
            
            # 备份原文件
            if self.config.backup_enabled:
                self._log("info", "创建文件备份")
                backup_path = self._create_backup(file_path)
                if backup_path:
                    self._log("info", f"备份文件: {backup_path}")
            
            # 获取文件信息
            file_info = self.excel_reader.get_file_info(file_path, sheet_name)
            total_rows = file_info.get('total_rows', 0)
            
            if total_rows <= 1:  # 只有表头或空文件
                return ProcessingResult(
                    success=False,
                    total_rows=0,
                    processed_rows=0,
                    success_rows=0,
                    error_rows=0,
                    errors=[{"row": 0, "error": "文件为空或只有表头"}],
                    execution_time=0
                )
            
            data_rows = total_rows - 1  # 减去表头行
            self._log("info", f"开始处理 {data_rows} 行数据（不含表头）")
            
            # 初始化统计
            self.processing_stats.update({
                'start_time': start_time,
                'total_rows': data_rows,
                'processed_rows': 0,
                'success_rows': 0,
                'error_rows': 0,
                'errors': []
            })
            
            # 检查是否需要保留现有公式
            preserve_existing_formulas = True  # 默认保留现有公式
            
            # 只生成目标列的公式数据
            self._log("info", f"生成目标列 '{target_column}' 的公式")
            
            success_count = 0
            error_count = 0
            formulas = []
            
            # 为每一行数据生成公式
            for row_idx in range(1, total_rows):  # 从第2行开始（Excel中的行号）
                try:
                    excel_row = row_idx + 1  # Excel行号
                    adjusted_formula = self.row_adjuster.adjust_formula_for_row(formula, excel_row)
                    formulas.append(adjusted_formula)
                    success_count += 1
                    
                    # 更新进度
                    self.processing_stats['processed_rows'] = row_idx
                    self.processing_stats['success_rows'] = success_count
                    self.processing_stats['error_rows'] = error_count
                    self._update_progress()
                    
                    # 检查停止和暂停请求
                    if self.stop_requested:
                        self._log("warning", "用户请求停止处理")
                        break
                    
                    while self.pause_requested and not self.stop_requested:
                        self.status = ProcessingStatus.PAUSED
                        time.sleep(0.1)
                    
                except Exception as e:
                    self._log("warning", f"处理行 {excel_row} 失败: {str(e)}")
                    formulas.append("")  # 使用空值作为错误标记
                    error_count += 1
                    self.processing_stats['errors'].append({
                        "row": excel_row,
                        "error": str(e)
                    })
                    
                    # 更新进度
                    self.processing_stats['processed_rows'] = row_idx
                    self.processing_stats['success_rows'] = success_count
                    self.processing_stats['error_rows'] = error_count
                    self._update_progress()
            
            if self.stop_requested:
                # 处理被中断
                execution_time = time.time() - start_time
                self._log("warning", "处理被用户中断")
                self.status = ProcessingStatus.STOPPED
                return ProcessingResult(
                    success=False,
                    total_rows=data_rows,
                    processed_rows=self.processing_stats['processed_rows'],
                    success_rows=self.processing_stats['success_rows'],
                    error_rows=self.processing_stats['error_rows'],
                    errors=self.processing_stats['errors'],
                    execution_time=execution_time
                )
            
            # 创建只包含目标列的DataFrame
            formula_data = pd.DataFrame({target_column: formulas})
            
            # 使用保护现有公式的方法保存数据
            if preserve_existing_formulas and overwrite_strategy == "overwrite":
                # 修改策略为添加新列，这样可以保护现有公式
                self._log("info", f"使用保护现有公式的方式添加列: {target_column}")
                
                # 检查目标列是否已存在
                existing_columns = self.excel_reader.get_column_names(file_path, sheet_name)
                if target_column in existing_columns:
                    if overwrite_strategy == "overwrite":
                        # 如果要覆盖现有列，我们需要先删除该列，然后添加新列
                        # 但这里我们选择保护策略，生成新的列名
                        self._log("info", f"目标列 '{target_column}' 已存在，将生成唯一列名")
                
                # 使用保护现有公式的添加列方法
                success = self._save_with_formula_protection(file_path, formula_data, sheet_name)
            else:
                # 使用原有的保存方法
                success = self.excel_reader.save_data(
                    file_path, 
                    formula_data,
                    sheet_name, 
                    overwrite_strategy
                )
            
            if not success:
                self._log("error", "数据保存失败")
                return ProcessingResult(
                    success=False,
                    total_rows=data_rows,
                    processed_rows=self.processing_stats['processed_rows'],
                    success_rows=self.processing_stats['success_rows'],
                    error_rows=self.processing_stats['error_rows'],
                    errors=self.processing_stats['errors'] + [{"error": "数据保存失败"}],
                    execution_time=time.time() - start_time
                )
            
            execution_time = time.time() - start_time
            self._log("info", f"全量处理完成，成功 {success_count} 个，失败 {error_count} 个，总耗时: {execution_time:.2f}秒")
            
            # 重新读取完整数据用于返回结果
            result_data = self.excel_reader.read_full_data(file_path, sheet_name)
            
            self.status = ProcessingStatus.COMPLETED
            return ProcessingResult(
                success=True,
                total_rows=data_rows,
                processed_rows=self.processing_stats['processed_rows'],
                success_rows=success_count,
                error_rows=error_count,
                errors=self.processing_stats['errors'],
                execution_time=execution_time,
                result_data=result_data
            )
            
        except Exception as e:
            error_msg = f"全量处理异常: {str(e)}"
            self._log("error", error_msg)
            self.status = ProcessingStatus.ERROR
            return ProcessingResult(
                success=False,
                total_rows=0,
                processed_rows=0,
                success_rows=0,
                error_rows=0,
                errors=[{"row": 0, "error": error_msg}],
                execution_time=time.time() - start_time if 'start_time' in locals() else 0
            )

    def _save_with_formula_protection(self, file_path: str, formula_data: pd.DataFrame, 
                                    sheet_name: Optional[str]) -> bool:
        """使用保护现有公式的方式保存数据"""
        try:
            # 直接调用ExcelFormulaReader的保护公式方法
            self.excel_reader._add_new_column_with_formula_support(
                Path(file_path), 
                formula_data, 
                sheet_name
            )
            return True
        except Exception as e:
            self._log("error", f"保护公式保存失败: {str(e)}")
            return False
    
    def _read_batch_data(self, file_path: str, start_row: int, end_row: int, 
                        sheet_name: Optional[str]) -> Optional[pd.DataFrame]:
        """读取批次数据"""
        try:
            # 计算要跳过的行数和读取的行数
            skiprows = start_row  # 跳过表头和前面的数据行
            nrows = end_row - start_row  # 实际要读取的数据行数
            
            # 先读取表头
            if hasattr(self, '_column_names'):
                column_names = self._column_names
            else:
                header_data = pd.read_excel(file_path, sheet_name=sheet_name, nrows=1)
                column_names = header_data.columns.tolist()
                self._column_names = column_names
            
            # 读取批次数据
            batch_data = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                skiprows=skiprows,
                nrows=nrows,
                header=None,  # 不使用第一行作为列名
                names=column_names  # 使用预定义的列名
            )
            
            return batch_data
            
        except Exception as e:
            self._log("error", f"批次数据读取失败: {str(e)}")
            return None
    
    def pause_processing(self):
        """暂停处理"""
        if self.status == ProcessingStatus.RUNNING:
            self.pause_requested = True
            self._log("info", "请求暂停处理")
    
    def resume_processing(self):
        """恢复处理"""
        if self.status == ProcessingStatus.PAUSED:
            self.pause_requested = False
            self._log("info", "恢复处理")
    
    def stop_processing(self):
        """停止处理"""
        if self.status in [ProcessingStatus.RUNNING, ProcessingStatus.PAUSED]:
            self.stop_requested = True
            self.pause_requested = False
            self._log("info", "请求停止处理")
    
    def get_status(self) -> ProcessingStatus:
        """获取当前状态"""
        return self.status
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.processing_stats.copy()
    
    def _create_backup(self, file_path: str) -> str:
        """创建文件备份"""
        try:
            file_path = Path(file_path)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
            backup_path = file_path.parent / backup_name
            
            # 复制文件
            import shutil
            shutil.copy2(file_path, backup_path)
            
            return str(backup_path)
            
        except Exception as e:
            self._log("warning", f"创建备份失败: {str(e)}")
            return ""
    
    def get_referenced_cells(self, formula: str) -> List[str]:
        """获取公式中引用的单元格"""
        return self.row_adjuster.get_referenced_cells(formula)