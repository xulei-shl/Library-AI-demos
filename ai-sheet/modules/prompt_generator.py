#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词生成模块
负责结构化提示词的生成、验证和优化
支持自定义提示词、模型选择和参数配置
"""

import threading
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import os

# 导入共享模块
from modules.config_manager import ConfigManager
from modules.prompt_manager import PromptManager
from units.llm_client import LLMClient


class PromptStructureProcessor:
    """提示词结构化处理器"""
    
    def __init__(self):
        self.required_fields = ['instruction']  # 必填字段
        self.optional_fields = ['role', 'background', 'example', 'output', 'constraint']  # 可选字段
    
    def validate_inputs(self, inputs: Dict[str, str]) -> tuple[bool, str]:
        """验证输入字段的有效性"""
        try:
            # 检查必填字段
            for field in self.required_fields:
                if not inputs.get(field, '').strip():
                    return False, f"请填写必填字段：{self._get_field_name(field)}"
            
            # 检查指令字段长度
            instruction = inputs.get('instruction', '').strip()
            if len(instruction) < 10:
                return False, "指令与要求至少需要10个字符"
            
            return True, "输入验证通过"
            
        except Exception as e:
            return False, f"验证输入时出错: {str(e)}"
    
    def _get_field_name(self, field: str) -> str:
        """获取字段的中文名称"""
        field_names = {
            'role': '角色',
            'background': '背景与目标',
            'instruction': '指令与要求',
            'example': '输入输出样例',
            'output': '输出要求',
            'constraint': '约束与限制'
        }
        return field_names.get(field, field)
    
    def build_structured_prompt(self, inputs: Dict[str, str]) -> str:
        """构建结构化提示词"""
        try:
            prompt_parts = []
            
            # 角色部分
            role = inputs.get('role', '').strip()
            if role:
                prompt_parts.append(f"# 角色\n{role}")
            
            # 背景与目标部分
            background = inputs.get('background', '').strip()
            if background:
                prompt_parts.append(f"# 背景与目标\n{background}")
            
            # 指令与要求部分（必填）
            instruction = inputs.get('instruction', '').strip()
            if instruction:
                prompt_parts.append(f"# 指令与要求\n{instruction}")
            
            # 样例部分
            example = inputs.get('example', '').strip()
            if example:
                prompt_parts.append(f"# 输入输出样例\n{example}")
            
            # 输出要求部分
            output = inputs.get('output', '').strip()
            if output:
                prompt_parts.append(f"# 输出要求\n{output}")
            
            # 约束与限制部分
            constraint = inputs.get('constraint', '').strip()
            if constraint:
                prompt_parts.append(f"# 约束与限制\n{constraint}")
            
            # 用双换行连接各部分
            return '\n\n'.join(prompt_parts)
            
        except Exception as e:
            return f"构建提示词时出错: {str(e)}"
    
    # ------------------- 样本读取 -------------------
    def _load_preview_sample(self) -> str:
        """直接返回 whole-file 内容"""
        preview_file = os.path.join("logs", "multi_excel_preview.md")
        if not os.path.exists(preview_file):
            return ""
        with open(preview_file, encoding='utf-8') as f:
            return f.read().strip()

    def build_context_for_ai(self, inputs: Dict[str, str]) -> str:
        """构建AI调用的上下文"""
        try:
            context = "请根据以下信息优化和完善提示词：\n\n"
            
            # 添加用户输入的各个部分
            for field in ['role', 'background', 'instruction', 'example', 'output', 'constraint']:
                value = inputs.get(field, '').strip()
                if value:
                    field_name = self._get_field_name(field)
                    context += f"## {field_name}\n{value}\n\n"
            
            # 构建数据样本部分
            sample_data = self._load_preview_sample()
            if sample_data and sample_data.strip():
                context += f"---\n\n## Excel数据样例\n\n{sample_data}"
            
            return context
            
        except Exception as e:
            return f"构建AI上下文时出错: {str(e)}"


class PromptCache:
    """提示词缓存管理器"""
    
    def __init__(self, max_size: int = 30):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}  # 记录访问时间，用于LRU淘汰
    
    def get_cached_prompt(self, inputs: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """获取缓存的提示词"""
        try:
            key = self._generate_cache_key(inputs)
            if key in self.cache:
                self.access_times[key] = datetime.now()
                return self.cache[key].copy()
            return None
        except Exception:
            return None
    
    def cache_prompt(self, inputs: Dict[str, str], result: Dict[str, Any]) -> None:
        """缓存提示词结果"""
        try:
            key = self._generate_cache_key(inputs)
            
            # 如果缓存已满，移除最久未访问的项
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            self.cache[key] = result.copy()
            self.access_times[key] = datetime.now()
            
        except Exception:
            pass  # 缓存失败不影响主要功能
    
    def _generate_cache_key(self, inputs: Dict[str, str]) -> str:
        """生成缓存键"""
        # 将所有输入字段按字母顺序排序后拼接
        sorted_inputs = []
        for key in sorted(inputs.keys()):
            value = inputs[key].strip()
            if value:
                sorted_inputs.append(f"{key}:{value}")
        return "|".join(sorted_inputs)
    
    def _evict_lru(self) -> None:
        """淘汰最久未访问的缓存项"""
        if not self.access_times:
            return
        
        # 找到最久未访问的键
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        
        # 移除缓存项
        if oldest_key in self.cache:
            del self.cache[oldest_key]
        if oldest_key in self.access_times:
            del self.access_times[oldest_key]
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()


class PromptHistory:
    """提示词历史记录管理器"""
    
    def __init__(self, max_history: int = 20):
        self.history = []
        self.max_history = max_history
    
    def add_prompt(self, inputs: Dict[str, str], generated_prompt: str, success: bool = True) -> None:
        """添加提示词到历史记录"""
        try:
            record = {
                'id': str(uuid.uuid4())[:8],
                'timestamp': datetime.now(),
                'inputs': inputs.copy(),
                'generated_prompt': generated_prompt,
                'success': success
            }
            
            self.history.insert(0, record)
            
            # 保持历史记录数量限制
            if len(self.history) > self.max_history:
                self.history = self.history[:self.max_history]
                
        except Exception:
            pass  # 历史记录失败不影响主要功能
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return [record.copy() for record in self.history]
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self.history.clear()
    
    def get_recent_prompts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最近的提示词记录"""
        return [record.copy() for record in self.history[:limit]]


