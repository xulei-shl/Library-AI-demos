#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词生成Tab界面
提供结构化提示词生成的用户界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
from typing import Dict, Any, List, Optional, Callable
import pyperclip
import json
import uuid
from datetime import datetime

# 导入业务逻辑模块
from modules.prompt_generator import OptimizedPromptGenerator


class PromptInputPanel:
    """提示词输入面板组件"""
    
    def __init__(self, parent):
        self.parent = parent
        self.input_widgets = {}
        
        # 创建主框架
        self.frame = ttk.LabelFrame(parent, text="提示词结构化元素", padding="10")
        
        # 创建滚动区域
        self.canvas = tk.Canvas(self.frame, height=400)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 布局
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # 创建输入字段
        self._create_input_fields()
    
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _create_input_fields(self):
        """创建输入字段"""
        # 字段定义：(字段名, 显示名, 是否必填, 高度)
        fields = [
            ('role', '角色 (可选)👇', False, 2),
            ('background', '背景与目标 (可选)👇', False, 4),
            ('instruction', '指令与要求 (必填)*👇', True, 6),
            ('example', '输入与输出样例 (可选)👇', False, 4),
            ('output', '输出要求 (可选)👇', False, 3),
            ('constraint', '约束与限制 (可选)👆', False, 3)
        ]
        
        for i, (field_name, display_name, is_required, height) in enumerate(fields):
            # 创建字段框架
            field_frame = ttk.LabelFrame(
                self.scrollable_frame, 
                text=display_name, 
                padding="5"
            )
            field_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=5)
            
            # 配置列权重
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            field_frame.grid_columnconfigure(0, weight=1)
            
            # 创建文本输入框
            if height <= 2:
                # 单行或双行使用Entry
                text_widget = tk.Text(
                    field_frame,
                    height=height,
                    wrap=tk.WORD,
                    font=("Microsoft YaHei", 10)
                )
            else:
                # 多行使用ScrolledText
                text_widget = scrolledtext.ScrolledText(
                    field_frame,
                    height=height,
                    wrap=tk.WORD,
                    font=("Microsoft YaHei", 10)
                )
            
            text_widget.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
            
            # 添加占位符文本
            placeholder_texts = {
                'role': '例如：你是一个专业的数据分析师...',
                'background': '例如：我需要分析销售数据，目标是找出最佳销售策略...',
                'instruction': '请详细描述你希望AI执行的具体任务和要求...',
                'example': '提供一些输入输出的示例，帮助AI更好地理解任务...',
                'output': '例如：请以JSON格式输出结果，包含以下字段...',
                'constraint': '例如：回答不超过200字，使用专业术语...'
            }
            
            if field_name in placeholder_texts:
                text_widget.insert("1.0", placeholder_texts[field_name])
                text_widget.bind("<FocusIn>", lambda e, w=text_widget, p=placeholder_texts[field_name]: self._on_focus_in(e, w, p))
                text_widget.config(foreground='grey')
            
            # 存储widget引用
            self.input_widgets[field_name] = text_widget
    
    def _on_focus_in(self, event, widget, placeholder):
        """输入框获得焦点时的处理"""
        current_text = widget.get("1.0", tk.END).strip()
        if current_text == placeholder:
            widget.delete("1.0", tk.END)
            widget.config(foreground='black')
    
    def get_inputs(self) -> Dict[str, str]:
        """获取所有输入内容"""
        inputs = {}
        placeholder_texts = {
            'role': '例如：你是一个专业的数据分析师...',
            'background': '例如：我需要分析销售数据，目标是找出最佳销售策略...',
            'instruction': '请详细描述你希望AI执行的具体任务和要求...',
            'example': '提供一些输入输出的示例，帮助AI更好地理解任务...',
            'output': '例如：请以JSON格式输出结果，包含以下字段...',
            'constraint': '例如：回答不超过200字，使用专业术语...'
        }
        
        for field_name, widget in self.input_widgets.items():
            text = widget.get("1.0", tk.END).strip()
            placeholder = placeholder_texts.get(field_name, '')
            
            # 如果是占位符文本，则视为空
            if text == placeholder:
                inputs[field_name] = ''
            else:
                inputs[field_name] = text
        
        return inputs
    
    def clear_inputs(self):
        """清空所有输入"""
        placeholder_texts = {
            'role': '例如：你是一个专业的数据分析师...',
            'background': '例如：我需要分析销售数据，目标是找出最佳销售策略...',
            'instruction': '请详细描述你希望AI执行的具体任务和要求...',
            'example': '提供一些输入输出的示例，帮助AI更好地理解任务...',
            'output': '例如：请以JSON格式输出结果，包含以下字段...',
            'constraint': '例如：回答不超过200字，使用专业术语...'
        }
        
        for field_name, widget in self.input_widgets.items():
            widget.delete("1.0", tk.END)
            if field_name in placeholder_texts:
                widget.insert("1.0", placeholder_texts[field_name])
                widget.config(foreground='grey')
    
    def get_widget(self) -> ttk.LabelFrame:
        """获取组件widget"""
        return self.frame


