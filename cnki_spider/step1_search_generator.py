"""
第一步：AI检索词生成模块
调用大模型生成检索条件（检索词），人工修改后，将完整检索配置写入默认json中
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime
from openai import OpenAI

class SearchGeneratorTab:
    """AI检索词生成Tab类"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.config = self.load_config()
        self.setup_ui()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("配置错误", f"无法加载配置文件: {str(e)}")
            return {}
    
    def setup_ui(self):
        """设置用户界面"""
        # TODO: 实现AI检索词生成界面
        pass
    
    def generate_search_terms(self, research_topic):
        """
        调用大模型生成检索词
        
        Args:
            research_topic (str): 研究主题
            
        Returns:
            str: 生成的检索词结果
        """
        try:
            # 获取系统提示词
            system_prompt = self.config.get('prompts', {}).get('prompt1', {}).get('content', '')
            if not system_prompt:
                return "错误：未找到系统提示词配置"
            
            # 构建用户提示词
            user_prompt = f"请根据以下研究主题生成检索词：\n\n{research_topic}"
            
            # 调用大模型API
            response = self.call_llm_api(system_prompt, user_prompt)
            return response
            
        except Exception as e:
            return f"生成检索词时出错: {str(e)}"
    
    def save_search_config(self, search_terms, time_range, journal_types, crawl_count):
        """
        保存检索配置到默认json文件
        
        Args:
            search_terms (list): 检索词列表
            time_range (dict): 时间范围配置
            journal_types (list): 期刊类型配置
            crawl_count (int): 爬取数量
        """
        try:
            # 更新配置文件中的默认设置
            if 'default_settings' not in self.config:
                self.config['default_settings'] = {}
            
            # 保存检索词（假设取第一个作为关键词）
            if search_terms:
                self.config['default_settings']['keyword'] = search_terms[0]
            
            # 保存其他配置
            if time_range:
                self.config['default_settings'].update(time_range)
            
            if crawl_count:
                self.config['default_settings']['max_results'] = crawl_count
            
            # 写入配置文件
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
                
            return True
            
        except Exception as e:
            messagebox.showerror("保存失败", f"保存配置时出错: {str(e)}")
            return False
    
    def call_llm_api(self, system_prompt, user_prompt):
        """
        调用大模型API
        
        Args:
            system_prompt (str): 系统提示词
            user_prompt (str): 用户提示词
            
        Returns:
            str: 大模型响应
        """
        try:
            # 从配置文件获取API参数
            default_settings = self.config.get('default_settings', {})
            api_key = default_settings.get('api_key', '')
            base_url = default_settings.get('base_url', 'https://open.bigmodel.cn/api/paas/v4/')
            model = default_settings.get('ai_model', 'glm-4.5-flash')
            temperature = default_settings.get('temperature', 0.6)
            top_p = default_settings.get('top_p', 0.9)
            
            if not api_key:
                raise Exception("API密钥未配置")
            
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            # 调用API
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                top_p=top_p
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"调用大模型API失败: {str(e)}")
    
# 为GUI模块提供的接口函数
def generate_search_terms_for_gui(research_topic):
    """
    为GUI模块提供的生成检索词接口
    
    Args:
        research_topic (str): 研究主题
        
    Returns:
        str: 生成的检索词结果
    """
    generator = SearchGeneratorTab(None)
    return generator.generate_search_terms(research_topic)

if __name__ == "__main__":
    # 测试代码
    root = tk.Tk()
    root.title("AI检索词生成测试")
    
    tab = SearchGeneratorTab(root)
    
    # 测试生成检索词
    test_topic = "智能体 图书馆"
    result = tab.generate_search_terms(test_topic)
    print("生成结果:")
    print(result)
    
    root.mainloop()
