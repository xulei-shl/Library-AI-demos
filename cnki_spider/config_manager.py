import json
import os
from datetime import datetime

class ConfigManager:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.get_default_config()
        else:
            # 如果配置文件不存在，创建默认配置
            default_config = self.get_default_config()
            self.save_config(default_config)
            return default_config
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            "default_settings": {
                "keyword": "",
                "time_range": "recent_year",  # 默认使用"最近一年"
                "start_year": None,  # 当使用"最近一年"时为None
                "end_year": None,    # 当使用"最近一年"时为None
                "check_core": False,
                "max_results": 50,
                "output_path": os.path.join(os.getcwd(), "data"),  # 默认输出路径
                "ai_model": "glm-4.5-flash",
                "api_key": "",
                "base_url": "https://open.bigmodel.cn/api/paas/v4/",
                "temperature": 0.6,
                "top_p": 0.9
            },
            "ui_settings": {
                "window_title": "CNKI文献爬虫工具",
                "window_size": "800x600",
                "theme": "default"
            },
            "download_settings": {
                "base_folder": "data",
                "create_topic_folder": True,
                "filename_format": "CNKI_export_{timestamp}.xls"
            }
        }
    
    def save_config(self, config=None):
        """保存配置文件"""
        if config is None:
            config = self.config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get_setting(self, category, key, default=None):
        """获取特定设置"""
        return self.config.get(category, {}).get(key, default)
    
    def set_setting(self, category, key_or_dict, value=None):
        """设置特定配置"""
        if category not in self.config:
            self.config[category] = {}
        
        if isinstance(key_or_dict, dict):
            # 如果传入的是字典，直接设置整个分类
            self.config[category] = key_or_dict
        else:
            # 如果传入的是键值对
            if isinstance(key_or_dict, str):
                self.config[category][key_or_dict] = value
            else:
                raise TypeError(f"键必须是字符串类型，不能是 {type(key_or_dict)}")
        
        return self.save_config()
    
    def get_default_settings(self):
        """获取默认搜索设置"""
        return self.config.get("default_settings", {})
    
    def update_default_settings(self, **kwargs):
        """更新默认搜索设置（只更新指定的配置项，保留其他配置）"""
        if "default_settings" not in self.config:
            self.config["default_settings"] = {}
        
        # 只更新传入的配置项，保留其他现有配置
        for key, value in kwargs.items():
            self.config["default_settings"][key] = value
        
        return self.save_config()
    
    def update_search_settings_only(self, **kwargs):
        """仅更新检索相关的设置，不影响其他配置"""
        search_keys = ['keyword', 'time_range', 'start_year', 'end_year', 'check_core', 'max_results', 'output_path']
        
        if "default_settings" not in self.config:
            self.config["default_settings"] = {}
        
        # 只更新检索相关的配置项
        for key, value in kwargs.items():
            if key in search_keys:
                self.config["default_settings"][key] = value
        
        return self.save_config()
    
    def reset_to_default(self):
        """重置为默认配置"""
        self.config = self.get_default_config()
        return self.save_config()
    
    def reload_config(self):
        """重新加载配置文件"""
        self.config = self.load_config()
        return self.config
