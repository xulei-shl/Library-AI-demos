#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown文本显示组件
支持基本的Markdown格式渲染
"""

import tkinter as tk
from tkinter import scrolledtext
import re


class MarkdownText(scrolledtext.ScrolledText):
    """支持Markdown格式的文本组件"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # 配置标签样式
        self.setup_markdown_styles()
        
        # 绑定内容变化事件
        self.bind('<KeyRelease>', self.on_content_change)
        self.bind('<Button-1>', self.on_content_change)
        
    def setup_markdown_styles(self):
        """设置Markdown样式标签"""
        # 标题样式
        self.tag_configure("h1", font=("微软雅黑", 16, "bold"), foreground="#2c3e50")
        self.tag_configure("h2", font=("微软雅黑", 14, "bold"), foreground="#34495e")
        self.tag_configure("h3", font=("微软雅黑", 12, "bold"), foreground="#7f8c8d")
        
        # 粗体和斜体
        self.tag_configure("bold", font=("微软雅黑", 10, "bold"))
        self.tag_configure("italic", font=("微软雅黑", 10, "italic"))
        
        # 代码样式
        self.tag_configure("code", font=("Consolas", 9), background="#f8f9fa", foreground="#e74c3c")
        self.tag_configure("code_block", font=("Consolas", 9), background="#f8f9fa", foreground="#2c3e50")
        
        # 列表样式
        self.tag_configure("list_item", lmargin1=20, lmargin2=20)
        
        # 引用样式
        self.tag_configure("quote", lmargin1=20, lmargin2=20, foreground="#7f8c8d", font=("微软雅黑", 10, "italic"))
        
    def set_markdown_content(self, content):
        """设置Markdown内容并渲染"""
        # 清空当前内容
        self.delete(1.0, tk.END)
        
        # 插入内容
        self.insert(1.0, content)
        
        # 渲染Markdown
        self.render_markdown()
        
    def get_plain_content(self):
        """获取纯文本内容"""
        return self.get(1.0, tk.END).rstrip('\n')
        
    def on_content_change(self, event=None):
        """内容变化时重新渲染"""
        # 延迟渲染，避免频繁更新
        self.after_idle(self.render_markdown)
        
    def render_markdown(self):
        """渲染Markdown格式"""
        # 移除所有现有标签
        for tag in self.tag_names():
            if tag not in ["sel", "current"]:
                self.tag_delete(tag)
        
        content = self.get(1.0, tk.END)
        lines = content.split('\n')
        
        current_pos = "1.0"
        
        # 代码块状态管理
        in_code_block = False
        code_block_start = 0
        
        for i, line in enumerate(lines):
            line_start = f"{i+1}.0"
            line_end = f"{i+1}.end"
            
            # 代码块处理
            if line.strip().startswith('```'):
                if not in_code_block:
                    # 代码块开始
                    in_code_block = True
                    code_block_start = i + 1
                    self.tag_add("code_block", line_start, line_end)
                else:
                    # 代码块结束
                    in_code_block = False
                    block_start = f"{code_block_start}.0"
                    block_end = f"{i+1}.end"
                    self.tag_add("code_block", block_start, block_end)
                continue
            
            # 如果在代码块中，应用代码块样式
            if in_code_block:
                self.tag_add("code_block", line_start, line_end)
                continue
            
            # 标题渲染
            if line.startswith('# '):
                self.tag_add("h1", line_start, line_end)
            elif line.startswith('## '):
                self.tag_add("h2", line_start, line_end)
            elif line.startswith('### '):
                self.tag_add("h3", line_start, line_end)
            
            # 列表项渲染
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                self.tag_add("list_item", line_start, line_end)
            
            # 引用渲染
            elif line.strip().startswith('> '):
                self.tag_add("quote", line_start, line_end)
                continue
            
            # 行内格式渲染
            self.render_inline_formats(line, i+1)
    
    def render_inline_formats(self, line, line_num):
        """渲染行内格式"""
        # 粗体 **text**
        bold_pattern = r'\*\*(.*?)\*\*'
        for match in re.finditer(bold_pattern, line):
            start_col = match.start()
            end_col = match.end()
            start_pos = f"{line_num}.{start_col}"
            end_pos = f"{line_num}.{end_col}"
            self.tag_add("bold", start_pos, end_pos)
        
        # 斜体 *text*
        italic_pattern = r'(?<!\*)\*([^*]+)\*(?!\*)'
        for match in re.finditer(italic_pattern, line):
            start_col = match.start()
            end_col = match.end()
            start_pos = f"{line_num}.{start_col}"
            end_pos = f"{line_num}.{end_col}"
            self.tag_add("italic", start_pos, end_pos)
        
        # 行内代码 `code`
        code_pattern = r'`([^`]+)`'
        for match in re.finditer(code_pattern, line):
            start_col = match.start()
            end_col = match.end()
            start_pos = f"{line_num}.{start_col}"
            end_pos = f"{line_num}.{end_col}"
            self.tag_add("code", start_pos, end_pos)