#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python代码执行器
核心工具模块，封装Python代码的执行环境和过程
"""

import os
import sys
import subprocess
import tempfile
import shutil
import venv
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


class PythonExecutor:
    """Python代码执行器类
    
    负责：
    1. 在指定路径创建和管理Python虚拟环境
    2. 安装requirements.txt中的依赖
    3. 以子进程方式执行Python脚本
    4. 捕获并返回脚本的stdout, stderr, 和exit_code
    5. 处理文件IO，例如将输入数据传递给脚本
    """
    
    def __init__(self, work_directory: str):
        """初始化执行器
        
        Args:
            work_directory: 工作目录路径，用于存放代码、虚拟环境等
        """
        self.work_directory = Path(work_directory)
        self.venv_path = self.work_directory / ".venv"
        self.python_executable = self._get_python_executable()
        self.pip_executable = self._get_pip_executable()
        
        # 确保工作目录存在
        self.work_directory.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志
        self.log_file = self.work_directory / "execution.log"
        self._init_log()
    
    def _init_log(self):
        """初始化日志文件"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Python代码执行器日志 - {datetime.now()}\n")
            f.write("=" * 50 + "\n\n")
    
    def _log(self, message: str):
        """写入日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message)
        
        # 同时输出到控制台
        print(f"PythonExecutor: {message}")
    
    def _get_python_executable(self) -> str:
        """获取虚拟环境中的Python可执行文件路径"""
        if sys.platform == "win32":
            return str(self.venv_path / "Scripts" / "python.exe")
        else:
            return str(self.venv_path / "bin" / "python")
    
    def _get_pip_executable(self) -> str:
        """获取虚拟环境中的pip可执行文件路径"""
        if sys.platform == "win32":
            return str(self.venv_path / "Scripts" / "pip.exe")
        else:
            return str(self.venv_path / "bin" / "pip")
    
    def setup_environment(self) -> Tuple[bool, str]:
        """创建并设置Python虚拟环境
        
        Returns:
            (success, message): 成功状态和信息
        """
        try:
            self._log("开始设置Python虚拟环境...")
            
            # 如果虚拟环境已存在，先删除
            if self.venv_path.exists():
                self._log("发现已存在的虚拟环境，正在删除...")
                shutil.rmtree(self.venv_path)
            
            # 创建新的虚拟环境
            self._log(f"在 {self.venv_path} 创建虚拟环境...")
            venv.create(self.venv_path, with_pip=True, clear=True)
            
            # 验证虚拟环境是否创建成功
            if not os.path.exists(self.python_executable):
                raise RuntimeError(f"虚拟环境创建失败：找不到Python可执行文件 {self.python_executable}")
            
            self._log("虚拟环境创建成功")
            return True, "虚拟环境设置成功"
            
        except Exception as e:
            error_msg = f"设置虚拟环境失败：{str(e)}"
            self._log(error_msg)
            return False, error_msg
    
    def install_dependencies(self, requirements_content: str) -> Tuple[bool, str, str]:
        """安装依赖包
        
        Args:
            requirements_content: requirements.txt文件内容
            
        Returns:
            (success, stdout, stderr): 成功状态、标准输出、标准错误
        """
        try:
            self._log("开始安装依赖包...")
            
            # 检查虚拟环境是否存在
            if not os.path.exists(self.python_executable):
                return False, "", "虚拟环境不存在，请先设置环境"
            
            # 将requirements内容写入文件
            requirements_file = self.work_directory / "requirements.txt"
            with open(requirements_file, 'w', encoding='utf-8') as f:
                f.write(requirements_content)
            
            self._log(f"requirements.txt 已保存到 {requirements_file}")
            
            # 升级pip
            self._log("升级pip...")
            upgrade_cmd = [self.python_executable, "-m", "pip", "install", "--upgrade", "pip"]
            upgrade_result = subprocess.run(
                upgrade_cmd,
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=300  # 5分钟超时
            )
            
            if upgrade_result.returncode != 0:
                self._log(f"升级pip失败: {upgrade_result.stderr}")
            else:
                self._log("pip升级成功")
            
            # 安装依赖
            self._log("安装requirements.txt中的依赖...")
            install_cmd = [
                self.python_executable, 
                "-m", 
                "pip", 
                "install", 
                "-r", 
                str(requirements_file),
                "--no-cache-dir"  # 不使用缓存，确保获取最新版本
            ]
            
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0:
                self._log("依赖安装成功")
                return True, result.stdout, result.stderr
            else:
                self._log(f"依赖安装失败: {result.stderr}")
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            error_msg = "依赖安装超时"
            self._log(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"安装依赖时出错：{str(e)}"
            self._log(error_msg)
            return False, "", error_msg
    
    def save_script(self, script_content: str, filename: str = "main.py") -> str:
        """保存Python脚本到工作目录
        
        Args:
            script_content: 脚本内容
            filename: 文件名，默认为main.py
            
        Returns:
            script_path: 脚本文件的完整路径
        """
        script_path = self.work_directory / filename
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        self._log(f"脚本已保存到 {script_path}")
        return str(script_path)
    
    def save_input_data(self, data_content: str, filename: str = "input_data.md") -> str:
        """保存输入数据到工作目录
        
        Args:
            data_content: 数据内容（通常是markdown格式）
            filename: 文件名
            
        Returns:
            data_path: 数据文件的完整路径
        """
        data_path = self.work_directory / filename
        
        with open(data_path, 'w', encoding='utf-8') as f:
            f.write(data_content)
        
        self._log(f"输入数据已保存到 {data_path}")
        return str(data_path)
    
    def run_script(self, script_name: str = "main.py", timeout: int = 300) -> Dict[str, Any]:
        """执行Python脚本
        
        Args:
            script_name: 要执行的脚本文件名
            timeout: 超时时间（秒）
            
        Returns:
            执行结果字典，包含：
            - success: bool - 是否执行成功
            - exit_code: int - 退出码
            - stdout: str - 标准输出
            - stderr: str - 标准错误
            - execution_time: float - 执行时间（秒）
        """
        try:
            script_path = self.work_directory / script_name
            
            if not script_path.exists():
                return {
                    "success": False,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"脚本文件不存在: {script_path}",
                    "execution_time": 0.0
                }
            
            self._log(f"开始执行脚本: {script_path}")
            start_time = time.time()
            
            # 执行脚本
            cmd = [self.python_executable, str(script_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.work_directory,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # 记录执行结果
            self._log(f"脚本执行完成，退出码: {result.returncode}, 执行时间: {execution_time:.2f}秒")
            
            if result.stdout:
                self._log(f"标准输出: {result.stdout}")
            
            if result.stderr:
                self._log(f"标准错误: {result.stderr}")
            
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time
            }
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0.0
            error_msg = f"脚本执行超时（{timeout}秒）"
            self._log(error_msg)
            
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "execution_time": execution_time
            }
            
        except Exception as e:
            error_msg = f"执行脚本时出错：{str(e)}"
            self._log(error_msg)
            
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "execution_time": 0.0
            }
    
    def archive_failed_attempt(self, script_content: str, error_log: str, attempt_number: int):
        """归档失败的尝试
        
        Args:
            script_content: 失败的脚本内容
            error_log: 错误日志
            attempt_number: 尝试次数
        """
        try:
            # 创建changelogs目录
            changelogs_dir = self.work_directory / "changelogs"
            changelogs_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存失败的脚本
            failed_script_path = changelogs_dir / f"main_v{attempt_number}_{timestamp}.py"
            with open(failed_script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 保存错误日志
            error_log_path = changelogs_dir / f"error_v{attempt_number}_{timestamp}.log"
            with open(error_log_path, 'w', encoding='utf-8') as f:
                f.write(f"错误时间: {datetime.now()}\n")
                f.write(f"尝试次数: {attempt_number}\n")
                f.write("=" * 50 + "\n")
                f.write(error_log)
            
            self._log(f"第{attempt_number}次失败尝试已归档: {failed_script_path}, {error_log_path}")
            
        except Exception as e:
            self._log(f"归档失败尝试时出错: {str(e)}")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息
        
        Returns:
            环境信息字典
        """
        try:
            info = {
                "work_directory": str(self.work_directory),
                "venv_path": str(self.venv_path),
                "venv_exists": self.venv_path.exists(),
                "python_executable": self.python_executable,
                "python_executable_exists": os.path.exists(self.python_executable)
            }
            
            # 如果Python可执行文件存在，获取版本信息
            if info["python_executable_exists"]:
                try:
                    version_result = subprocess.run(
                        [self.python_executable, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    info["python_version"] = version_result.stdout.strip()
                except:
                    info["python_version"] = "无法获取版本信息"
            else:
                info["python_version"] = "Python可执行文件不存在"
            
            return info
            
        except Exception as e:
            return {
                "error": f"获取环境信息失败: {str(e)}"
            }
    
    def cleanup(self):
        """清理资源"""
        try:
            self._log("开始清理资源...")
            
            # 可以选择是否删除虚拟环境
            # 为了调试方便，这里不自动删除，由用户手动决定
            
            self._log("资源清理完成")
            
        except Exception as e:
            self._log(f"清理资源时出错: {str(e)}")


# 测试代码
if __name__ == "__main__":
    # 简单测试
    import tempfile
    
    # 创建临时目录进行测试
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = PythonExecutor(temp_dir)
        
        print("测试环境设置...")
        success, message = executor.setup_environment()
        print(f"环境设置: {success}, {message}")
        
        if success:
            print("\n测试依赖安装...")
            requirements = "pandas==2.0.0\nnumpy"
            success, stdout, stderr = executor.install_dependencies(requirements)
            print(f"依赖安装: {success}")
            if not success:
                print(f"错误: {stderr}")
            
            print("\n测试脚本执行...")
            test_script = '''
import sys
import pandas as pd
import numpy as np

print("Hello from test script!")
print(f"Python version: {sys.version}")
print(f"Pandas version: {pd.__version__}")
print(f"Numpy version: {np.__version__}")

# 创建简单的数据处理示例
data = pd.DataFrame({
    'A': [1, 2, 3, 4, 5],
    'B': [10, 20, 30, 40, 50]
})

print("\\nSample data:")
print(data)

# 保存结果
data.to_csv('output.csv', index=False)
print("\\nOutput saved to output.csv")
'''
            
            executor.save_script(test_script)
            result = executor.run_script()
            
            print(f"执行成功: {result['success']}")
            print(f"退出码: {result['exit_code']}")
            print(f"执行时间: {result['execution_time']:.2f}秒")
            print(f"标准输出:\n{result['stdout']}")
            if result['stderr']:
                print(f"标准错误:\n{result['stderr']}")