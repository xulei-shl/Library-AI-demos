#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词管理模块
负责管理AI-Sheet的提示词库，提供增删改查功能
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

class PromptManager:
    """提示词管理器"""
    def __init__(self, prompts_file: str = None):
        # 如果调用者没传路径，就统一放到 config 目录
        if prompts_file is None:
            prompts_file = os.path.join("config", "prompts.json")
        self.prompts_file = prompts_file
        self.prompts_data = {}
        self.load_prompts()
        
    def get_default_prompts_data(self) -> Dict[str, Any]:
        """获取默认提示词数据结构"""
        return {
            "prompts": [
                {
                    "id": "default_chat",
                    "name": "默认对话",
                    "content": "你是一个Excel数据处理助手，专门帮助用户分析和处理Excel数据。\\n\\n你的主要职责：\\n1. 分析用户提供的Excel数据样本\\n2. 理解用户的数据处理需求\\n3. 推荐合适的处理方案（公式方案 vs AI处理方案）\\n4. 提供专业的数据处理建议\\n\\n处理原则：\\n- 对于简单的数学计算、文本处理，推荐使用Excel公式\\n- 对于复杂的语义分析、内容生成，推荐使用AI大模型处理\\n- 始终考虑处理效率和准确性\\n\\n请根据用户的数据和需求，给出详细的分析和建议。",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                },
                {
                    "id": "formula_generation",
                    "name": "Excel公式生成",
                    "content": "你是一个Excel公式专家，专门根据用户需求生成准确的Excel原生公式。\\n\\n输入信息：\\n- 用户选择的数据列（格式：A列-列名）\\n- 用户的处理需求描述\\n- 数据样本（前10行）\\n\\n输出要求：\\n1. 只返回Excel公式，不要额外解释\\n2. 使用标准Excel函数（SUM、VLOOKUP、IF、CONCATENATE等）\\n3. 确保公式语法完全正确\\n4. 支持复杂的嵌套函数和条件判断\\n5. 公式中的列引用使用相对引用（如A2、B2）\\n\\n注意事项：\\n- 公式必须能在Excel中直接执行\\n- 考虑数据类型和格式\\n- 处理可能的空值和错误情况",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                },
                {
                    "id": "prompt_optimization",
                    "name": "提示词优化",
                    "content": "你是一个提示词工程专家，专门优化和改进AI提示词的质量。\\n\\n任务：根据用户提供的结构化信息，生成高质量的AI提示词。\\n\\n输入结构：\\n- 角色：AI扮演的角色\\n- 背景与目标：任务背景和目标\\n- 指令与要求：具体的执行指令\\n- 样例：输入输出示例\\n- 输出要求：期望的输出格式\\n- 约束与限制：需要遵守的限制\\n\\n优化原则：\\n1. 角色定义清晰具体\\n2. 指令明确可执行\\n3. 输出格式标准化\\n4. 包含必要的约束条件\\n5. 语言简洁专业\\n\\n请将这些信息整合成一个完整、专业的AI提示词。",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            ],
            "metadata": {
                "version": "1.0",
                "total_prompts": 3,
                "last_updated": datetime.now().isoformat()
            }
        }
        
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().isoformat()
        
    def _generate_prompt_id(self) -> str:
        """生成唯一的提示词ID"""
        return str(uuid.uuid4())[:8]
    # -------------- 1. 关闭“默认提示词自动补回” --------------
    def _ensure_prompts_integrity(self) -> None:
        """
        仅保证数据结构完整（有 prompts/metadata 两个 key），
        不再追加任何默认提示词。
        """
        if "prompts" not in self.prompts_data:
            self.prompts_data["prompts"] = []
        if "metadata" not in self.prompts_data:
            self.prompts_data["metadata"] = {
                "version": "1.0",
                "total_prompts": 0,
                "last_updated": self._get_current_timestamp()
            }

    # -------------- 2. 让“确保默认提示词”直接 noop --------------
    def ensure_default_prompts(self) -> bool:
        """
        已禁用默认提示词自动恢复功能。
        用户删除的提示词在重启后不会自动恢复。
        此函数保持接口兼容性，直接返回 True。
        """
        return True

    # -------------- 3. （可选）第一次启动时也不再写默认内容 --------------
    def load_prompts(self) -> Dict[str, Any]:
        """
        文件存在就读，不存在就生成一个**空** prompts.json，
        不再带任何默认提示词。
        """
        try:
            if os.path.exists(self.prompts_file):
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    self.prompts_data = json.load(f)
                self._ensure_prompts_integrity()
            else:
                # 生成空结构
                self.prompts_data = {"prompts": [], "metadata": {}}
                self._ensure_prompts_integrity()
                self.save_prompts()
        except json.JSONDecodeError as e:
            print(f"提示词文件格式错误: {e}")
            if os.path.exists(self.prompts_file):
                backup = f"{self.prompts_file}.backup"
                os.rename(self.prompts_file, backup)
                print(f"已备份为 {backup}")
            # 损坏后也不再给默认提示词，只给空结构
            self.prompts_data = {"prompts": [], "metadata": {}}
            self._ensure_prompts_integrity()
            self.save_prompts()
        except Exception as e:
            print(f"加载提示词文件时出错: {e}")
            self.prompts_data = {"prompts": [], "metadata": {}}
        return self.prompts_data.copy()
    
    def reload_prompts(self) -> Dict[str, Any]:
        """重新加载提示词文件（强制从文件读取最新数据）"""
        print("🔄 强制重新加载提示词文件...")
        return self.load_prompts()
        
    def save_prompts(self, prompts_data: Optional[Dict[str, Any]] = None) -> bool:
        """保存提示词到文件"""
        try:
            if prompts_data is None:
                prompts_data = self.prompts_data
                
            # 更新元数据
            prompts_data["metadata"]["total_prompts"] = len(prompts_data.get("prompts", []))
            prompts_data["metadata"]["last_updated"] = self._get_current_timestamp()
                
            # 保存到文件
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                json.dump(prompts_data, f, ensure_ascii=False, indent=2)
                
            # 更新内存中的数据
            self.prompts_data = prompts_data.copy()
            
            return True
            
        except Exception as e:
            print(f"保存提示词文件时出错: {e}")
            return False
            
    def get_all_prompts(self) -> List[Dict[str, Any]]:
        """获取所有提示词"""
        return self.prompts_data.get("prompts", [])
        
    def get_prompt_by_id(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取提示词"""
        for prompt in self.prompts_data.get("prompts", []):
            if prompt.get("id") == prompt_id:
                return prompt.copy()
        return None
                
    def save_prompt(self, prompt_data: Dict[str, Any]) -> bool:
        """保存提示词（新增或更新）"""
        try:
            # 验证提示词数据
            is_valid, error_msg = self.validate_prompt_data(prompt_data)
            if not is_valid:
                print(f"提示词数据验证失败: {error_msg}")
                return False
                
            prompt_id = prompt_data.get("id")
            
            if prompt_id:
                # 更新现有提示词
                for i, prompt in enumerate(self.prompts_data["prompts"]):
                    if prompt.get("id") == prompt_id:
                        # 保留创建时间，更新修改时间
                        prompt_data["created_at"] = prompt.get("created_at", self._get_current_timestamp())
                        prompt_data["updated_at"] = self._get_current_timestamp()
                        
                        self.prompts_data["prompts"][i] = prompt_data
                        return self.save_prompts()
                        
                # 如果没找到对应ID，作为新提示词添加
                prompt_data["created_at"] = self._get_current_timestamp()
                prompt_data["updated_at"] = self._get_current_timestamp()
                self.prompts_data["prompts"].append(prompt_data)
                
            else:
                # 新增提示词
                prompt_data["id"] = self._generate_prompt_id()
                prompt_data["created_at"] = self._get_current_timestamp()
                prompt_data["updated_at"] = self._get_current_timestamp()
                
                self.prompts_data["prompts"].append(prompt_data)
                
            return self.save_prompts()
            
        except Exception as e:
            print(f"保存提示词时出错: {e}")
            return False
            
    def delete_prompt(self, prompt_id: str) -> bool:
        """删除提示词"""
        try:
            for i, prompt in enumerate(self.prompts_data["prompts"]):
                if prompt.get("id") == prompt_id:
                    del self.prompts_data["prompts"][i]
                    return self.save_prompts()
                    
            print(f"未找到ID为 {prompt_id} 的提示词")
            return False
            
        except Exception as e:
            print(f"删除提示词时出错: {e}")
            return False
            
    def validate_prompt_data(self, prompt_data: Dict[str, Any]) -> tuple[bool, str]:
        """验证提示词数据"""
        try:
            # 检查必填字段
            required_fields = ["name", "content"]
            for field in required_fields:
                if field not in prompt_data or not str(prompt_data[field]).strip():
                    return False, f"字段 '{field}' 不能为空"
                    
            # 验证名称长度
            name = prompt_data["name"].strip()
            if len(name) > 100:
                return False, "提示词名称不能超过100个字符"
                
            # 验证内容长度
            content = prompt_data["content"].strip()
            if len(content) > 10000:
                return False, "提示词内容不能超过10000个字符"
                
            return True, "提示词数据验证通过"
            
        except Exception as e:
            return False, f"验证提示词数据时出错: {str(e)}"
            

            
    def prompts_file_exists(self) -> bool:
        """检查提示词文件是否存在"""
        return os.path.exists(self.prompts_file)
        
    def validate_prompts_file(self) -> bool:
        """验证提示词文件格式"""
        try:
            if not os.path.exists(self.prompts_file):
                return False
                
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 检查基本结构
            required_keys = ["prompts", "metadata"]
            for key in required_keys:
                if key not in data:
                    return False
                    
            return True
            
        except Exception:
            return False
            
    def repair_prompts_file(self) -> bool:
        """修复提示词文件 - 创建空的数据结构，不包含默认提示词"""
        try:
            # 创建空的数据结构，不包含默认提示词
            self.prompts_data = {
                "prompts": [],
                "metadata": {
                    "version": "1.0",
                    "total_prompts": 0,
                    "last_updated": self._get_current_timestamp()
                }
            }
            return self.save_prompts()
            
        except Exception as e:
            print(f"修复提示词文件时出错: {e}")
            return False
            
    def backup_to_file(self, backup_file: str) -> bool:
        """备份提示词数据到指定文件"""
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompts_data, f, ensure_ascii=False, indent=2)
            return True
            
        except Exception as e:
            print(f"备份提示词数据时出错: {e}")
            return False
            
    def get_prompts_statistics(self) -> Dict[str, Any]:
        """获取提示词统计信息"""
        prompts = self.prompts_data.get("prompts", [])
        
        return {
            "total_prompts": len(prompts),
            "last_updated": self.prompts_data.get("metadata", {}).get("last_updated", "未知")
        }