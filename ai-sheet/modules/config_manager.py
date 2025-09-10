#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型配置管理模块
负责管理AI-Sheet的多个大模型API配置信息
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests


class MultiModelConfigManager:
    """多模型配置管理器"""
    def __init__(self, config_file: str = None):
        if config_file is None:
            config_file = os.path.join("config", "models_config.json")
        self.config_file = config_file
        self.config_data = {}
        self.load_config()

        
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置结构"""
        return {
            "models": [],
            "default_paths": {
                "excel_path": "",
                "output_dir": ""
            },
            "settings": {
                "default_model_index": 0,
                "auto_save": True
            },
            "excel": {
                "supported_formats": [".xlsx"],
                "max_rows": 5000,
                "max_file_size_mb": 50,
                "preview_rows": 10
            },
            "ui": {
                "theme": "default"
            }
        }
        
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def _ensure_config_integrity(self) -> None:
        """确保配置完整性"""
        default_config = self.get_default_config()
        for key in default_config:
            if key not in self.config_data:
                self.config_data[key] = default_config[key]
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                self._ensure_config_integrity()
            else:
                # 创建默认配置
                self.config_data = self.get_default_config()
                self.save_config()
                
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {e}")
            # 备份损坏的配置文件
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.backup"
                os.rename(self.config_file, backup_file)
                print(f"已将损坏的配置文件备份为: {backup_file}")
            
            # 创建新配置
            self.config_data = self.get_default_config()
            self.save_config()
            
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            self.config_data = self.get_default_config()
            
        return self.config_data.copy()
    
    def reload_config(self) -> Dict[str, Any]:
        """重新加载配置文件（强制从文件读取最新数据）"""
        print("🔄 强制重新加载配置文件...")
        return self.load_config()
        


    def save_config(self, config_data: Optional[Dict[str, Any]] = None) -> bool:
        """保存配置到文件"""
        try:
            if config_data is None:
                config_data = self.config_data
                
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
                
            # 更新内存中的配置
            self.config_data = config_data.copy()
            
            # 设置文件权限（仅当前用户可读写）
            try:
                import stat
                os.chmod(self.config_file, stat.S_IRUSR | stat.S_IWUSR)
            except:
                pass  # 在某些系统上可能不支持
                
            return True
            
        except Exception as e:
            print(f"保存配置文件时出错: {e}")
            return False
            
    def get_config(self, key: str = None) -> Any:
        """获取配置值"""
        if key is None:
            return self.config_data.copy()
        return self.config_data.get(key)
        
    def set_config(self, key: str, value: Any) -> bool:
        """设置配置值"""
        try:
            self.config_data[key] = value
            return self.save_config()
        except Exception as e:
            print(f"设置配置值时出错: {e}")
            return False

    # ========== 模型管理方法 ==========
    
    def get_all_models(self) -> List[Dict[str, str]]:
        """获取所有模型配置"""
        return self.config_data.get("models", [])
        
    def add_model(self, model_config: Dict[str, str]) -> bool:
        """添加新模型配置"""
        try:
            # 验证模型配置
            is_valid, error_msg = self.validate_model_config(model_config)
            if not is_valid:
                print(f"模型配置验证失败: {error_msg}")
                return False
                
            # 检查模型名称是否重复
            if self.is_model_name_exists(model_config["name"]):
                print(f"模型名称 '{model_config['name']}' 已存在")
                return False
                
            # 添加时间戳
            current_time = self._get_current_timestamp()
            new_model = model_config.copy()
            new_model["created_at"] = current_time
            new_model["updated_at"] = current_time
                
            # 添加模型
            self.config_data["models"].append(new_model)
            return self.save_config()
            
        except Exception as e:
            print(f"添加模型时出错: {e}")
            return False
            
    def update_model(self, index: int, model_config: Dict[str, str]) -> bool:
        """更新指定索引的模型配置"""
        try:
            if not (0 <= index < len(self.config_data["models"])):
                print(f"模型索引 {index} 超出范围")
                return False
                
            # 验证模型配置
            is_valid, error_msg = self.validate_model_config(model_config)
            if not is_valid:
                print(f"模型配置验证失败: {error_msg}")
                return False
                
            # 检查模型名称是否与其他模型重复
            if self.is_model_name_exists(model_config["name"], exclude_index=index):
                print(f"模型名称 '{model_config['name']}' 已存在")
                return False
                
            # 保留原创建时间，更新修改时间
            old_model = self.config_data["models"][index]
            updated_model = model_config.copy()
            updated_model["created_at"] = old_model.get("created_at", self._get_current_timestamp())
            updated_model["updated_at"] = self._get_current_timestamp()
                
            # 更新模型
            self.config_data["models"][index] = updated_model
            return self.save_config()
            
        except Exception as e:
            print(f"更新模型时出错: {e}")
            return False
            
    def delete_model(self, index: int) -> bool:
        """删除指定索引的模型配置"""
        try:
            if not (0 <= index < len(self.config_data["models"])):
                print(f"模型索引 {index} 超出范围")
                return False
                
            # 删除模型
            del self.config_data["models"][index]
            
            # 调整默认模型索引
            default_index = self.config_data["settings"]["default_model_index"]
            if default_index >= len(self.config_data["models"]):
                self.config_data["settings"]["default_model_index"] = max(0, len(self.config_data["models"]) - 1)
            elif default_index > index:
                self.config_data["settings"]["default_model_index"] = default_index - 1
                
            return self.save_config()
            
        except Exception as e:
            print(f"删除模型时出错: {e}")
            return False
            
    def get_model(self, index: int) -> Optional[Dict[str, str]]:
        """获取指定索引的模型配置"""
        if 0 <= index < len(self.config_data["models"]):
            return self.config_data["models"][index].copy()
        return None
        
    def get_model_by_name(self, name: str) -> Optional[Dict[str, str]]:
        """根据名称获取模型配置"""
        for model in self.config_data["models"]:
            if model["name"] == name:
                return model.copy()
        return None
        
    def is_model_name_exists(self, name: str, exclude_index: Optional[int] = None) -> bool:
        """检查模型名称是否已存在"""
        for i, model in enumerate(self.config_data["models"]):
            if exclude_index is not None and i == exclude_index:
                continue
            if model["name"] == name:
                return True
        return False
        
    def get_default_model(self) -> Optional[Dict[str, str]]:
        """获取默认模型配置"""
        default_index = self.config_data["settings"]["default_model_index"]
        return self.get_model(default_index)
        
    def set_default_model(self, index: int) -> bool:
        """设置默认模型"""
        if 0 <= index < len(self.config_data["models"]):
            self.config_data["settings"]["default_model_index"] = index
            return self.save_config()
        return False
        
    def is_configured(self) -> bool:
        """检查是否已配置（至少有一个有效的模型配置）"""
        models = self.config_data.get("models", [])
        if not models:
            return False
            
        # 检查是否至少有一个完整配置的模型
        for model in models:
            is_valid, _ = self.validate_model_config(model)
            if is_valid:
                return True
                
        return False

    # ========== 路径配置管理 ==========
    
    def get_default_paths(self) -> Dict[str, str]:
        """获取默认路径配置"""
        return self.config_data.get("default_paths", {"excel_path": "", "output_dir": ""})
        
    def set_default_paths(self, excel_path: str = None, output_dir: str = None) -> bool:
        """设置默认路径配置"""
        try:
            if "default_paths" not in self.config_data:
                self.config_data["default_paths"] = {}
                
            if excel_path is not None:
                self.config_data["default_paths"]["excel_path"] = excel_path
            if output_dir is not None:
                self.config_data["default_paths"]["output_dir"] = output_dir
                
            return self.save_config()
        except Exception as e:
            print(f"设置默认路径时出错: {e}")
            return False
            
    # ========== API连接测试 ==========
    
    def test_api_connection(self, model_config: Optional[Dict[str, str]] = None) -> bool:
        """测试API连接"""
        if model_config is None:
            model_config = self.get_default_model()
            if model_config is None:
                return False
            
        try:
            api_key = model_config.get("api_key", "").strip()
            base_url = model_config.get("base_url", "").strip()
            
            if not api_key or not base_url:
                return False
                
            # 构建测试请求
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 使用models端点进行测试（通常比较轻量）
            test_url = f"{base_url.rstrip('/')}/models"
            
            response = requests.get(
                test_url, 
                headers=headers, 
                timeout=10
            )
            
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            print(f"API连接测试失败: {e}")
            return False
        except Exception as e:
            print(f"API连接测试出错: {e}")
            return False
            
    # ========== 配置验证 ==========
    
    def validate_model_config(self, model_config: Dict[str, str]) -> tuple[bool, str]:
        """验证单个模型配置"""
        try:
            # 检查必填字段（时间戳字段是可选的，会自动添加）
            required_fields = ["name", "api_key", "base_url", "model_id"]
            for field in required_fields:
                if field not in model_config or not str(model_config[field]).strip():
                    return False, f"字段 '{field}' 不能为空"
                    
            # 验证模型名称
            name = model_config["name"].strip()
            if len(name) < 1:
                return False, "模型名称不能为空"

            # 验证Base URL格式
            base_url = model_config["base_url"].strip()
            if not base_url.startswith(("http://", "https://")):
                return False, "Base URL必须以http://或https://开头"

            return True, "模型配置验证通过"
            
        except Exception as e:
            return False, f"验证模型配置时出错: {str(e)}"

    # ========== 工具方法 ==========
    
    def backup_config(self) -> bool:
        """备份当前配置"""
        try:
            if os.path.exists(self.config_file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{self.config_file}.backup_{timestamp}"
                
                import shutil
                shutil.copy2(self.config_file, backup_file)
                print(f"配置已备份到: {backup_file}")
                return True
            return False
        except Exception as e:
            print(f"备份配置时出错: {e}")
            return False
            
    def restore_config(self, backup_file: str) -> bool:
        """从备份恢复配置"""
        try:
            if os.path.exists(backup_file):
                import shutil
                shutil.copy2(backup_file, self.config_file)
                self.load_config()  # 重新加载配置
                print(f"已从备份恢复配置: {backup_file}")
                return True
            return False
        except Exception as e:
            print(f"恢复配置时出错: {e}")
            return False
            
    def get_config_status(self) -> Dict[str, Any]:
        """获取配置状态信息"""
        models = self.config_data.get("models", [])
        default_model = self.get_default_model()
        
        # 获取配置文件的最后修改时间
        last_updated = "未知"
        if os.path.exists(self.config_file):
            try:
                mtime = os.path.getmtime(self.config_file)
                last_updated = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        return {
            "is_configured": self.is_configured(),
            "config_file_exists": os.path.exists(self.config_file),
            "config_file_size": os.path.getsize(self.config_file) if os.path.exists(self.config_file) else 0,
            "last_updated": last_updated,
            "models_count": len(models),
            "default_model_name": default_model["name"] if default_model else "无",
            "default_paths": self.get_default_paths()
        }
        
    def get_excel_config(self) -> Dict[str, Any]:
        """获取Excel相关配置"""
        if "excel" not in self.config_data:
            self.config_data["excel"] = self.get_default_config()["excel"]
            self.save_config()
        
        return self.config_data["excel"]
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI相关配置"""
        if "ui" not in self.config_data:
            self.config_data["ui"] = self.get_default_config()["ui"]
            self.save_config()
        
        return self.config_data["ui"]
        
    def export_config(self, export_file: str) -> bool:
        """导出配置到指定文件"""
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            print(f"配置已导出到: {export_file}")
            return True
        except Exception as e:
            print(f"导出配置时出错: {e}")
            return False
            
    def import_config(self, import_file: str) -> bool:
        """从指定文件导入配置"""
        try:
            if not os.path.exists(import_file):
                print(f"导入文件不存在: {import_file}")
                return False
                
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
                
            # 验证导入的配置结构
            if "models" not in imported_config:
                print("导入的配置文件格式不正确")
                return False
                
            # 备份当前配置
            self.backup_config()
            
            # 应用导入的配置
            self.config_data = imported_config
            
            # 确保配置完整性
            self._ensure_config_integrity()
                    
            # 保存配置
            if self.save_config():
                print(f"配置已从 {import_file} 导入成功")
                return True
            else:
                print("保存导入的配置失败")
                return False
                
        except Exception as e:
            print(f"导入配置时出错: {e}")
            return False


# 为了向后兼容，保留原来的类名作为别名
ConfigManager = MultiModelConfigManager

