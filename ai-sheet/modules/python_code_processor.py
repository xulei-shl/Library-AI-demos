#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python代码处理器
作为Python代码处理功能的后端总控制器（Orchestrator）
实现从提示词生成到最终文档生成的完整工作流
"""

import os
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
from datetime import datetime

from modules.python_code_executor import PythonExecutor
from modules.config_manager import ConfigManager
from modules.prompt_manager import PromptManager
from units.llm_client import LLMClient


class PythonCodeProcessor:
    """Python代码处理主控制器
    
    功能流程：
    1. 提示词生成 -> 代码生成 
    2. 自动测试与修复 
    3. 正式数据处理 
    4. 结果与文档生成
    """
    
    def __init__(self):
        """初始化处理器"""
        self.config_manager = ConfigManager()
        self.prompt_manager = PromptManager()
        self.llm_client = LLMClient(self.config_manager)
        
        # 最大重试次数
        self.max_retry_attempts = 3
        
        # 当前处理状态
        self.current_executor: Optional[PythonExecutor] = None
        self.current_work_dir: Optional[str] = None
        
    def analyze_processing_type(self,
                               requirement: str,
                               sample_data: str,
                               selected_model: str = "") -> Dict[str, Any]:
        """分析处理类型
        
        Args:
            requirement: 用户需求描述
            sample_data: 样例数据（markdown格式）
            selected_model: 选择的大模型
            
        Returns:
            分析结果字典
        """
        try:
            # 构建分析提示词
            analysis_prompt = f"""用户需求：
{requirement}

---

样例数据：
{sample_data}

