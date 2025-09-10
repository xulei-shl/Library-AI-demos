"""
任务调度器模块 - 负责异步任务管理和线程池处理
"""

import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Any, Callable, Optional, List
import logging
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """任务对象"""
    
    def __init__(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_time = time.time()
        self.start_time = None
        self.end_time = None
        self.progress = 0.0
        
    def execute(self):
        """执行任务"""
        try:
            self.status = TaskStatus.RUNNING
            self.start_time = time.time()
            
            self.result = self.func(*self.args, **self.kwargs)
            
            self.status = TaskStatus.COMPLETED
            self.end_time = time.time()
            
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = str(e)
            self.end_time = time.time()
            raise
            
    def get_duration(self) -> float:
        """获取任务执行时长"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'progress': self.progress,
            'created_time': self.created_time,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.get_duration(),
            'error': self.error
        }


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_workers: int = 2):
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 任务管理
        self.tasks: Dict[str, Task] = {}
        self.futures: Dict[str, Future] = {}
        
        # 状态管理
        self.is_running = True
        self._lock = threading.Lock()
        
        # 监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_tasks, daemon=True)
        self.monitor_thread.start()
        
    def submit_task(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None) -> str:
        """提交任务"""
        try:
            with self._lock:
                if task_id in self.tasks:
                    raise ValueError(f"任务ID已存在: {task_id}")
                    
                # 创建任务
                task = Task(task_id, func, args, kwargs)
                self.tasks[task_id] = task
                
                # 提交到线程池
                future = self.executor.submit(task.execute)
                self.futures[task_id] = future
                
                self.logger.info(f"任务已提交: {task_id}")
                return task_id
                
        except Exception as e:
            self.logger.error(f"提交任务失败: {e}")
            raise
            
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            with self._lock:
                if task_id not in self.tasks:
                    return False
                    
                task = self.tasks[task_id]
                future = self.futures.get(task_id)
                
                if future and future.cancel():
                    task.status = TaskStatus.CANCELLED
                    self.logger.info(f"任务已取消: {task_id}")
                    return True
                    
                return False
                
        except Exception as e:
            self.logger.error(f"取消任务失败: {e}")
            return False
            
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self._lock:
            task = self.tasks.get(task_id)
            return task.to_dict() if task else None
            
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务状态"""
        with self._lock:
            return [task.to_dict() for task in self.tasks.values()]
            
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """等待任务完成"""
        try:
            future = self.futures.get(task_id)
            if not future:
                raise ValueError(f"任务不存在: {task_id}")
                
            return future.result(timeout=timeout)
            
        except Exception as e:
            self.logger.error(f"等待任务失败: {e}")
            raise
            
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        try:
            with self._lock:
                completed_tasks = []
                
                for task_id, task in self.tasks.items():
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        completed_tasks.append(task_id)
                        
                for task_id in completed_tasks:
                    del self.tasks[task_id]
                    if task_id in self.futures:
                        del self.futures[task_id]
                        
                self.logger.info(f"清理了 {len(completed_tasks)} 个已完成任务")
                
        except Exception as e:
            self.logger.error(f"清理任务失败: {e}")
            
    def get_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        with self._lock:
            stats = {
                'total_tasks': len(self.tasks),
                'pending': 0,
                'running': 0,
                'completed': 0,
                'failed': 0,
                'cancelled': 0,
                'max_workers': self.max_workers
            }
            
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING:
                    stats['pending'] += 1
                elif task.status == TaskStatus.RUNNING:
                    stats['running'] += 1
                elif task.status == TaskStatus.COMPLETED:
                    stats['completed'] += 1
                elif task.status == TaskStatus.FAILED:
                    stats['failed'] += 1
                elif task.status == TaskStatus.CANCELLED:
                    stats['cancelled'] += 1
                    
            return stats
            
    def _monitor_tasks(self):
        """监控任务状态"""
        while self.is_running:
            try:
                with self._lock:
                    # 检查已完成的任务
                    for task_id, future in list(self.futures.items()):
                        if future.done():
                            task = self.tasks.get(task_id)
                            if task and task.status == TaskStatus.RUNNING:
                                try:
                                    # 获取结果（如果有异常会抛出）
                                    result = future.result()
                                    task.result = result
                                    task.status = TaskStatus.COMPLETED
                                    task.end_time = time.time()
                                    
                                except Exception as e:
                                    task.status = TaskStatus.FAILED
                                    task.error = str(e)
                                    task.end_time = time.time()
                                    
                time.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                self.logger.error(f"任务监控失败: {e}")
                time.sleep(5)  # 出错时等待更长时间
                
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        try:
            self.is_running = False
            self.executor.shutdown(wait=wait)
            self.logger.info("任务调度器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭调度器失败: {e}")
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


class AsyncTaskManager:
    """异步任务管理器 - 简化的任务管理接口"""
    
    def __init__(self):
        self.scheduler = TaskScheduler()
        self.logger = logging.getLogger(__name__)
        
    def run_async(self, func: Callable, *args, **kwargs) -> str:
        """异步运行函数"""
        task_id = f"task_{int(time.time() * 1000)}"
        return self.scheduler.submit_task(task_id, func, args, kwargs)
        
    def wait_for_completion(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """等待任务完成"""
        return self.scheduler.wait_for_task(task_id, timeout)
        
    def is_task_running(self, task_id: str) -> bool:
        """检查任务是否正在运行"""
        status = self.scheduler.get_task_status(task_id)
        return status and status['status'] == TaskStatus.RUNNING.value
        
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self.scheduler.cancel_task(task_id)
        
    def get_task_progress(self, task_id: str) -> Optional[float]:
        """获取任务进度"""
        status = self.scheduler.get_task_status(task_id)
        return status['progress'] if status else None
        
    def cleanup(self):
        """清理资源"""
        self.scheduler.clear_completed_tasks()
        
    def shutdown(self):
        """关闭管理器"""
        self.scheduler.shutdown()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()