class PromptResultDisplay:
    """提示词结果显示组件"""
    
    def __init__(self, parent):
        self.parent = parent
        self.current_prompt = ""
        
        # 创建主框架
        self.frame = ttk.LabelFrame(parent, text="生成结果", padding="10")
        
        # 创建结果显示区域
        self.result_text = scrolledtext.ScrolledText(
            self.frame,
            height=15,
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.result_text.pack(fill="both", expand=True)
        
        # 创建按钮框架
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(fill="x", pady=(10, 0))
        
        # 保存按钮
        self.save_button = ttk.Button(
            self.button_frame,
            text="保存到提示词库",
            command=self.save_prompt,
            state=tk.DISABLED
        )
        self.save_button.pack(side="left", padx=(0, 10))
        
        # 下载按钮
        self.download_button = ttk.Button(
            self.button_frame,
            text="下载文件",
            command=self.download_prompt,
            state=tk.DISABLED
        )
        self.download_button.pack(side="left", padx=(0, 10))
        
        # 复制按钮
        self.copy_button = ttk.Button(
            self.button_frame,
            text="复制结果",
            command=self.copy_prompt,
            state=tk.DISABLED
        )
        self.copy_button.pack(side="left", padx=(0, 10))
        
        # 清空结果按钮
        self.clear_button = ttk.Button(
            self.button_frame,
            text="清空结果",
            command=self.clear_result
        )
        self.clear_button.pack(side="left")
        
        # 保存回调函数
        self.save_callback = None
    
    def display_result(self, result: Dict[str, Any]):
        """显示生成结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        
        if result['success']:
            # 成功结果
            content = f"✅ 提示词生成成功\n\n"
            content += result['generated_prompt']
            
            self.result_text.insert("1.0", content)
            self.current_prompt = result['generated_prompt']
            
            # 启用按钮
            self.save_button.config(state=tk.NORMAL)
            self.download_button.config(state=tk.NORMAL)
            self.copy_button.config(state=tk.NORMAL)
            
        else:
            # 失败结果
            content = f"❌ 提示词生成失败\n\n"
            content += f"错误信息：{result['error']}\n"
            
            self.result_text.insert("1.0", content)
            self.current_prompt = ""
            
            # 禁用按钮
            self.save_button.config(state=tk.DISABLED)
            self.download_button.config(state=tk.DISABLED)
            self.copy_button.config(state=tk.DISABLED)
            
            # 设置错误信息样式
            self.result_text.tag_add("error", "3.5", "3.end")
            self.result_text.tag_config("error", foreground="red")
        
        self.result_text.config(state=tk.DISABLED)
    
    def save_prompt(self):
        """保存提示词到提示词库"""
        if not self.current_prompt:
            messagebox.showwarning("警告", "没有可保存的提示词")
            return
        
        # 弹出对话框让用户输入提示词名称
        dialog = tk.Toplevel(self.parent)
        dialog.title("保存提示词")
        dialog.geometry("400x150")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # 创建输入框
        ttk.Label(dialog, text="请输入提示词名称:").pack(pady=10)
        name_var = tk.StringVar(value="自定义提示词")
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        name_entry.select_range(0, tk.END)
        name_entry.focus()
        
        # 按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def save_action():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("警告", "请输入提示词名称")
                return
            
            if self.save_callback:
                self.save_callback(self.current_prompt, name)
            dialog.destroy()
        
        def cancel_action():
            dialog.destroy()
        
        ttk.Button(button_frame, text="保存", command=save_action).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=cancel_action).pack(side="left", padx=5)
        
        # 绑定回车键
        name_entry.bind("<Return>", lambda e: save_action())
    
    def download_prompt(self):
        """下载提示词为文件"""
        if not self.current_prompt:
            messagebox.showwarning("警告", "没有可下载的提示词")
            return
        
        try:
            # 选择保存位置
            filename = filedialog.asksaveasfilename(
                title="保存提示词",
                defaultextension=".txt",
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("Markdown文件", "*.md"),
                    ("所有文件", "*.*")
                ]
            )
            
            if filename:
                # 添加元信息
                content = f"# 生成的提示词\n\n"
                content += f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                content += f"---\n\n"
                content += self.current_prompt
                
                # 写入文件
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                messagebox.showinfo("成功", f"提示词已保存到：{filename}")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败：{str(e)}")
    
    def copy_prompt(self):
        """复制提示词到剪贴板"""
        if not self.current_prompt:
            messagebox.showwarning("警告", "没有可复制的提示词")
            return
        
        try:
            pyperclip.copy(self.current_prompt)
            messagebox.showinfo("成功", "提示词已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败：{str(e)}")
    
    def clear_result(self):
        """清空结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.current_prompt = ""
        
        # 禁用按钮
        self.save_button.config(state=tk.DISABLED)
        self.download_button.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
    
    def show_generating_status(self, message: str = "正在生成提示词，请稍候..."):
        """显示生成状态"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", f"⏳ {message}")
        self.result_text.config(state=tk.DISABLED)
        
        # 禁用按钮
        self.save_button.config(state=tk.DISABLED)
        self.download_button.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
    
    def get_widget(self) -> ttk.LabelFrame:
        """获取组件widget"""
        return self.frame


class PromptGenerationTab:
    """提示词生成Tab主界面"""
    
    def __init__(self, parent):
        """
        初始化提示词生成Tab
        
        Args:
            parent: 父窗口
        """
        self.parent = parent
        
        # 初始化业务逻辑
        self.prompt_generator = OptimizedPromptGenerator()
        
        # 创建主框架
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 初始化UI组件
        self._setup_ui()
        
        # 加载配置选项
        self._load_config_options()

    def _setup_ui(self):
        """设置UI界面 – 强制左右 1:1 均分"""
        # 创建左右分栏
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill="both", expand=True)

        # 左右两帧，权重相同即可 1:1
        self.left_frame = ttk.Frame(self.paned_window)
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        self.paned_window.add(self.right_frame, weight=1)

        self._setup_left_panel()
        self._setup_right_panel()

    def _setup_left_panel(self):
        """设置左侧面板 – 允许纵向滚动 + 下拉框宽度对调"""
        # ---- 输入面板（可滚动） ----
        self.input_panel = PromptInputPanel(self.left_frame)
        # 关键：左右撑满，上下可扩展
        self.input_panel.get_widget().pack(fill="both", expand=True, pady=(0, 10))

        # ---- 生成配置区 ----
        self.config_frame = ttk.LabelFrame(self.left_frame, text="生成配置", padding="10")
        self.config_frame.pack(fill="x", pady=(0, 10))

        # 第一行：提示词 + 大模型
        row1 = ttk.Frame(self.config_frame)
        row1.pack(fill="x", pady=(0, 5))

        ttk.Label(row1, text="提示词:").pack(side="left", padx=(0, 5))
        self.prompt_var = tk.StringVar()
        self.prompt_combo = ttk.Combobox(row1, textvariable=self.prompt_var,
                                         state="readonly", width=18)   # 变窄
        self.prompt_combo.pack(side="left", padx=(0, 15))

        ttk.Label(row1, text="大模型:").pack(side="left", padx=(0, 5))
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(row1, textvariable=self.model_var,
                                        state="readonly", width=28)   # 变宽
        self.model_combo.pack(side="left")

        # 第二行：temperature + top_p
        row2 = ttk.Frame(self.config_frame)
        row2.pack(fill="x")

        ttk.Label(row2, text="Temperature:").pack(side="left", padx=(0, 5))
        self.temperature_var = tk.StringVar(value="0.3")
        ttk.Entry(row2, textvariable=self.temperature_var, width=8)\
            .pack(side="left", padx=(0, 15))

        ttk.Label(row2, text="Top_p:").pack(side="left", padx=(0, 5))
        self.top_p_var = tk.StringVar(value="0.9")
        ttk.Entry(row2, textvariable=self.top_p_var, width=8)\
            .pack(side="left")

        # ---- 按钮区 ----
        self.button_frame = ttk.Frame(self.left_frame)
        self.button_frame.pack(fill="x")

        self.generate_button = ttk.Button(
            self.button_frame,
            text="生成提示词",
            command=self._on_generate_prompt,
            style="Accent.TButton"
        )
        self.generate_button.pack(side="left", padx=(0, 10))

        self.clear_button = ttk.Button(
            self.button_frame,
            text="清空",
            command=self._on_clear_all
        )
        self.clear_button.pack(side="left")
    
    def _setup_right_panel(self):
        """设置右侧面板"""
        # 结果显示区域
        self.result_display = PromptResultDisplay(self.right_frame)
        self.result_display.save_callback = self._save_generated_prompt
        self.result_display.get_widget().pack(fill="both", expand=True, pady=(0, 10))
        
        # 状态和统计信息
        self.status_frame = ttk.LabelFrame(self.right_frame, text="状态信息", padding="10")
        self.status_frame.pack(fill="x")
        
        # 状态标签
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(anchor="w")
        
        # 统计信息
        self.stats_label = ttk.Label(self.status_frame, text="")
        self.stats_label.pack(anchor="w", pady=(5, 0))
        
        # 更新统计信息
        self._update_statistics()
    
    def _load_config_options(self):
        """加载配置选项"""
        try:
            print("🔄 开始加载提示词生成配置选项...")
            
            # 加载提示词选项
            prompts = self.prompt_generator.prompt_manager.get_all_prompts()
            print(f"📝 获取到 {len(prompts)} 个提示词")
            
            prompt_options = []
            prompt_generation_prompt = None
            
            for prompt in prompts:
                prompt_name = prompt.get('name', prompt.get('id', ''))
                prompt_options.append(prompt_name)
                
                # 检查是否存在"提示词生成"相关提示词
                if '提示词生成' in prompt_name or 'prompt' in prompt_name.lower():
                    prompt_generation_prompt = prompt_name
            
            print(f"📝 提示词选项: {prompt_options}")
            self.prompt_combo['values'] = prompt_options
            
            # 设置默认值：优先选择"提示词生成"相关，没有则留空
            if prompt_generation_prompt:
                self.prompt_var.set(prompt_generation_prompt)
                print(f"✅ 设置默认提示词: {prompt_generation_prompt}")
            else:
                self.prompt_var.set("")
                print("ℹ️ 未找到'提示词生成'相关提示词，留空让用户选择")
            
            # 加载大模型选项
            models = self.prompt_generator.config_manager.get_all_models()
            print(f"🤖 获取到 {len(models)} 个模型配置")
            
            model_options = [model.get('name', model.get('model_id', '')) for model in models]
            
            if not model_options:
                model_options = ["默认模型"]
                print("⚠️ 未找到模型配置，使用默认值")
            
            print(f"🤖 模型选项: {model_options}")
            self.model_combo['values'] = model_options
            if model_options:
                self.model_var.set(model_options[0])
                
            print("✅ 提示词生成配置选项加载完成")
                
        except Exception as e:
            print(f"❌ 加载配置选项失败：{e}")
            import traceback
            traceback.print_exc()
            # 设置默认值 - 不强制设置提示词，让用户自己选择
            self.prompt_combo['values'] = []
            self.prompt_var.set("")
            self.model_combo['values'] = ["默认模型"]
            self.model_var.set("默认模型")
    
    def refresh_config_options(self):
        """刷新配置选项（供外部调用）"""
        try:
            print("🔄 开始刷新提示词生成配置选项...")
            
            # 保存当前选中的值
            current_prompt = self.prompt_var.get()
            current_model = self.model_var.get()
            print(f"📝 当前选中 - 提示词: {current_prompt}, 模型: {current_model}")
            
            # 强制重新初始化配置管理器和提示词管理器
            try:
                print("🔄 重新初始化配置管理器...")
                self.prompt_generator.config_manager.reload_config()
                print("🔄 重新初始化提示词管理器...")
                self.prompt_generator.prompt_manager.reload_prompts()
            except Exception as reload_error:
                print(f"⚠️ 重新加载配置时出现错误: {reload_error}")
            
            # 重新加载配置选项
            self._load_config_options()
            print("✅ 提示词生成配置选项重新加载完成")
            
            # 尝试恢复之前的选择
            prompt_values = list(self.prompt_combo['values'])
            
            if current_prompt in prompt_values:
                self.prompt_var.set(current_prompt)
                print(f"✅ 恢复提示词选择: {current_prompt}")
            else:
                # 检查是否存在"提示词生成"相关作为默认值
                prompt_generation_prompt = None
                for value in prompt_values:
                    if '提示词生成' in value or 'prompt' in value.lower():
                        prompt_generation_prompt = value
                        break
                
                if prompt_generation_prompt:
                    self.prompt_var.set(prompt_generation_prompt)
                    print(f"✅ 使用默认提示词: {prompt_generation_prompt}")
                else:
                    # 没有找到"提示词生成"相关的提示词，留空让用户选择
                    self.prompt_var.set("")
                    print("ℹ️ 未找到'提示词生成'相关提示词，留空让用户选择")
            
            # 模型选择逻辑
            model_values = list(self.model_combo['values'])
            if current_model in model_values:
                self.model_var.set(current_model)
                print(f"✅ 恢复模型选择: {current_model}")
            else:
                print(f"⚠️ 原模型 '{current_model}' 不存在，使用默认值")
            
            # 强制更新UI显示
            self.prompt_combo.update()
            self.model_combo.update()
            print("✅ UI更新完成")
                
            print("✅ 提示词生成配置选项刷新完成")
                
        except Exception as e:
            print(f"❌ 刷新提示词生成配置选项失败：{e}")
            import traceback
            traceback.print_exc()
    
    def _on_generate_prompt(self):
        """生成提示词按钮点击事件"""
        try:
            # 获取输入参数
            inputs = self.input_panel.get_inputs()
            
            # 基本验证
            if not inputs.get('instruction', '').strip():
                messagebox.showwarning("警告", "请填写必填字段：指令与要求")
                return
            
            if len(inputs.get('instruction', '').strip()) < 10:
                messagebox.showwarning("警告", "指令与要求至少需要10个字符")
                return
            
            # 获取配置参数
            selected_prompt = self.prompt_var.get()
            selected_model = self.model_var.get()
            
            try:
                temperature = float(self.temperature_var.get())
                if not (0.0 <= temperature <= 1.0):
                    raise ValueError("Temperature必须在0.0-1.0之间")
            except ValueError as e:
                messagebox.showwarning("警告", f"Temperature参数无效：{e}")
                return
            
            try:
                top_p = float(self.top_p_var.get())
                if not (0.0 <= top_p <= 1.0):
                    raise ValueError("Top_p必须在0.0-1.0之间")
            except ValueError as e:
                messagebox.showwarning("警告", f"Top_p参数无效：{e}")
                return
            
            # 显示生成状态
            self.result_display.show_generating_status()
            self.generate_button.config(state=tk.DISABLED, text="生成中...")
            self.status_label.config(text="正在生成提示词...")
            
            # 异步生成提示词
            self.prompt_generator.generate_prompt_async(
                inputs=inputs,
                selected_prompt=selected_prompt,
                selected_model=selected_model,
                temperature=temperature,
                top_p=top_p,
                success_callback=self._on_prompt_generated,
                error_callback=self._on_prompt_error,
                progress_callback=self._on_generation_progress
            )
            
        except Exception as e:
            messagebox.showerror("错误", f"生成提示词时出错：{str(e)}")
            self._reset_generate_button()
    
    def _on_prompt_generated(self, result: Dict[str, Any]):
        """提示词生成成功回调"""
        # 使用after方法确保在主线程中更新UI
        self.parent.after(0, self._update_ui_after_generation, result)
    
    def _on_prompt_error(self, result: Dict[str, Any]):
        """提示词生成失败回调"""
        # 使用after方法确保在主线程中更新UI
        self.parent.after(0, self._update_ui_after_generation, result)
    
    def _on_generation_progress(self, message: str):
        """生成进度回调"""
        self.parent.after(0, lambda: self.status_label.config(text=message))
    
    def _update_ui_after_generation(self, result: Dict[str, Any]):
        """在主线程中更新UI"""
        try:
            # 显示结果
            self.result_display.display_result(result)
            
            # 更新状态
            if result['success']:
                self.status_label.config(text="提示词生成成功")
            else:
                self.status_label.config(text=f"生成失败：{result['error']}")
            
            # 更新统计信息
            self._update_statistics()
            
        except Exception as e:
            print(f"更新UI时出错：{e}")
        finally:
            # 恢复按钮状态
            self._reset_generate_button()
    
    def _reset_generate_button(self):
        """重置生成按钮状态"""
        self.generate_button.config(state=tk.NORMAL, text="生成提示词")
    
    def _on_clear_all(self):
        """清空所有内容"""
        # 清空输入
        self.input_panel.clear_inputs()
        
        # 清空结果
        self.result_display.clear_result()
        
        # 更新状态
        self.status_label.config(text="已清空所有内容")
    
    def _save_generated_prompt(self, prompt_content: str, prompt_name: str):
        """保存生成的提示词到prompts.json"""
        try:
            prompt_data = {
                "id": f"generated_{uuid.uuid4().hex[:8]}",
                "name": prompt_name,
                "content": prompt_content,
                "created_at": datetime.now().isoformat(),
                "source": "generated"
            }
            
            # 使用提示词管理器保存
            self.prompt_generator.prompt_manager.save_prompt(prompt_data)
            
            messagebox.showinfo("成功", f"提示词 '{prompt_name}' 已保存到提示词库")
            
            # 刷新配置选项以显示新保存的提示词
            self.refresh_config_options()
            
        except Exception as e:
            messagebox.showerror("错误", f"保存提示词失败：{str(e)}")
    
    def _update_statistics(self):
        """更新统计信息"""
        try:
            cache_stats = self.prompt_generator.get_cache_statistics()
            history_stats = self.prompt_generator.get_history_statistics()
            
            stats_text = f"缓存: {cache_stats['cache_size']}/{cache_stats['max_cache_size']} | "
            stats_text += f"历史: {history_stats['total_prompts']}"
            
            self.stats_label.config(text=stats_text)
        except Exception as e:
            self.stats_label.config(text="统计信息获取失败")
    
    def get_main_frame(self) -> ttk.Frame:
        """获取主框架"""
        return self.main_frame
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清空缓存
            self.prompt_generator.clear_cache()
        except Exception as e:
            print(f"清理资源时出错：{e}")


# 测试代码
if __name__ == "__main__":
    root = tk.Tk()
    root.title("提示词生成Tab测试")
    root.geometry("1200x800")
    
    # 创建提示词生成Tab
    prompt_tab = PromptGenerationTab(root)
    
    root.mainloop()