class OptimizedPromptGenerator:
    """优化的提示词生成器"""
    
    def __init__(self):
        # 初始化共享模块
        self.config_manager = ConfigManager()
        self.prompt_manager = PromptManager()
        self.llm_client = LLMClient(self.config_manager)
        
        # 初始化组件
        self.structure_processor = PromptStructureProcessor()
        self.cache = PromptCache()
        self.history = PromptHistory()
        
        # 确保默认提示词存在
        self._ensure_default_prompts()
    
    def _ensure_default_prompts(self) -> None:
        """
        已移除冗余的默认提示词创建逻辑。
        默认提示词统一由 PromptManager 管理。
        此方法保持接口兼容性。
        """
        pass
    
    def generate_prompt(self, inputs: Dict[str, str], 
                       progress_callback: Optional[Callable] = None,
                       selected_prompt: str = "", selected_model: str = "",
                       temperature: float = 0.3, top_p: float = 0.9) -> Dict[str, Any]:
        """
        生成优化的提示词
        
        Args:
            inputs: 输入字段字典
            progress_callback: 进度回调函数
            selected_prompt: 选择的提示词
            selected_model: 选择的模型
            temperature: 温度参数
            top_p: top_p参数
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            if progress_callback:
                progress_callback("正在验证输入...")
            
            # 验证输入
            validation_result = self._validate_inputs(inputs)
            if not validation_result['success']:
                return validation_result
            
            if progress_callback:
                progress_callback("正在检查缓存...")
            
            # 检查缓存
            cached_result = self.cache.get_cached_prompt(inputs)
            if cached_result:
                cached_result['from_cache'] = True
                return cached_result
            
            if progress_callback:
                progress_callback("正在调用AI生成提示词...")
            
            # 调用AI生成提示词
            ai_result = self._call_ai_for_prompt(
                inputs, selected_prompt, selected_model, temperature, top_p
            )
            
            # 缓存结果
            if ai_result['success']:
                self.cache.cache_prompt(inputs, ai_result)
                self.history.add_prompt(inputs, ai_result['generated_prompt'], True)
            else:
                self.history.add_prompt(inputs, "", False)
            
            if progress_callback:
                progress_callback("提示词生成完成")
            
            return ai_result
            
        except Exception as e:
            return {
                'generated_prompt': '',
                'success': False,
                'error': f'生成提示词时出错：{str(e)}',
                'from_cache': False
            }
    
    def _validate_inputs(self, inputs: Dict[str, str]) -> Dict[str, Any]:
        """验证输入参数"""
        is_valid, message = self.structure_processor.validate_inputs(inputs)
        
        if not is_valid:
            return {
                'generated_prompt': '',
                'success': False,
                'error': message,
                'from_cache': False
            }
        
        return {'success': True}
    
    def _call_ai_for_prompt(self, inputs: Dict[str, str],
                           selected_prompt: str = "", selected_model: str = "",
                           temperature: float = 0.3, top_p: float = 0.9) -> Dict[str, Any]:
        """调用AI生成提示词"""
        try:
            # 获取系统提示词
            system_prompt = self._get_system_prompt(selected_prompt)
            
            # 构建用户消息
            user_message = self.structure_processor.build_context_for_ai(inputs)
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # 获取模型配置（如果指定了特定模型）
            model_config = None
            if selected_model:
                # 根据选择的模型名称获取模型配置
                models = self.config_manager.get_all_models()
                for model in models:
                    if model.get('name', '') == selected_model or model.get('model_id', '') == selected_model:
                        model_config = model
                        break
            
            # 调用LLM
            response = self.llm_client.chat_completion(
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                model_config=model_config
            )
            
            # 返回AI响应
            return {
                'generated_prompt': response.strip() if response else '',
                'success': True,
                'error': '',
                'from_cache': False
            }
            
        except Exception as e:
            return {
                'generated_prompt': '',
                'success': False,
                'error': f'AI调用失败：{str(e)}',
                'from_cache': False
            }
    
    def _get_system_prompt(self, selected_prompt: str = "") -> str:
        """获取系统提示词"""
        try:
            # 如果指定了提示词，直接获取对应的内容
            if selected_prompt:
                prompts = self.prompt_manager.get_all_prompts()
                for prompt in prompts:
                    if prompt.get('name', '') == selected_prompt or prompt.get('id', '') == selected_prompt:
                        return prompt.get('content', '')
            
            # 如果没有指定提示词，返回默认提示词
            return """
            从现在起，把自己当作我的专家助理，充分调动你的知识与推理能力。请始终提供：

