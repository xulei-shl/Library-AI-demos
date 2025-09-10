#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证模块
提供各种数据验证功能，包括API配置验证、URL验证等
"""

import re
import urllib.parse
from typing import Dict, Any, Tuple, List


class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        # API Key格式正则表达式
        self.api_key_patterns = [
            r'^sk-[a-zA-Z0-9]{48,}$',  # OpenAI格式
            r'^pk-[a-zA-Z0-9]{48,}$',  # 其他格式
            r'^[a-zA-Z0-9]{32,}$',     # 通用格式
        ]
        
        # URL格式正则表达式
        self.url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
            r'(?::\d+)?'  # 可选端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, str]:
        """验证API Key格式"""
        if not api_key or not isinstance(api_key, str):
            return False, "API Key不能为空"
            
        api_key = api_key.strip()
        
        if len(api_key) < 10:
            return False, "API Key长度过短"
            
        # 检查是否匹配已知格式
        for pattern in self.api_key_patterns:
            if re.match(pattern, api_key):
                return True, "API Key格式正确"
                
        # 如果不匹配已知格式，给出警告但不阻止
        if api_key.startswith(('sk-', 'pk-')):
            return True, "API Key格式可能正确"
        else:
            return True, "API Key格式未知，请确认是否正确"
    
    def validate_url(self, url: str) -> Tuple[bool, str]:
        """验证URL格式"""
        if not url or not isinstance(url, str):
            return False, "URL不能为空"
            
        url = url.strip()
        
        # 基本格式检查
        if not self.url_pattern.match(url):
            return False, "URL格式不正确"
            
        try:
            # 使用urllib.parse进行更详细的验证
            parsed = urllib.parse.urlparse(url)
            
            if not parsed.scheme:
                return False, "URL缺少协议（http://或https://）"
                
            if parsed.scheme not in ['http', 'https']:
                return False, "URL协议必须是http或https"
                
            if not parsed.netloc:
                return False, "URL缺少主机名"
                
            return True, "URL格式正确"
            
        except Exception as e:
            return False, f"URL验证出错: {str(e)}"
    
    def validate_model_name(self, model: str) -> Tuple[bool, str]:
        """验证模型名称"""
        if not model or not isinstance(model, str):
            return False, "模型名称不能为空"
            
        model = model.strip()
        
        if len(model) < 2:
            return False, "模型名称过短"
            
        if len(model) > 100:
            return False, "模型名称过长"
            
        # 检查是否包含非法字符
        if re.search(r'[<>:"/\\|?*]', model):
            return False, "模型名称包含非法字符"
            
        return True, "模型名称格式正确"
    
    def validate_config(self, config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证完整配置"""
        errors = []
        
        # 验证API Key
        api_key = config_data.get('api_key', '')
        is_valid, message = self.validate_api_key(api_key)
        if not is_valid:
            errors.append(f"API Key: {message}")
            
        # 验证Base URL
        base_url = config_data.get('base_url', '')
        is_valid, message = self.validate_url(base_url)
        if not is_valid:
            errors.append(f"Base URL: {message}")
            
        # 验证模型名称
        model = config_data.get('model', '')
        is_valid, message = self.validate_model_name(model)
        if not is_valid:
            errors.append(f"模型名称: {message}")
            
        return len(errors) == 0, errors
    
    def validate_json_data(self, data: str) -> Tuple[bool, str]:
        """验证JSON数据格式"""
        if not data or not isinstance(data, str):
            return False, "数据不能为空"
            
        try:
            import json
            json.loads(data)
            return True, "JSON格式正确"
        except json.JSONDecodeError as e:
            return False, f"JSON格式错误: {str(e)}"
        except Exception as e:
            return False, f"验证JSON时出错: {str(e)}"
    
    def validate_file_path(self, file_path: str) -> Tuple[bool, str]:
        """验证文件路径"""
        if not file_path or not isinstance(file_path, str):
            return False, "文件路径不能为空"
            
        file_path = file_path.strip()
        
        # 检查路径长度
        if len(file_path) > 260:  # Windows路径长度限制
            return False, "文件路径过长"
            
        # 检查非法字符
        illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in illegal_chars:
            if char in file_path:
                return False, f"文件路径包含非法字符: {char}"
                
        return True, "文件路径格式正确"
    
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """验证邮箱格式"""
        if not email or not isinstance(email, str):
            return False, "邮箱地址不能为空"
            
        email = email.strip()
        
        # 简单的邮箱格式验证
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        if not email_pattern.match(email):
            return False, "邮箱格式不正确"
            
        return True, "邮箱格式正确"
    
    def validate_port(self, port: str) -> Tuple[bool, str]:
        """验证端口号"""
        if not port or not isinstance(port, str):
            return False, "端口号不能为空"
            
        try:
            port_num = int(port.strip())
            if port_num < 1 or port_num > 65535:
                return False, "端口号必须在1-65535之间"
            return True, "端口号格式正确"
        except ValueError:
            return False, "端口号必须是数字"
        except Exception as e:
            return False, f"验证端口号时出错: {str(e)}"
    
    def sanitize_input(self, input_str: str, max_length: int = 1000) -> str:
        """清理用户输入"""
        if not input_str or not isinstance(input_str, str):
            return ""
            
        # 移除首尾空白
        cleaned = input_str.strip()
        
        # 限制长度
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
            
        # 移除控制字符
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        return cleaned
    
    def validate_positive_integer(self, value: str) -> Tuple[bool, str]:
        """验证正整数"""
        if not value or not isinstance(value, str):
            return False, "值不能为空"
            
        try:
            num = int(value.strip())
            if num <= 0:
                return False, "值必须是正整数"
            return True, "值格式正确"
        except ValueError:
            return False, "值必须是整数"
        except Exception as e:
            return False, f"验证时出错: {str(e)}"
    
    def validate_float_range(self, value: str, min_val: float = None, max_val: float = None) -> Tuple[bool, str]:
        """验证浮点数范围"""
        if not value or not isinstance(value, str):
            return False, "值不能为空"
            
        try:
            num = float(value.strip())
            
            if min_val is not None and num < min_val:
                return False, f"值不能小于{min_val}"
                
            if max_val is not None and num > max_val:
                return False, f"值不能大于{max_val}"
                
            return True, "值格式正确"
        except ValueError:
            return False, "值必须是数字"
        except Exception as e:
            return False, f"验证时出错: {str(e)}"