请分析上述数据处理需求的类型。"""
            
            # 获取系统提示词
            system_prompt = self._get_system_prompt("python处理类型分析")
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analysis_prompt}
            ]
            
            # 获取模型配置
            model_config = self._get_model_config(selected_model)
            
            # 调用LLM
            response = self.llm_client.chat_completion(
                messages=messages,
                temperature=0.1,  # 使用较低的温度以获得更一致的结果
                top_p=0.9,
                model_config=model_config
            )
            
            if not response:
                return {
                    'success': False,
                    'error': 'LLM返回空响应'
                }
            
            # 解析JSON响应
            try:
                # 提取JSON部分
                json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试直接解析整个响应
                    json_str = response.strip()
                
                analysis_result = json.loads(json_str)
                
                # 验证必要字段
                required_fields = ['type', 'reason', 'suggested_columns', 'confidence']
                for field in required_fields:
                    if field not in analysis_result:
                        return {
                            'success': False,
                            'error': f'缺少必要字段: {field}'
                        }
                
                # 验证类型值
                if analysis_result['type'] not in ['enhancement', 'reconstruction']:
                    analysis_result['type'] = 'enhancement'  # 默认为增强型
                
                # 确保置信度在合理范围内
                if not isinstance(analysis_result['confidence'], (int, float)):
                    analysis_result['confidence'] = 0.8
                elif analysis_result['confidence'] > 1:
                    analysis_result['confidence'] = analysis_result['confidence'] / 100
                
                return {
                    'success': True,
                    'analysis': analysis_result
                }
                
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'error': f'无法解析LLM返回的JSON: {str(e)}\n原始响应: {response[:200]}...'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'分析处理类型时出错: {str(e)}'
            }
    
    def _get_model_config(self, selected_model: str) -> Optional[Dict[str, Any]]:
        """获取模型配置"""
        if not selected_model:
            return None
        
        for model in self.config_manager.get_all_models():
            if model.get('name') == selected_model or model.get('model_id') == selected_model:
                return model
        return None
    
    def process_python_code_with_strategy(self,
                                        requirement: str,
                                        sample_data: str,
                                        output_directory: str,
                                        selected_model: str = "",
                                        strategy: Optional[Dict[str, Any]] = None,
                                        temperature: float = 0.3,
                                        top_p: float = 0.9,
                                        progress_callback: Optional[Callable[[str], None]] = None,
                                        log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """使用策略处理Python代码
        
        Args:
            requirement: 用户需求描述
            sample_data: 样例数据（markdown格式）
            output_directory: 结果保存路径
            selected_model: 选择的大模型
            strategy: 处理策略信息
            temperature: 温度参数
            top_p: top_p参数
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
            
        Returns:
            处理结果字典
        """
        # 默认策略
        if not strategy:
            strategy = {'type': 'enhancement'}
        
        # 构建增强的提示词
        enhanced_requirement = self._build_strategy_enhanced_prompt(
            requirement, sample_data, strategy
        )
        
        # 调用原有的处理方法
        return self.process_python_code(
            requirement=enhanced_requirement,
            sample_data=sample_data,
            output_directory=output_directory,
            selected_model=selected_model,
            temperature=temperature,
            top_p=top_p,
            progress_callback=progress_callback,
            log_callback=log_callback
        )
    
    def _build_strategy_enhanced_prompt(self, 
                                       requirement: str, 
                                       sample_data: str, 
                                       strategy: Dict[str, Any]) -> str:
        """根据策略构建增强的提示词"""
        processing_type = strategy.get('type', 'enhancement')
        analysis_result = strategy.get('analysis_result', {})
        
        # 检查requirement是否已经是完整的提示词格式（包含标题结构）
        if "# 数据处理需求" in requirement and ("# Excel" in requirement or "# 输出策略" in requirement):
            # 已有完整结构，智能检测是否已包含策略信息
            if "# 输出策略" in requirement or "# 结果保存策略" in requirement:
                # 已包含策略信息，直接返回，避免重复
                enhanced_prompt = requirement
            else:
                # 只添加缺少的策略信息
                enhanced_prompt = requirement
                strategy_section = f"""\n\n---\n\n# 结果保存策略\n\n处理类型：{processing_type}"""
                
                if processing_type == "enhancement":
                    main_excel = strategy.get('main_excel', '')
                    main_sheet = strategy.get('main_sheet', '')
                    keep_original = strategy.get('keep_original', True)
                    suggested_columns = analysis_result.get('suggested_columns', [])
                    
                    strategy_section += f"""
处理结果存储的Excel文件：{main_excel}
处理结果存储的Sheet：{main_sheet}
保留原始数据：{'是' if keep_original else '否'}
建议新增列：{', '.join(suggested_columns)}

**要求：**
1. 从指定的Excel文件和Sheet中读取数据
2. 对数据进行处理并生成结果
3. 将结果作为新列添加到原始数据中
4. 保存为新的Excel文件
5. 如果存在同名列，自动添加序号后缀（如 -1, -2, -3）"""
                
                else:  # reconstruction
                    strategy_section += f"""

**要求：**
1. 从提供的数据中读取信息
2. 根据需求重新组织和处理数据
3. 生成全新的结构化结果文件
4. 不需要保留原始数据结构"""
                
                enhanced_prompt += strategy_section
        else:
            # 简单的需求描述，构建完整提示词
            enhanced_prompt = f"""# 数据处理需求

{requirement}

---

# Excel数据样例

{sample_data}

---

# 结果保存策略

处理类型：{processing_type}
"""
            
            if processing_type == "enhancement":
                main_excel = strategy.get('main_excel', '')
                main_sheet = strategy.get('main_sheet', '')
                keep_original = strategy.get('keep_original', True)
                suggested_columns = analysis_result.get('suggested_columns', [])
                
                enhanced_prompt += f"""
处理结果存储的Excel文件：{main_excel}
处理结果存储的Sheet：{main_sheet}
保留原始数据：{'是' if keep_original else '否'}
建议新增列：{', '.join(suggested_columns)}

**要求：**
1. 从指定的Excel文件和Sheet中读取数据
2. 对数据进行处理并生成结果
3. 将结果作为新列添加到原始数据中
4. 保存为新的Excel文件
5. 如果存在同名列，自动添加序号后缀（如 -1, -2, -3）"""
            
            else:  # reconstruction
                enhanced_prompt += f"""

**要求：**
1. 从提供的数据中读取信息
2. 根据需求重新组织和处理数据
3. 生成全新的结构化结果文件
4. 不需要保留原始数据结构"""
        
        # 确保末尾有生成指令
        if "请根据上述" not in enhanced_prompt:
            enhanced_prompt += "\n\n请根据上述要求生成完整的Python代码。"
        
        return enhanced_prompt
    
    def process_python_code(self, 
                           requirement: str,
                           sample_data: str,
                           output_directory: str,
                           selected_model: str = "",
                           temperature: float = 0.3,
                           top_p: float = 0.9,
                           progress_callback: Optional[Callable[[str], None]] = None,
                           log_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """处理Python代码的主流程
        
        Args:
            requirement: 用户需求描述
            sample_data: 样例数据（markdown格式）
            output_directory: 结果保存路径
            selected_model: 选择的大模型
            temperature: 温度参数
            top_p: top_p参数
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
            
        Returns:
            处理结果字典
        """
        try:
            def log(message: str):
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_message = f"[{timestamp}] {message}"
                if log_callback:
                    log_callback(log_message)
                print(f"PythonCodeProcessor: {message}")
            
            def progress(message: str):
                if progress_callback:
                    progress_callback(message)
                log(message)
            
            progress("开始Python代码处理...")
            
            # 1. 初始化工作环境
            self.current_work_dir = output_directory
            self.current_executor = PythonExecutor(output_directory)
            
            # 2. 保存输入数据
            log("保存样例数据...")
            sample_data_path = self.current_executor.save_input_data(sample_data, "sample_data.md")
            
            # 3. 生成初始代码
            progress("生成Python代码...")
            initial_prompt = self._build_initial_prompt(requirement, sample_data)
            
            code_result = self._generate_code(
                initial_prompt, 
                selected_model, 
                temperature, 
                top_p,
                is_fix=False
            )
            
            if not code_result['success']:
                return {
                    'success': False,
                    'error': f"代码生成失败: {code_result['error']}",
                    'work_directory': output_directory
                }
            
            main_py_content = code_result['main_py']
            requirements_content = code_result['requirements']
            
            log(f"生成的代码长度: {len(main_py_content)} 字符")
            log(f"依赖包数量: {len(requirements_content.splitlines())} 个")
            
            # 4. 自动测试与修复循环
            progress("开始自动测试与修复...")
            final_code, final_requirements = self._auto_test_and_fix_loop(
                main_py_content,
                requirements_content,
                initial_prompt,
                sample_data,
                selected_model,
                temperature,
                top_p,
                progress,
                log
            )
            
            if final_code is None:
                return {
                    'success': False,
                    'error': f"经过{self.max_retry_attempts}次尝试，代码仍无法正常运行",
                    'work_directory': output_directory
                }
            
            # 5. 正式数据处理
            progress("执行正式数据处理...")
            
            # 保存完整数据（如果与样例数据不同的话）
            full_data_path = self.current_executor.save_input_data(sample_data, "full_data.md")
            
            # 执行最终代码
            final_script_path = self.current_executor.save_script(final_code, "main.py")
            execution_result = self.current_executor.run_script("main.py", timeout=600)  # 10分钟超时
            
            if not execution_result['success']:
                log(f"正式执行失败: {execution_result['stderr']}")
                return {
                    'success': False,
                    'error': f"正式执行失败: {execution_result['stderr']}",
                    'work_directory': output_directory
                }
            
            # 6. 生成文档
            progress("生成项目文档...")
            readme_result = self._generate_documentation(
                requirement,
                final_code,
                execution_result,
                selected_model,
                temperature,
                top_p
            )
            
            if readme_result['success']:
                readme_path = os.path.join(output_directory, "README.md")
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(readme_result['content'])
                log("README.md 生成成功")
            else:
                log(f"README.md 生成失败: {readme_result['error']}")
            
            progress("Python代码处理完成！")
            
            return {
                'success': True,
                'work_directory': output_directory,
                'execution_time': execution_result['execution_time'],
                'stdout': execution_result['stdout'],
                'files_created': self._list_output_files()
            }
            
        except Exception as e:
            error_msg = f"处理过程中出现错误: {str(e)}"
            if log_callback:
                log_callback(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'work_directory': output_directory if 'output_directory' in locals() else ""
            }
    
    def _build_initial_prompt(self, requirement: str, sample_data: str) -> str:
        """构建初始提示词"""
        # 检查requirement是否已经是完整的提示词格式（包含标题结构）
        if "# 数据处理需求" in requirement and "# Excel" in requirement:
            # 已经是完整的提示词，直接使用
            prompt = requirement
            # 如果需要，在末尾添加生成指令
            if "请根据上述需求和数据样例，生成处理Excel数据的Python代码" not in prompt:
                prompt += "\n\n请根据上述需求和数据样例，生成处理Excel数据的Python代码。"
        else:
            # 简单的需求描述，需要构建完整提示词
            prompt = f"""# 数据处理需求

{requirement}

---

# Excel数据样例

{sample_data}

请根据上述需求和数据样例，生成处理Excel数据的Python代码。"""
        
        return prompt
    
    def _generate_code(self, 
                      user_prompt: str, 
                      selected_model: str,
                      temperature: float,
                      top_p: float,
                      is_fix: bool = False) -> Dict[str, Any]:
        """调用LLM生成代码
        
        Args:
            user_prompt: 用户提示词
            selected_model: 选择的模型
            temperature: 温度参数
            top_p: top_p参数
            is_fix: 是否是修复模式
            
        Returns:
            生成结果字典
        """
        try:
            # 选择系统提示词
            system_prompt_name = "python代码修复" if is_fix else "python代码编写"
            system_prompt = self._get_system_prompt(system_prompt_name)
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 获取模型配置
            model_config = None
            if selected_model:
                for model in self.config_manager.get_all_models():
                    if model.get('name') == selected_model or model.get('model_id') == selected_model:
                        model_config = model
                        break
            
            # 调用LLM
            response = self.llm_client.chat_completion(
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                model_config=model_config
            )
            
            if not response:
                return {
                    'success': False,
                    'error': 'LLM返回空响应'
                }
            
            # 解析响应，提取main.py和requirements.txt内容
            main_py, requirements = self._parse_llm_response(response)
            
            if not main_py:
                return {
                    'success': False,
                    'error': '无法从LLM响应中提取有效的Python代码'
                }
            
            return {
                'success': True,
                'main_py': main_py,
                'requirements': requirements,
                'raw_response': response
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'调用LLM失败: {str(e)}'
            }
    
    def _parse_llm_response(self, response: str) -> Tuple[str, str]:
        """解析LLM响应，提取main.py和requirements.txt内容
        
        Args:
            response: LLM的原始响应
            
        Returns:
            (main_py_content, requirements_content): Python代码和依赖内容
        """
        main_py_content = ""
        requirements_content = ""
        
        # 尝试多种模式匹配代码块
        
        # 模式1：明确标注的代码块
        main_py_patterns = [
            r'```python\s*#\s*main\.py\s*\n(.*?)\n```',
            r'```python\s*#\s*主代码\s*\n(.*?)\n```',
            r'```python\s*#.*main.*\n(.*?)\n```',
            r'main\.py.*?```python\s*\n(.*?)\n```',
        ]
        
        requirements_patterns = [
            r'```(?:txt|text)?\s*#\s*requirements\.txt\s*\n(.*?)\n```',
            r'```(?:txt|text)?\s*#\s*依赖\s*\n(.*?)\n```',
            r'requirements\.txt.*?```(?:txt|text)?\s*\n(.*?)\n```',
        ]
        
        # 尝试匹配main.py
        for pattern in main_py_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                main_py_content = match.group(1).strip()
                break
        
        # 如果没有找到明确标注的，尝试匹配第一个Python代码块
        if not main_py_content:
            python_blocks = re.findall(r'```python\s*\n(.*?)\n```', response, re.DOTALL)
            if python_blocks:
                main_py_content = python_blocks[0].strip()
        
        # 尝试匹配requirements.txt
        for pattern in requirements_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                requirements_content = match.group(1).strip()
                break
        
        # 如果没有找到requirements，尝试其他模式
        if not requirements_content:
            # 查找常见的包名列表
            common_packages = ['pandas', 'numpy', 'openpyxl', 'xlrd', 'matplotlib', 'seaborn', 'requests']
            found_packages = []
            
            for package in common_packages:
                if package in response.lower():
                    found_packages.append(package)
            
            if found_packages:
                requirements_content = '\n'.join(found_packages)
        
        # 如果仍然没有requirements，使用默认值
        if not requirements_content:
            requirements_content = "pandas\nnumpy\nopenpyxl"
        
        return main_py_content, requirements_content
    
    def _auto_test_and_fix_loop(self,
                               initial_code: str,
                               initial_requirements: str,
                               initial_prompt: str,
                               sample_data: str,
                               selected_model: str,
                               temperature: float,
                               top_p: float,
                               progress_callback: Callable[[str], None],
                               log_callback: Callable[[str], None]) -> Tuple[Optional[str], Optional[str]]:
        """自动测试与修复循环
        
        Returns:
            (final_code, final_requirements): 最终的代码和依赖，如果失败则返回(None, None)
        """
        current_code = initial_code
        current_requirements = initial_requirements
        
        # 确保执行器存在
        if not self.current_executor:
            log_callback("❗ 执行器未初始化")
            return None, None
        
        for attempt in range(1, self.max_retry_attempts + 1):
            log_callback(f"第 {attempt} 次尝试...")
            
            # 1. 设置环境
            progress_callback(f"第{attempt}次尝试 - 设置环境...")
            setup_success, setup_message = self.current_executor.setup_environment()
            if not setup_success:
                log_callback(f"环境设置失败: {setup_message}")
                continue
            
            # 2. 安装依赖
            progress_callback(f"第{attempt}次尝试 - 安装依赖...")
            install_success, install_stdout, install_stderr = self.current_executor.install_dependencies(current_requirements)
            if not install_success:
                log_callback(f"依赖安装失败: {install_stderr}")
                # 依赖安装失败可能需要修复requirements.txt
                # 这里可以添加智能修复逻辑
                continue
            
            # 3. 执行测试
            progress_callback(f"第{attempt}次尝试 - 测试执行...")
            self.current_executor.save_script(current_code, "main.py")
            test_result = self.current_executor.run_script("main.py", timeout=120)  # 2分钟超时
            
            if test_result['success']:
                log_callback(f"第{attempt}次尝试成功！")
                return current_code, current_requirements
            
            # 4. 执行失败，归档并尝试修复
            log_callback(f"第{attempt}次尝试失败: {test_result['stderr']}")
            
            # 归档失败尝试
            self.current_executor.archive_failed_attempt(
                current_code,
                test_result['stderr'],
                attempt
            )
            
            # 如果不是最后一次尝试，则尝试修复
            if attempt < self.max_retry_attempts:
                progress_callback(f"第{attempt}次尝试失败，尝试修复...")
                
                # 构建修复提示词
                fix_prompt = self._build_fix_prompt(
                    initial_prompt,
                    current_code,
                    current_requirements,
                    test_result['stderr']
                )
                
                # 调用LLM修复
                fix_result = self._generate_code(
                    fix_prompt,
                    selected_model,
                    temperature,
                    top_p,
                    is_fix=True
                )
                
                if fix_result['success']:
                    current_code = fix_result['main_py']
                    current_requirements = fix_result['requirements']
                    log_callback("代码修复完成，将进行下一次尝试...")
                else:
                    log_callback(f"代码修复失败: {fix_result['error']}")
        
        return None, None
    
    def _build_fix_prompt(self, 
                         initial_prompt: str,
                         failed_code: str,
                         failed_requirements: str,
                         error_message: str) -> str:
        """构建修复提示词"""
        fix_prompt = f"""原始需求：
{initial_prompt}

---

出错的Python代码（main.py）：
```python
{failed_code}
```

---

出错的依赖文件（requirements.txt）：
```
{failed_requirements}
```

---

错误信息：
```
{error_message}
```

请根据错误信息修复代码，生成修复后的完整Python代码和requirements.txt。"""
        
        return fix_prompt
    
    def _generate_documentation(self,
                               requirement: str,
                               final_code: str,
                               execution_result: Dict[str, Any],
                               selected_model: str,
                               temperature: float,
                               top_p: float) -> Dict[str, Any]:
        """生成项目文档
        
        Returns:
            文档生成结果
        """
        try:
            # 构建文档生成提示词
            doc_prompt = f"""请为以下Python数据处理项目生成README.md文档：

{requirement}

# 最终Python代码
```python
{final_code}
```

# 执行结果概述
- 执行成功: {execution_result['success']}
- 执行时间: {execution_result['execution_time']:.2f}秒
- 标准输出: {execution_result['stdout'][:500]}...

请生成一个完整的README.md，包含：
1. 项目简介
2. 功能说明
3. 如何运行
4. 输出文件说明
5. 注意事项

请使用Markdown格式。"""
            
            # 获取文档生成的系统提示词
            system_prompt = """你是一个技术文档专家，擅长为Python项目编写清晰、专业的README文档。请根据用户提供的信息，生成一个结构清晰、内容详实的README.md文档。"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": doc_prompt}
            ]
            
            # 获取模型配置
            model_config = None
            if selected_model:
                for model in self.config_manager.get_all_models():
                    if model.get('name') == selected_model or model.get('model_id') == selected_model:
                        model_config = model
                        break
            
            # 调用LLM
            response = self.llm_client.chat_completion(
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                model_config=model_config
            )
            
            if response:
                return {
                    'success': True,
                    'content': response
                }
            else:
                return {
                    'success': False,
                    'error': 'LLM返回空响应'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'生成文档失败: {str(e)}'
            }
    
    def _get_system_prompt(self, prompt_name: str) -> str:
        """获取系统提示词"""
        try:
            # 从提示词管理器中获取
            for prompt in self.prompt_manager.get_all_prompts():
                if prompt.get('name') == prompt_name or prompt.get('id') == prompt_name:
                    return prompt.get('content', '')
            
            # 如果没找到，返回默认提示词
            if prompt_name == "python代码编写":
                return "请根据提供的待处理excel数据信息，数据处理需求，样例数据编写处理excel数据的完整python代码。"
            elif prompt_name == "python代码修复":
                return "请根据提供的错误的 `main.py` 代码，错误日志，待处理excel数据信息，数据处理需求，样例数据修复代码，输出修复后的完整的python代码"
            else:
                return "请根据用户需求生成相应的内容。"
                
        except Exception as e:
            return "请根据用户需求生成相应的内容。"
    
    def _list_output_files(self) -> List[str]:
        """列出输出目录中的文件"""
        try:
            if not self.current_work_dir:
                return []
            
            files = []
            work_path = Path(self.current_work_dir)
            
            for file_path in work_path.rglob('*'):
                if file_path.is_file():
                    relative_path = file_path.relative_to(work_path)
                    files.append(str(relative_path))
            
            return files
            
        except Exception as e:
            return [f"列出文件失败: {str(e)}"]
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "processor_active": self.current_executor is not None,
            "work_directory": self.current_work_dir
        }
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.current_executor:
                self.current_executor.cleanup()
                self.current_executor = None
            
            self.current_work_dir = None
            
        except Exception as e:
            print(f"清理PythonCodeProcessor资源时出错: {e}")


# 测试代码
if __name__ == "__main__":
    # 简单测试
    processor = PythonCodeProcessor()
    
    test_requirement = """从Excel文件中读取数据，计算每个产品的总销售额，并生成报表。"""
    
    test_sample_data = """
# 样例数据

| 产品名称 | 单价 | 销量 |
|---------|------|------|
| 产品A   | 100  | 10   |
| 产品B   | 200  | 5    |
| 产品C   | 150  | 8    |
"""
    
    def test_progress(message):
        print(f"进度: {message}")
    
    def test_log(message):
        print(f"日志: {message}")
    
    # 这里只测试提示词构建，不执行完整流程
    initial_prompt = processor._build_initial_prompt(test_requirement, test_sample_data)
    print("构建的初始提示词:")
    print(initial_prompt)