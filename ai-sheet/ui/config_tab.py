#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型配置Tab模块
提供多个大模型API配置管理界面，左右布局
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
from typing import Dict, List, Optional

# 添加modules目录到路径
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'modules'))
from config_manager import MultiModelConfigManager


class MultiModelConfigTab:
    """多模型配置Tab主类"""
    
    def __init__(self, parent, config_change_callback=None):
        self.parent = parent
        self.config_manager = MultiModelConfigManager()
        self.current_model_index = None
        self.config_change_callback = config_change_callback
        
        # 界面变量
        self.model_name_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.base_url_var = tk.StringVar()
        self.model_id_var = tk.StringVar()
        self.excel_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        
        # 创建界面
        self.setup_ui()
        
        # 加载模型列表
        self.load_models_to_list()
    
    def setup_ui(self):
        """创建界面元素"""
        # 创建主框架
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建左右分割的PanedWindow
        self.paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # 左侧框架 - 模型列表
        self.left_frame = ttk.LabelFrame(self.paned_window, text="📋 模型列表", padding=15)
        
        # 模型列表框架
        list_container = ttk.Frame(self.left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        # 创建列表框和滚动条
        self.model_listbox = tk.Listbox(
            list_container, 
            font=("微软雅黑", 10),
            selectmode=tk.SINGLE,
            height=18,
            activestyle='dotbox',
            selectbackground='#0078d4',
            selectforeground='white'
        )
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.model_listbox.yview)
        self.model_listbox.configure(yscrollcommand=scrollbar.set)

        self.model_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定列表选择事件
        self.model_listbox.bind('<<ListboxSelect>>', self.on_model_select)

        # 添加按钮
        add_btn = ttk.Button(self.left_frame, text="➕ 添加新模型", command=self.add_new_model)
        add_btn.pack(pady=(15, 0), fill=tk.X)

        # 右侧框架 - 配置详情
        self.right_frame = ttk.LabelFrame(self.paned_window, text="⚙️ 配置详情", padding=15)
        
        # 配置表单框架
        self.form_frame = ttk.Frame(self.right_frame)
        self.form_frame.pack(fill=tk.BOTH, expand=True)

        # 添加到PanedWindow
        self.paned_window.add(self.left_frame, weight=1)
        self.paned_window.add(self.right_frame, weight=2)

        # 创建配置表单
        self.create_config_form()

        # 延迟设置分割比例
        self.parent.after(100, self.set_paned_position)
    
    def set_paned_position(self):
        """设置分割窗口位置"""
        try:
            # 设置左侧面板宽度为320像素
            self.paned_window.sashpos(0, 320)
        except:
            pass

    def create_config_form(self):
        """创建配置表单"""
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

        # API配置框架
        api_frame = ttk.LabelFrame(scrollable_frame, text="🔑 API配置", padding=15)
        api_frame.pack(fill=tk.X, pady=(0, 15))

        # 模型名称
        ttk.Label(api_frame, text="模型名称:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        model_name_entry = ttk.Entry(api_frame, textvariable=self.model_name_var, width=45, font=("微软雅黑", 10))
        model_name_entry.grid(row=0, column=1, sticky=tk.EW, padx=(15, 0), pady=8)

        # API Key
        ttk.Label(api_frame, text="API Key:", font=("微软雅黑", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=45, show="*", font=("微软雅黑", 10))
        api_key_entry.grid(row=1, column=1, sticky=tk.EW, padx=(15, 0), pady=8)

        # Base URL
        ttk.Label(api_frame, text="Base URL:", font=("微软雅黑", 10)).grid(row=2, column=0, sticky=tk.W, pady=8)
        base_url_entry = ttk.Entry(api_frame, textvariable=self.base_url_var, width=45, font=("微软雅黑", 10))
        base_url_entry.grid(row=2, column=1, sticky=tk.EW, padx=(15, 0), pady=8)

        # 模型ID
        ttk.Label(api_frame, text="模型ID:", font=("微软雅黑", 10)).grid(row=3, column=0, sticky=tk.W, pady=8)
        model_id_entry = ttk.Entry(api_frame, textvariable=self.model_id_var, width=45, font=("微软雅黑", 10))
        model_id_entry.grid(row=3, column=1, sticky=tk.EW, padx=(15, 0), pady=8)

        # 配置列的权重
        api_frame.columnconfigure(1, weight=1)

        # # 文件路径配置框架
        path_frame = ttk.LabelFrame(scrollable_frame, text="📁 文件路径配置", padding=15)
        path_frame.pack(fill=tk.X, pady=(0, 15))

        # # Excel文件路径
        # ttk.Label(path_frame, text="Excel文件路径:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        # excel_path_entry = ttk.Entry(path_frame, textvariable=self.excel_path_var, width=35, font=("微软雅黑", 10))
        # excel_path_entry.grid(row=0, column=1, sticky=tk.EW, padx=(15, 10), pady=8)
        
        # excel_browse_btn = ttk.Button(path_frame, text="📂 浏览", 
        #                             command=lambda: self.browse_file(self.excel_path_var, "Excel文件", "*.xlsx"))
        # excel_browse_btn.grid(row=0, column=2, pady=8)

        # # 输出目录
        # ttk.Label(path_frame, text="输出目录:", font=("微软雅黑", 10)).grid(row=1, column=0, sticky=tk.W, pady=8)
        # output_dir_entry = ttk.Entry(path_frame, textvariable=self.output_dir_var, width=35, font=("微软雅黑", 10))
        # output_dir_entry.grid(row=1, column=1, sticky=tk.EW, padx=(15, 10), pady=8)
        
        # output_browse_btn = ttk.Button(path_frame, text="📂 浏览", 
        #                              command=lambda: self.browse_directory(self.output_dir_var))
        # output_browse_btn.grid(row=1, column=2, pady=8)

        # 配置列的权重
        path_frame.columnconfigure(1, weight=1)

        # 按钮框架
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # 保存按钮
        self.save_btn = ttk.Button(button_frame, text="💾 保存配置", command=self.save_current_model)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 测试连接按钮
        self.test_btn = ttk.Button(button_frame, text="🔗 测试连接", command=self.test_connection)
        self.test_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 删除按钮
        self.delete_btn = ttk.Button(button_frame, text="🗑️ 删除配置", command=self.delete_current_model)
        self.delete_btn.pack(side=tk.LEFT)

        # 布局滚动组件
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_form.pack(side="right", fill="y")

        # 初始状态禁用按钮
        self.save_btn.config(state='disabled')
        self.test_btn.config(state='disabled')
        self.delete_btn.config(state='disabled')

    def load_models_to_list(self):
        """加载模型列表到界面"""
        # 清空列表
        self.model_listbox.delete(0, tk.END)
        
        # 获取所有模型
        models = self.config_manager.get_all_models()
        
        if not models:
            # 如果没有模型，显示提示信息
            self.model_listbox.insert(tk.END, "暂无配置的模型")
            self.model_listbox.config(state='disabled')
        else:
            # 启用列表框
            self.model_listbox.config(state='normal')
            
            # 添加每个模型到列表
            for i, model in enumerate(models):
                model_name = model.get("name", f"未命名模型{i+1}")
                model_id = model.get("model_id", "")
                
                # 构建显示名称
                display_name = f"🤖 {model_name}"
                if model_id:
                    display_name += f" ({model_id})"
                
                self.model_listbox.insert(tk.END, display_name)
        
        # 加载默认路径
        default_paths = self.config_manager.get_default_paths()
        self.excel_path_var.set(default_paths.get("excel_path", ""))
        self.output_dir_var.set(default_paths.get("output_dir", ""))

    def on_model_select(self, event):
        """模型选择事件处理"""
        selection = self.model_listbox.curselection()
        
        if selection:
            # 检查是否是提示信息
            models = self.config_manager.get_all_models()
            if not models:
                return
                
            self.current_model_index = selection[0]
            
            # 检查索引是否有效
            if self.current_model_index < len(models):
                self.load_model_to_form(self.current_model_index)
                self.enable_buttons()

    def load_model_to_form(self, index: int):
        """加载指定模型配置到表单"""
        model = self.config_manager.get_model(index)
        if model:
            self.model_name_var.set(model.get("name", ""))
            self.api_key_var.set(model.get("api_key", ""))
            self.base_url_var.set(model.get("base_url", ""))
            self.model_id_var.set(model.get("model_id", ""))

    def add_new_model(self):
        """添加新模型"""
        # 清空表单
        self.clear_form()
        
        # 设置默认值
        self.model_name_var.set("")
        self.base_url_var.set("https://api.openai.com/v1")
        self.model_id_var.set("")
        
        # 取消列表选择
        self.model_listbox.selection_clear(0, tk.END)
        self.current_model_index = None
        
        # 更新按钮状态
        self.save_btn.config(state='normal')
        self.test_btn.config(state='normal')
        self.delete_btn.config(state='disabled')

    def clear_form(self):
        """清空表单"""
        self.model_name_var.set("")
        self.api_key_var.set("")
        self.base_url_var.set("")
        self.model_id_var.set("")

    def enable_buttons(self):
        """启用按钮"""
        self.save_btn.config(state='normal')
        self.test_btn.config(state='normal')
        self.delete_btn.config(state='normal')

    def save_current_model(self):
        """保存当前模型配置"""
        # 验证输入
        if not self.validate_input():
            return

        model_data = {
            "name": self.model_name_var.get().strip(),
            "api_key": self.api_key_var.get().strip(),
            "base_url": self.base_url_var.get().strip(),
            "model_id": self.model_id_var.get().strip()
        }

        # 使用配置管理器验证
        is_valid, error_msg = self.config_manager.validate_model_config(model_data)
        if not is_valid:
            messagebox.showerror("验证错误", error_msg)
            return

        success = False
        if self.current_model_index is not None:
            # 更新现有模型
            success = self.config_manager.update_model(self.current_model_index, model_data)
        else:
            # 添加新模型
            success = self.config_manager.add_model(model_data)

        if success:
            # 保存路径配置
            self.config_manager.set_default_paths(
                excel_path=self.excel_path_var.get().strip(),
                output_dir=self.output_dir_var.get().strip()
            )
            
            messagebox.showinfo("成功", "模型配置保存成功！")
            self.load_models_to_list()
            
            # 重新选择当前模型
            if self.current_model_index is not None:
                self.model_listbox.selection_set(self.current_model_index)
            else:
                # 新添加的模型，选择最后一个
                models = self.config_manager.get_all_models()
                last_index = len(models) - 1
                if last_index >= 0:
                    self.model_listbox.selection_set(last_index)
                    self.current_model_index = last_index
            
            # 通知配置变更 - 强制刷新公式生成页面的候选列表
            print("🔄 配置保存成功，正在通知公式生成页面刷新...")
            if self.config_change_callback:
                try:
                    self.config_change_callback()
                    print("✅ 配置变更通知发送成功")
                except Exception as e:
                    print(f"❌ 配置变更通知失败: {e}")
        else:
            messagebox.showerror("错误", "保存模型配置失败")

    def validate_input(self) -> bool:
        """验证输入数据（基础验证）"""
        if not self.model_name_var.get().strip():
            messagebox.showerror("验证错误", "请输入模型名称")
            return False
        
        if not self.api_key_var.get().strip():
            messagebox.showerror("验证错误", "请输入API Key")
            return False
        
        if not self.base_url_var.get().strip():
            messagebox.showerror("验证错误", "请输入Base URL")
            return False
        
        if not self.model_id_var.get().strip():
            messagebox.showerror("验证错误", "请输入模型ID")
            return False
        
        return True

    def delete_current_model(self):
        """删除当前模型配置"""
        if self.current_model_index is None:
            return

        model = self.config_manager.get_model(self.current_model_index)
        if not model:
            return
            
        model_name = model["name"]
        result = messagebox.askyesno("确认删除", f"确定要删除模型配置 '{model_name}' 吗？")
        
        if result:
            # 删除模型
            if self.config_manager.delete_model(self.current_model_index):
                messagebox.showinfo("成功", "模型配置删除成功！")
                
                # 重新加载列表
                self.load_models_to_list()
                
                # 清空表单和重置状态
                self.clear_form()
                self.current_model_index = None
                self.save_btn.config(state='disabled')
                self.test_btn.config(state='disabled')
                self.delete_btn.config(state='disabled')
                
                # 通知配置变更 - 强制刷新公式生成页面的候选列表
                print("🔄 配置删除成功，正在通知公式生成页面刷新...")
                if self.config_change_callback:
                    try:
                        self.config_change_callback()
                        print("✅ 配置变更通知发送成功")
                    except Exception as e:
                        print(f"❌ 配置变更通知失败: {e}")
            else:
                messagebox.showerror("错误", "删除模型配置失败")

    def test_connection(self):
        """测试API连接"""
        if not self.validate_input():
            return

        try:
            self.test_btn.config(text="测试中...", state='disabled')
            self.parent.update()
            
            # 构建测试配置
            test_config = {
                "name": self.model_name_var.get().strip(),
                "api_key": self.api_key_var.get().strip(),
                "base_url": self.base_url_var.get().strip(),
                "model_id": self.model_id_var.get().strip()
            }
            
            # 使用配置管理器测试连接
            success = self.config_manager.test_api_connection(test_config)
            
            # 恢复按钮状态
            self.test_btn.config(text="测试连接", state='normal')
            
            if success:
                messagebox.showinfo("连接测试", "API连接测试成功！")
            else:
                messagebox.showerror("连接测试", "API连接测试失败！\n请检查API Key和Base URL是否正确。")
            
        except Exception as e:
            self.test_btn.config(text="测试连接", state='normal')
            messagebox.showerror("测试错误", f"连接测试出错：{str(e)}")

    def browse_file(self, var: tk.StringVar, title: str, filetypes: str):
        """浏览文件"""
        filename = filedialog.askopenfilename(
            title=f"选择{title}",
            filetypes=[(title, filetypes), ("所有文件", "*.*")]
        )
        if filename:
            var.set(filename)

    def browse_directory(self, var: tk.StringVar):
        """浏览目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            var.set(directory)

    def get_current_model_config(self) -> Optional[Dict]:
        """获取当前选中的模型配置"""
        if self.current_model_index is not None:
            return self.config_manager.get_model(self.current_model_index)
        return None

    def get_all_models(self) -> List[Dict]:
        """获取所有模型配置"""
        return self.config_manager.get_all_models()

    def get_default_paths(self) -> Dict:
        """获取默认路径配置"""
        return self.config_manager.get_default_paths()
        
    def get_config_manager(self) -> MultiModelConfigManager:
        """获取配置管理器实例"""
        return self.config_manager