- 对我问题清晰、直接的答案
- 你是如何得到结论的分步骤说明
- 我可能没有想到的其他视角或可选方案
- 立刻可执行的摘要或行动计划

不要给含糊的回答。问题过于宽泛时，请把它拆解成若干部分。若我寻求帮助，请像该领域的专业人士（老师、教练、工程师、医生等）那样回应。把你的推理能力开到最大。
            """
            
        except Exception:
            # 返回最基本的提示词
            return "请根据用户提供的信息，生成一个结构化、清晰、专业的提示词。"
    
    def generate_prompt_async(self, inputs: Dict[str, str],
                             selected_prompt: str = "",
                             selected_model: str = "",
                             temperature: float = 0.3,
                             top_p: float = 0.9,
                             success_callback: Optional[Callable] = None,
                             error_callback: Optional[Callable] = None,
                             progress_callback: Optional[Callable] = None) -> None:
        """
        异步生成提示词
        
        Args:
            inputs: 输入字段字典
            selected_prompt: 选择的提示词
            selected_model: 选择的模型
            temperature: 温度参数
            top_p: top_p参数
            success_callback: 成功回调函数
            error_callback: 错误回调函数
            progress_callback: 进度回调函数
        """
        def generation_thread():
            try:
                result = self.generate_prompt(
                    inputs, progress_callback,
                    selected_prompt, selected_model, temperature, top_p
                )
                
                if result['success'] and success_callback:
                    success_callback(result)
                elif not result['success'] and error_callback:
                    error_callback(result)
                    
            except Exception as e:
                error_result = {
                    'generated_prompt': '',
                    'success': False,
                    'error': f'异步生成失败：{str(e)}',
                    'from_cache': False
                }
                if error_callback:
                    error_callback(error_result)
        
        # 启动生成线程
        thread = threading.Thread(target=generation_thread)
        thread.daemon = True
        thread.start()
    
    def build_structured_prompt(self, inputs: Dict[str, str]) -> str:
        """构建结构化提示词（不调用AI）"""
        return self.structure_processor.build_structured_prompt(inputs)
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self.cache.cache),
            'max_cache_size': self.cache.max_size,
            'cache_hit_available': len(self.cache.cache) > 0
        }
    
    def get_history_statistics(self) -> Dict[str, Any]:
        """获取历史统计信息"""
        return {
            'total_prompts': len(self.history.history),
            'max_history_size': self.history.max_history,
            'recent_prompts': self.history.get_recent_prompts(3)
        }
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear_cache()
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self.history.clear_history()