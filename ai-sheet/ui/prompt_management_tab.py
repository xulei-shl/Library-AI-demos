#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词管理Tab模块
提供提示词库的检索和编辑界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import os
from typing import Dict, List, Optional

# 添加modules目录到路径
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'modules'))
from prompt_manager import PromptManager
from .markdown_text import MarkdownText


class PromptManagementTab:
    """提示词管理Tab主类"""
    
    def __init__(self, parent, prompt_change_callback=None):
        self.parent = parent
        self.prompt_manager = PromptManager()
        self.current_prompt_id = None
        self.prompt_data = {}
        self.prompt_change_callback = prompt_change_callback
        
        # 界面变量
        self.name_var = tk.StringVar()
        
        # 创建界面
        self.setup_ui()
        
        # 确保默认提示词存在
        self.prompt_manager.ensure_default_prompts()
        
        # 加载提示词列表
        self.load_prompt_list()
        
    def setup_ui(self):
        """创建界面元素"""
        # 创建主框架
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建左右分割的PanedWindow
        self.paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # 左侧框架 - 提示词列表
        self.left_frame = ttk.LabelFrame(self.paned_window, text="📋 提示词列表", padding=15)
        
        # 创建左侧内容
        self.create_left_panel()
        
        # 右侧框架 - 提示词编辑
        self.right_frame = ttk.LabelFrame(self.paned_window, text="✏️ 提示词编辑", padding=15)
        
        # 创建右侧内容框架
        self.form_frame = ttk.Frame(self.right_frame)
        self.form_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建右侧内容
        self.create_right_panel()

        # 添加到PanedWindow
        self.paned_window.add(self.left_frame, weight=1)
        self.paned_window.add(self.right_frame, weight=2)

        # 延迟设置分割比例
        self.parent.after(100, self.set_paned_position)
        
    def set_paned_position(self):
        """设置分割窗口位置"""
        try:
            # 设置左侧面板宽度为320像素
            self.paned_window.sashpos(0, 320)
        except:
            pass
            
    def create_left_panel(self):
        """创建左侧面板"""
        # 提示词列表框架
        list_container = ttk.Frame(self.left_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建列表框和滚动条
        self.prompt_listbox = tk.Listbox(
            list_container, 
            font=("微软雅黑", 10),
            selectmode=tk.SINGLE,
            height=18,
            activestyle='dotbox',
            selectbackground='#0078d4',
            selectforeground='white'
        )
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.prompt_listbox.yview)
        self.prompt_listbox.configure(yscrollcommand=scrollbar.set)

        self.prompt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定列表选择事件
        self.prompt_listbox.bind('<<ListboxSelect>>', self.on_prompt_select)

        # 新增按钮
        add_btn = ttk.Button(self.left_frame, text="➕ 新增提示词", command=self.create_new_prompt)
        add_btn.pack(pady=(15, 0), fill=tk.X)

        refresh_btn = ttk.Button(self.left_frame, text="🔄 刷新列表",
                             command=self.reload_prompt_list)
        refresh_btn.pack(pady=(8, 0), fill=tk.X)
        
    def create_right_panel(self):
        """创建右侧面板"""
        # 清空表单框架
        for widget in self.form_frame.winfo_children():
            widget.destroy()
            
        # 创建滚动框架
        canvas = tk.Canvas(self.form_frame)
        scrollbar_form = ttk.Scrollbar(self.form_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_form.set)

        # 提示词名称
        name_frame = ttk.Frame(scrollable_frame)
        name_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(name_frame, text="名称:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var, width=40, font=("微软雅黑", 10))
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, padx=(15, 0), pady=8)

        # 配置列的权重
        name_frame.columnconfigure(1, weight=1)

        # 内容编辑区
        content_container = ttk.Frame(scrollable_frame)
        content_container.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.content_text = MarkdownText(
            content_container,
            width=60,
            height=20,
            font=("微软雅黑", 10),
            wrap=tk.WORD
        )
        self.content_text.pack(fill=tk.BOTH, expand=True)

        # 按钮框架
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # 保存按钮
        self.save_btn = ttk.Button(button_frame, text="💾 保存", command=self.save_prompt)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 重置按钮
        self.reset_btn = ttk.Button(button_frame, text="🔄 重置", command=self.reset_form)
        self.reset_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 删除按钮
        self.delete_btn = ttk.Button(button_frame, text="🗑️ 删除", command=self.delete_prompt)
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 布局滚动组件
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_form.pack(side="right", fill="y")

        # 初始状态禁用按钮
        self.disable_editing()
        
    def load_prompt_list(self):
        """加载并显示提示词列表"""
        try:
            # 从prompt_manager获取所有提示词
            prompts = self.prompt_manager.get_all_prompts()
            
            # 清空当前列表
            self.prompt_listbox.delete(0, tk.END)
            
            if not prompts:
                self.prompt_listbox.insert(tk.END, "暂无提示词")
                self.prompt_listbox.config(state='disabled')
                self.prompt_data = {}
            else:
                # 启用列表框
                self.prompt_listbox.config(state='normal')
                
                # 按名称排序
                sorted_prompts = sorted(prompts, key=lambda x: x.get('name', ''))
                
                # 添加到列表框
                for i, prompt in enumerate(sorted_prompts):
                    display_text = f"🤖 {prompt.get('name', '未命名')}"
                    self.prompt_listbox.insert(tk.END, display_text)
                    
                # 存储完整数据用于后续操作
                self.prompt_data = {i: prompt for i, prompt in enumerate(sorted_prompts)}
                
        except Exception as e:
            messagebox.showerror("错误", f"加载提示词列表失败: {str(e)}")
            
    def on_prompt_select(self, event):
        """处理提示词选择事件"""
        selection = self.prompt_listbox.curselection()
        
        if not selection:
            return
            
        # 检查是否是提示信息
        if not self.prompt_data:
            return
            
        index = selection[0]
        prompt_data = self.prompt_data.get(index)
        
        if prompt_data:
            # 在右侧面板显示提示词详情
            self.display_prompt_details(prompt_data)
            
            # 记录当前选中的提示词ID
            self.current_prompt_id = prompt_data.get('id')
            
        self.enable_editing()

    def display_prompt_details(self, prompt_data: Dict):
        """在右侧面板显示提示词详情"""
        # 填充基本信息
        self.name_var.set(prompt_data.get('name', ''))
        
        # 填充内容编辑区并渲染Markdown
        content = prompt_data.get('content', '')
        
        # 确保内容不为空并设置Markdown内容
        if content:
            # 清理内容中可能存在的转义字符
            cleaned_content = content.replace('\\n', '\n').replace('\\t', '\t')
            self.content_text.set_markdown_content(cleaned_content)
        else:
            self.content_text.set_markdown_content("暂无内容")
        
        # 启用编辑功能
        self.enable_editing()
        
    def create_new_prompt(self):
        """创建新的提示词"""
        # 清空右侧编辑区
        self.clear_editing_area()
        
        # 设置默认值
        self.name_var.set("")
        
        # 清空内容区并设置默认内容
        self.content_text.set_markdown_content("")
        
        # 重置当前提示词ID
        self.current_prompt_id = None
        
        # 取消列表选择
        self.prompt_listbox.selection_clear(0, tk.END)
        
        # 启用编辑
        self.enable_editing()
        
        # 焦点到名称输入框
        self.name_entry.focus_set()
        self.name_entry.select_range(0, tk.END)
        
    def save_prompt(self):
        """保存当前编辑的提示词"""
        try:
            # 验证必填字段
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("错误", "提示词名称不能为空")
                return
                
            content = self.content_text.get_plain_content()
            if not content:
                messagebox.showerror("错误", "提示词内容不能为空")
                return
            
            # 构建提示词数据
            prompt_data = {
                'name': name,
                'content': content
            }
            
            # 如果是更新现有提示词，保留ID
            if self.current_prompt_id:
                prompt_data['id'] = self.current_prompt_id
            
            # 调用prompt_manager保存
            success = self.prompt_manager.save_prompt(prompt_data)
            
            if success:
                messagebox.showinfo("成功", "提示词保存成功")
                # 刷新列表
                self.load_prompt_list()
                # 重新选中当前项
                if self.current_prompt_id:
                    self.select_prompt_by_id(self.current_prompt_id)
                else:
                    # 新添加的提示词，选择最后一个
                    if self.prompt_data:
                        last_index = len(self.prompt_data) - 1
                        self.prompt_listbox.selection_set(last_index)
                        self.on_prompt_select(None)
                
                # 通知提示词变更 - 强制刷新公式生成页面的候选列表
                print("🔄 提示词保存成功，正在通知公式生成页面刷新...")
                if self.prompt_change_callback:
                    try:
                        self.prompt_change_callback()
                        print("✅ 提示词变更通知发送成功")
                    except Exception as e:
                        print(f"❌ 提示词变更通知失败: {e}")
            else:
                messagebox.showerror("错误", "保存失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存提示词时发生错误: {str(e)}")
            
    def delete_prompt(self):
        """删除当前选中的提示词"""
        if not self.current_prompt_id:
            messagebox.showwarning("警告", "请先选择要删除的提示词")
            return
        
        # 获取当前提示词信息
        prompt_name = self.name_var.get()
        
        # 确认删除
        result = messagebox.askyesno(
            "确认删除", 
            f"确定要删除提示词 '{prompt_name}' 吗？\n此操作不可撤销。"
        )
        
        if result:
            try:
                # 调用prompt_manager删除
                success = self.prompt_manager.delete_prompt(self.current_prompt_id)
                
                if success:
                    messagebox.showinfo("成功", "提示词删除成功")
                    # 刷新列表
                    self.load_prompt_list()
                    # 清空编辑区
                    self.clear_editing_area()
                    self.current_prompt_id = None
                    self.disable_editing()
                    
                    # 通知提示词变更 - 强制刷新公式生成页面的候选列表
                    print("🔄 提示词删除成功，正在通知公式生成页面刷新...")
                    if self.prompt_change_callback:
                        try:
                            self.prompt_change_callback()
                            print("✅ 提示词变更通知发送成功")
                        except Exception as e:
                            print(f"❌ 提示词变更通知失败: {e}")
                else:
                    messagebox.showerror("错误", "删除失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"删除提示词时发生错误: {str(e)}")

    def reload_prompt_list(self):
        """从磁盘重新加载 prompts.json 并刷新界面"""
        self.prompt_manager.reload_prompts()   # 强制读文件
        self.load_prompt_list()                # 重新填充 Listbox                
                
    def reset_form(self):
        """重置表单到上次保存的状态"""
        if not self.current_prompt_id:
            # 如果是新建状态，清空表单
            self.clear_editing_area()
            self.create_new_prompt()
        else:
            # 重新加载当前提示词
            prompt_data = self.prompt_manager.get_prompt_by_id(self.current_prompt_id)
            if prompt_data:
                self.display_prompt_details(prompt_data)
                
    def clear_editing_area(self):
        """清空编辑区"""
        self.name_var.set("")
        self.content_text.set_markdown_content("")
        
    def enable_editing(self):
        """启用编辑功能"""
        self.save_btn.config(state='normal')
        self.reset_btn.config(state='normal')
        self.delete_btn.config(state='normal' if self.current_prompt_id else 'disabled')
        
    def disable_editing(self):
        """禁用编辑功能"""
        self.save_btn.config(state='disabled')
        self.reset_btn.config(state='disabled')
        self.delete_btn.config(state='disabled')
        
    def select_prompt_by_id(self, prompt_id: str):
        """根据ID选中提示词"""
        for index, prompt in self.prompt_data.items():
            if prompt.get('id') == prompt_id:
                self.prompt_listbox.selection_set(index)
                self.prompt_listbox.see(index)
                break
                
    def get_prompt_for_selection(self):
        """为其他模块提供提示词选择接口"""
        return {
            'prompts': self.prompt_manager.get_all_prompts(),
            'default_prompt_id': 'default_chat'
        }
            
    def get_prompt_manager(self) -> PromptManager:
        """获取提示词管理器实例"""
        return self.prompt_manager