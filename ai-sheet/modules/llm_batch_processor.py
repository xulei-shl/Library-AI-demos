"""
LLM批量处理器模块 - 负责批量AI调用和数据处理
复用现有的OptimizedPromptGenerator架构
"""

import time
import threading
from typing import List, Dict, Any, Callable, Optional
import logging
from pathlib import Path

from .prompt_generator import OptimizedPromptGenerator
from .excel_processor import ExcelProcessor


class ProcessingState:
    """处理状态管理类 - 统一管理所有处理相关的状态"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """重置所有状态"""
        self.total = 0
        self.processed = 0
        self.success = 0
        self.failed = 0
        self.start_time = None
        self.current_speed = 0.0
        self.current_file = None
        self.current_row = None
        self.last_total = 0  # 用于检测文件切换
    
    def update_progress(self, **kwargs):
        """更新进度状态"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'total': self.total,
            'processed': self.processed,
            'success': self.success,
            'failed': self.failed,
            'start_time': self.start_time,
            'current_speed': self.current_speed,
            'current_file': self.current_file,
            'current_row': self.current_row
        }


class LLMBatchProcessor:
    """LLM批量处理器 - 复用现有AI调用架构"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 复用现有的AI调用组件
        self.prompt_generator = OptimizedPromptGenerator()
        
        # 处理状态
        self.is_processing = False
        self.is_paused = False
        self.should_stop = False
        
        # 使用新的状态管理类
        self.state = ProcessingState()
        
        # 保持向后兼容的stats属性
        self.stats = self.state.to_dict()
        
    def process_excel_batch(self, 
                           file_path: str,
                           columns: List[str],
                           model_config: Dict[str, Any],
                           prompt_config: Dict[str, Any],
                           temperature: float = 0.3,
                           top_p: float = 0.9,
                           progress_callback: Optional[Callable] = None,
                           log_callback: Optional[Callable] = None,
                           pause_check: Optional[Callable] = None,
                           stop_check: Optional[Callable] = None,
                           current_row_callback: Optional[Callable] = None,
                           pending_stop_check: Optional[Callable] = None,
                           pending_pause_check: Optional[Callable] = None,
                           pause_confirmed_callback: Optional[Callable] = None,
                           stop_confirmed_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        批量处理Excel数据
        
        Args:
            file_path: Excel文件路径
            columns: 要处理的列名列表
            model_config: 模型配置
            prompt_config: 提示词配置
            temperature: 温度参数
            top_p: top_p参数
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
            pause_check: 暂停检查函数
            stop_check: 停止检查函数
        """
        try:
            self.is_processing = True
            self.should_stop = False
            self.stats['start_time'] = time.time()
            
            if log_callback:
                log_callback("开始批量处理Excel数据...", "INFO")
            
            # 创建文件备份
            if log_callback:
                log_callback("正在创建文件备份...", "INFO")
            backup_path = self._create_backup(file_path)
            if backup_path:
                if log_callback:
                    log_callback(f"文件备份成功: {backup_path}", "INFO")
            else:
                if log_callback:
                    log_callback("文件备份失败，但继续处理", "WARNING")
                
            # 使用Excel处理器
            with ExcelProcessor() as excel_processor:
                excel_processor.load_excel(file_path)
                
                # 获取数据和状态
                data_rows = excel_processor.get_column_data(columns)
                
                # 获取提示词名称作为列名
                prompt_name = prompt_config.get('name', 'AI处理结果')
                if log_callback:
                    log_callback(f"使用提示词: {prompt_name}", "INFO")
                
                result_column = excel_processor.find_result_column(prompt_name)
                
                self.stats['total'] = len(data_rows)
                
                if log_callback:
                    log_callback(f"共需处理 {self.stats['total']} 行数据", "INFO")
                    
                # 获取提示词内容
                system_prompt = prompt_config.get('content', '')
                user_prompt_template = prompt_config.get('user_prompt', '{input}')
                
                # 逐行处理数据
                for i, row_data in enumerate(data_rows):
                    # 检查停止条件
                    if stop_check and stop_check():
                        if log_callback:
                            log_callback("收到停止信号，终止处理", "WARNING")
                        break
                        
                    # 检查暂停条件
                    while pause_check and pause_check():
                        time.sleep(0.1)  # 暂停时短暂休眠
                        if stop_check and stop_check():
                            break
                            
                    row_number = row_data['row_number']
                    
                    # 设置当前处理行号
                    if current_row_callback:
                        current_row_callback(row_number)
                    
                    # 检查是否已处理（断点续传） - 使用提示词名称检查
                    if excel_processor.check_processed(row_number, result_column, prompt_name):
                        self.stats['processed'] += 1
                        self.stats['success'] += 1
                        
                        if log_callback:
                            log_callback(f"第{row_number}行在'{prompt_name}'列已处理，跳过", "INFO")
                            
                        self._update_progress(progress_callback)
                        continue
                        
                    try:
                        # 准备输入数据
                        input_data = row_data['combined']
                        
                        # 构建用户提示词
                        user_prompt = user_prompt_template.replace('{input}', input_data)
                        
                        if log_callback:
                            log_callback(f"正在处理第{row_number}行数据...", "INFO")
                            
                        # 调用AI处理（复用现有逻辑）
                        result = self._call_llm_single(
                            user_prompt=user_prompt,
                            system_prompt=system_prompt,
                            model_config=model_config,
                            temperature=temperature,
                            top_p=top_p
                        )
                        
                        # 写入结果 - 使用提示词名称
                        if excel_processor.write_result(row_number, result, result_column, prompt_name):
                            self.stats['success'] += 1
                            if log_callback:
                                log_callback(f"第{row_number}行处理成功，结果写入'{prompt_name}'列", "SUCCESS")
                        else:
                            self.stats['failed'] += 1
                            if log_callback:
                                log_callback(f"第{row_number}行写入'{prompt_name}'列失败", "ERROR")
                                
                        # AI调用完成后立即保存
                        excel_processor.save_excel()
                        
                        # AI调用完成后检查待处理的停止请求
                        if pending_stop_check and pending_stop_check():
                            if log_callback:
                                log_callback(f"第{row_number}行处理完成，执行停止操作", "WARNING")
                            if stop_confirmed_callback:
                                stop_confirmed_callback()
                            break
                            
                        # AI调用完成后检查待处理的暂停请求
                        if pending_pause_check and pending_pause_check():
                            if log_callback:
                                log_callback(f"第{row_number}行处理完成，执行暂停操作", "WARNING")
                            if pause_confirmed_callback:
                                pause_confirmed_callback()
                                
                    except Exception as e:
                        self.stats['failed'] += 1
                        error_msg = f"第{row_number}行处理失败: {str(e)}"
                        self.logger.error(error_msg)
                        if log_callback:
                            log_callback(error_msg, "ERROR")
                            
                        # 写入错误信息 - 使用提示词名称
                        excel_processor.write_result(row_number, f"处理失败: {str(e)}", result_column, prompt_name)
                        
                        # 错误处理后也要立即保存
                        excel_processor.save_excel()
                        
                        # 错误后也检查待处理的停止请求
                        if pending_stop_check and pending_stop_check():
                            if log_callback:
                                log_callback(f"第{row_number}行处理失败后，执行停止操作", "WARNING")
                            if stop_confirmed_callback:
                                stop_confirmed_callback()
                            break
                            
                        # 错误后也检查待处理的暂停请求
                        if pending_pause_check and pending_pause_check():
                            if log_callback:
                                log_callback(f"第{row_number}行处理失败后，执行暂停操作", "WARNING")
                            if pause_confirmed_callback:
                                pause_confirmed_callback()
                        
                    self.stats['processed'] += 1
                    
                    # 更新进度
                    self._update_progress(progress_callback)
                    
                    # 每处理10行输出一次进度日志（因为现在每行都保存，减少日志输出）
                    if self.stats['processed'] % 10 == 0:
                        if log_callback:
                            log_callback(f"已处理进度 ({self.stats['processed']}/{self.stats['total']})", "INFO")
                            
                # 最终保存
                excel_processor.save_excel()
                
                if log_callback:
                    log_callback("批量处理完成，正在保存文件...", "INFO")
                    
            # 返回处理结果
            return {
                'total': self.stats['total'],
                'processed': self.stats['processed'],
                'success': self.stats['success'],
                'failed': self.stats['failed'],
                'duration': time.time() - self.stats['start_time']
            }
            
        except Exception as e:
            error_msg = f"批量处理失败: {str(e)}"
            self.logger.error(error_msg)
            if log_callback:
                log_callback(error_msg, "ERROR")
            raise
        finally:
            self.is_processing = False
            
    def _call_llm_single(self, 
                        user_prompt: str,
                        system_prompt: str,
                        model_config: Dict[str, Any],
                        temperature: float,
                        top_p: float) -> str:
        """
        单次AI调用 - 复用现有的prompt_generator逻辑
        """
        try:
            # 构建消息格式（复用现有架构）
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
                
            messages.append({
                "role": "user", 
                "content": user_prompt
            })
            
            # 直接调用现有的LLMClient（通过prompt_generator）
            response = self.prompt_generator.llm_client.chat_completion(
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                model_config=model_config
            )
            
            # 提取响应内容
            if isinstance(response, dict):
                content = response.get('content', str(response))
            else:
                content = str(response)
                
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"AI调用失败: {e}")
            raise
            
    def _update_progress(self, progress_callback: Optional[Callable]):
        """更新进度信息"""
        try:
            if not progress_callback:
                return
                
            # 计算处理速度
            if self.stats['start_time'] and self.stats['processed'] > 0:
                elapsed_time = time.time() - self.stats['start_time']
                speed = (self.stats['processed'] / elapsed_time) * 60  # 每分钟处理数
                self.stats['current_speed'] = speed
            else:
                self.stats['current_speed'] = 0.0
                
            # 调用进度回调
            progress_callback(
                current=self.stats['processed'],
                total=self.stats['total'],
                success=self.stats['success'],
                failed=self.stats['failed'],
                speed=self.stats['current_speed']
            )
            
        except Exception as e:
            self.logger.error(f"更新进度失败: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        # 更新stats以保持同步
        self.stats = self.state.to_dict()
        return self.stats.copy()
        
    def reset_stats(self):
        """重置统计信息"""
        self.state.reset()
        self.stats = self.state.to_dict()
        self.logger.info("批量处理器状态已重置")
        
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
            self.logger.warning(f"创建备份失败: {str(e)}")
            return ""

    def force_stop(self):
        """强制停止处理"""
        self.should_stop = True
        self.is_processing = False
        self.is_paused = False
        self.logger.warning("批量处理器已强制停止")


class BatchProcessingManager:
    """批量处理管理器 - 支持多任务管理"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_processor = None
        self.processing_thread = None
        
    def start_batch_processing(self, **kwargs) -> threading.Thread:
        """启动批量处理任务"""
        try:
            if self.current_processor and self.current_processor.is_processing:
                raise RuntimeError("已有处理任务在运行")
                
            self.current_processor = LLMBatchProcessor()
            
            # 创建处理线程
            self.processing_thread = threading.Thread(
                target=self._run_batch_processing,
                args=(kwargs,),
                daemon=True
            )
            
            self.processing_thread.start()
            return self.processing_thread
            
        except Exception as e:
            self.logger.error(f"启动批量处理失败: {e}")
            raise
            
    def _run_batch_processing(self, kwargs):
        """运行批量处理"""
        try:
            self.current_processor.process_excel_batch(**kwargs)
        except Exception as e:
            self.logger.error(f"批量处理执行失败: {e}")
            
    def stop_processing(self):
        """停止当前处理"""
        if self.current_processor:
            self.current_processor.should_stop = True
            
    def get_current_stats(self) -> Optional[Dict[str, Any]]:
        """获取当前处理统计"""
        if self.current_processor:
            return self.current_processor.get_stats()
        return None
        
    def is_processing(self) -> bool:
        """检查是否正在处理"""
        return (self.current_processor and 
                self.current_processor.is_processing)