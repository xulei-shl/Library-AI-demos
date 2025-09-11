#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python处理Tab - 前端界面
基于公式生成Tab的设计，实现Python代码处理功能的UI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import os
import json
import threading
from typing import Optional, Callable
from datetime import datetime

from modules.python_code_processor import PythonCodeProcessor


class SimpleDataDisplaySelector:
    """简化的数据显示选择器（复用自公式生成Tab）"""
    
    def __init__(self, parent, get_export_data_callback=None):
        self.parent = parent
        self.excel_data = {}
        self.on_selection_changed = None
        self._last_struct_info = ""

        # UI构建
        self.frame = ttk.LabelFrame(parent, text="Excel文件和Sheet选择", padding="10")
        self.info_frame = ttk.Frame(self.frame)
        self.info_frame.pack(fill="x", pady=(0, 10))
        self.source_info_label = ttk.Label(self.info_frame, text="数据来源：multi_excel_selections.json", foreground="blue")
        self.source_info_label.pack(side="left")
        self.button_frame = ttk.Frame(self.info_frame)
        self.button_frame.pack(side="right")
        self.load_btn = ttk.Button(self.button_frame, text="获取数据", command=self.load_data)
        self.load_btn.pack(side="left", padx=(0, 5))
        self.refresh_btn = ttk.Button(self.button_frame, text="刷新数据", command=self.refresh_data)
        self.refresh_btn.pack(side="left")

        self.data_text = scrolledtext.ScrolledText(self.frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.data_text.pack(fill="both", expand=True, pady=(10, 0))
        self.load_data()

    def load_data(self):
        try:
            json_file = os.path.join("logs", "multi_excel_selections.json")
            if not os.path.exists(json_file):
                self._show_message("未找到数据文件", "warning")
                return False
            with open(json_file, encoding='utf-8') as f:
                data = json.load(f)
            self._parse_and_display_data(data)
            self._show_message("数据加载成功", "success")
            return True
        except Exception as e:
            self._show_message(f"加载失败：{e}", "error")
            return False

    def refresh_data(self):
        return self.load_data()

    def _parse_and_display_data(self, json_data):
        self.excel_data = {}
        display_lines = ["📊 Excel文件和Sheet数据信息", "=" * 50, ""]
        selections = json_data.get('selections', [])
        if not selections:
            display_lines.append("❌ 没有找到任何选择的数据")
        else:
            for idx, sel in enumerate(selections, 1):
                if 'error' in sel:
                    continue
                file_path = sel.get('file_path', '')
                file_name = sel.get('file_name', '')
                sheet_name = sel.get('sheet_name', '')
                selected_columns = sel.get('selected_columns', [])
                total_rows = sel.get('total_rows', 0)
                display_lines.extend([
                    f"📁 选择组 {idx}:",
                    f"   文件路径: {file_path}",
                    f"   Sheet名称: {sheet_name}",
                    f"   数据行数: {total_rows}",
                    f"   选择的列: {', '.join(selected_columns) if selected_columns else '未选择指定列'}",
                    ""
                ])
        self._last_struct_info = "\n".join(display_lines)
        self.data_text.config(state=tk.NORMAL)
        self.data_text.delete("1.0", tk.END)
        self.data_text.insert("1.0", self._last_struct_info)
        self.data_text.config(state=tk.DISABLED)

    def _load_preview_sample(self) -> str:
        """获取预览数据"""
        preview_file = os.path.join("logs", "multi_excel_preview.md")
        if not os.path.exists(preview_file):
            return ""
        with open(preview_file, encoding='utf-8') as f:
            return f.read().strip()

    def build_enhanced_prompt(self, requirement_text: str, output_path: str = "") -> str:
        """构建增强的提示词"""
        if not self._last_struct_info:
            return requirement_text
        whole_sample = self._load_preview_sample()
        sample_section = whole_sample or "*请在【多Excel上传】页生成预览后，再返回此处*"
        # 构建基础提示词
        prompt_parts = [f"# 数据处理需求\n\n{requirement_text}"]
        
        # 添加结果保存路径部分（如果提供了路径）
        if output_path.strip():
            prompt_parts.append(f"# 结果保存路径\n\n{output_path.strip()}")
        
        # 添加Excel信息和数据样例
        prompt_parts.extend([
            f"# Excel文件、工作表和处理列信息\n\n{self._last_struct_info}",
            f"# Excel数据样例\n\n{sample_section}"
        ])
        
        return "\n\n---\n\n".join(prompt_parts)

    def get_sample_data(self) -> str:
        return self._load_preview_sample()

    def get_widget(self): 
        return self.frame

    def _show_message(self, msg, typ="info"):
        color = {"success": "green", "warning": "orange", "error": "red"}.get(typ, "blue")
        self.source_info_label.config(text=msg, foreground=color)


class PythonProcessingTab:
    """Python处理Tab主类"""
    
    def __init__(self, parent):
        self.parent = parent
        self.processor = PythonCodeProcessor()
        self.is_processing = False
        self.current_thread: Optional[threading.Thread] = None
        self.analysis_result = None  # 存储LLM分析结果
        self.excel_file_mapping = {}  # Excel文件映射信息
        
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self._setup_ui()
        self._load_config_options()
    
    def _setup_ui(self):
        """设置UI界面"""
        # 创建左右分栏
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill="both", expand=True)
        
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=1)
        
        self._setup_left_panel()
        self._setup_right_panel()
    
    def _setup_left_panel(self):
        """设置左侧面板"""
        # Excel数据选择器
        self.column_selector = SimpleDataDisplaySelector(self.left_frame)
        self.column_selector.get_widget().pack(fill="both", expand=True, pady=(0, 10))
        
        # 需求描述区域
        self.requirement_frame = ttk.LabelFrame(self.left_frame, text="需求描述", padding="10")
        self.requirement_frame.pack(fill="both", expand=True)
        
        self.requirement_text = scrolledtext.ScrolledText(
            self.requirement_frame, height=6, wrap=tk.WORD, font=("Microsoft YaHei", 10)
        )
        self.requirement_text.pack(fill="both", expand=True, pady=(0, 10))
        
        placeholder_text = """请详细描述您的Python数据处理需求，例如：

• 从Excel文件中读取数据，进行数据清洗和分析
• 计算各种统计指标，如平均值、中位数、标准差等
• 生成图表和可视化结果
• 将处理结果保存为新的Excel文件或CSV文件

请清空此文本后输入您的具体需求..."""
        
        self.requirement_text.insert("1.0", placeholder_text)
        self.requirement_text.bind("<FocusIn>", self._on_requirement_focus_in)
        
        # 结果保存路径
        self.path_frame = ttk.LabelFrame(self.requirement_frame, text="结果保存路径", padding="10")
        self.path_frame.pack(fill="x", pady=(10, 10))
        
        path_select_frame = ttk.Frame(self.path_frame)
        path_select_frame.pack(fill="x")
        
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_select_frame, textvariable=self.path_var, state="readonly")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.path_button = ttk.Button(path_select_frame, text="选择路径", command=self._select_output_path, width=10)
        self.path_button.pack(side="right")
        
        # 配置选项
        self.config_frame = ttk.LabelFrame(self.requirement_frame, text="生成配置", padding="10")
        self.config_frame.pack(fill="x", pady=(10, 10))
        
        config_row = ttk.Frame(self.config_frame)
        config_row.pack(fill="x")
        
        ttk.Label(config_row, text="大模型:").pack(side="left", padx=(0, 5))
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(config_row, textvariable=self.model_var, state="readonly", width=25)
        self.model_combo.pack(side="left")
        
        # 第一阶段按钮区域
        self.button_frame = ttk.Frame(self.requirement_frame)
        self.button_frame.pack(fill="x", pady=(10, 0))
        
        self.analyze_button = ttk.Button(
            self.button_frame, text="🔍 分析处理类型", command=self._on_analyze_type, style="Accent.TButton"
        )
        self.analyze_button.pack(side="left", padx=(0, 10))
        
        self.clear_button = ttk.Button(self.button_frame, text="清空", command=self._on_clear_all)
        self.clear_button.pack(side="left")
        
        # 添加提示标签（初始隐藏），引导用户关注右侧
        self.attention_frame = ttk.Frame(self.requirement_frame)
        self.attention_frame.pack(fill="x", pady=(10, 0))
        
        self.attention_label = ttk.Label(
            self.attention_frame, 
            text="👉 分析完成！请查看右侧的 '输出策略确认' 区域继续操作", 
            font=("Microsoft YaHei", 10, "bold"),
            foreground="#2E8B57",  # 使用绿色
            background="#F0F8FF"   # 浅蓝色背景
        )
        self.attention_label.pack(pady=5)
        self.attention_frame.pack_forget()  # 初始隐藏
    def _setup_right_panel(self):
        """设置右侧面板"""
        # 第二阶段：策略确认区域（初始隐藏，移到右侧顶部）
        self.strategy_frame = ttk.LabelFrame(self.right_frame, text="📋 输出策略确认", padding="15")
        self.strategy_frame.pack_forget()  # 初始隐藏
        
        # LLM分析结果显示
        self.analysis_display_frame = ttk.Frame(self.strategy_frame)
        self.analysis_display_frame.pack(fill="x", pady=(0, 15))
        
        self.analysis_label = ttk.Label(self.analysis_display_frame, text="✨ 处理类型分析结果：", font=("Microsoft YaHei", 10, "bold"))
        self.analysis_label.pack(anchor="w")
        
        self.analysis_text = tk.Text(
            self.analysis_display_frame, height=4, wrap=tk.WORD, font=("Microsoft YaHei", 9),
            relief="flat", bg="#f8f9fa", state=tk.DISABLED
        )
        self.analysis_text.pack(fill="x", pady=(5, 0))
        
        # 处理类型选择
        self.type_selection_frame = ttk.Frame(self.strategy_frame)
        self.type_selection_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(self.type_selection_frame, text="处理类型：", font=("Microsoft YaHei", 10, "bold")).pack(anchor="w")
        
        self.type_var = tk.StringVar()
        type_radio_frame = ttk.Frame(self.type_selection_frame)
        type_radio_frame.pack(fill="x", pady=(5, 0))
        
        self.type_enhancement = ttk.Radiobutton(
            type_radio_frame, text="🔧 增强型（保留原数据+新增列）", variable=self.type_var, 
            value="enhancement", command=self._on_type_changed
        )
        self.type_enhancement.pack(anchor="w", pady=(0, 5))
        
        self.type_reconstruction = ttk.Radiobutton(
            type_radio_frame, text="🔄 重构型（生成新文件）", variable=self.type_var, 
            value="reconstruction", command=self._on_type_changed
        )
        self.type_reconstruction.pack(anchor="w")
        
        # 增强型选项（仅在增强型时显示）
        self.enhancement_options_frame = ttk.LabelFrame(self.strategy_frame, text="增强型选项", padding="10")
        
        # 主Excel选择
        excel_select_frame = ttk.Frame(self.enhancement_options_frame)
        excel_select_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(excel_select_frame, text="主Excel：").pack(side="left", padx=(0, 5))
        self.main_excel_var = tk.StringVar()
        self.main_excel_combo = ttk.Combobox(excel_select_frame, textvariable=self.main_excel_var, state="readonly", width=30)
        self.main_excel_combo.pack(side="left", padx=(0, 10))
        
        # 主Sheet选择
        sheet_select_frame = ttk.Frame(self.enhancement_options_frame)
        sheet_select_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(sheet_select_frame, text="主Sheet：").pack(side="left", padx=(0, 5))
        self.main_sheet_var = tk.StringVar()
        self.main_sheet_combo = ttk.Combobox(sheet_select_frame, textvariable=self.main_sheet_var, state="readonly", width=30)
        self.main_sheet_combo.pack(side="left")
        
        # 绑定主Excel变化事件
        self.main_excel_combo.bind('<<ComboboxSelected>>', self._on_main_excel_changed)
        
        # 保留原始数据选项
        self.keep_original_var = tk.BooleanVar(value=True)
        self.keep_original_check = ttk.Checkbutton(
            self.enhancement_options_frame, text="保留原始数据", variable=self.keep_original_var
        )
        self.keep_original_check.pack(anchor="w")
        
        # 最终执行按钮
        self.execute_frame = ttk.Frame(self.strategy_frame)
        self.execute_frame.pack(fill="x", pady=(15, 0))
        
        self.execute_button = ttk.Button(
            self.execute_frame, text="✅ 确认并执行Python代码", command=self._on_execute_python, style="Accent.TButton"
        )
        self.execute_button.pack(side="left", padx=(0, 10))
        
        self.cancel_button = ttk.Button(
            self.execute_frame, text="❌ 取消", command=self._on_cancel_strategy
        )
        self.cancel_button.pack(side="left")
        
        # 日志信息区域（移到策略确认区域下方）
        self.log_frame = ttk.LabelFrame(self.right_frame, text="处理日志", padding="10")
        self.log_frame.pack(fill="both", expand=True, pady=(10, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9)
        )
        self.log_text.pack(fill="both", expand=True)
        
        self.log_button_frame = ttk.Frame(self.log_frame)
        self.log_button_frame.pack(fill="x", pady=(10, 0))
        
        self.clear_log_button = ttk.Button(self.log_button_frame, text="清空日志", command=self._clear_log)
        self.clear_log_button.pack(side="left")
        
        # 状态信息
        self.status_frame = ttk.LabelFrame(self.right_frame, text="状态信息", padding="10")
        self.status_frame.pack(fill="x")
        
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(anchor="w")
    
    def _load_config_options(self):
        """加载配置选项"""
        try:
            models = self.processor.config_manager.get_all_models()
            model_options = [model.get('name', model.get('model_id', '')) for model in models]
            if not model_options:
                model_options = ["默认模型"]
            self.model_combo['values'] = model_options
            if model_options:
                self.model_var.set(model_options[0])
        except Exception as e:
            self.model_combo['values'] = ["默认模型"]
            self.model_var.set("默认模型")
    
    def refresh_config_options(self):
        """刷新配置选项"""
        current_model = self.model_var.get()
        self._load_config_options()
        model_values = list(self.model_combo['values'])
        if current_model in model_values:
            self.model_var.set(current_model)
    
    def _on_requirement_focus_in(self, event):
        """需求输入框获得焦点时的处理"""
        current_text = self.requirement_text.get("1.0", tk.END).strip()
        if "请清空此文本后输入您的具体需求" in current_text:
            self.requirement_text.delete("1.0", tk.END)
    
    def _select_output_path(self):
        """选择输出路径"""
        directory = filedialog.askdirectory(title="选择结果保存目录", initialdir=os.getcwd())
        if directory:
            self.path_var.set(directory)
    
    def _on_analyze_type(self):
        """分析处理类型"""
        try:
            requirement = self.requirement_text.get("1.0", tk.END).strip()
            if not requirement or len(requirement) < 10:
                messagebox.showwarning("警告", "请输入详细的需求描述（至少10个字符）")
                return
            
            if "请清空此文本后输入您的具体需求" in requirement:
                messagebox.showwarning("警告", "请输入您的具体需求")
                return
            
            sample_data = self.column_selector.get_sample_data()
            if not sample_data:
                messagebox.showwarning("警告", "未找到样例数据，请先在多Excel上传页面选择数据并生成预览")
                return
            
            # 禁用分析按钮
            self.analyze_button.config(state=tk.DISABLED, text="🔄 分析中...")
            self._update_progress("正在分析处理类型...")
            
            # 在后台线程中进行分析
            self.current_thread = threading.Thread(
                target=self._analyze_type_in_background,
                args=(requirement, sample_data, self.model_var.get()),
                daemon=True
            )
            self.current_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"分析处理类型时出错：{str(e)}")
            self.analyze_button.config(state=tk.NORMAL, text="🔍 分析处理类型")
    
    def _analyze_type_in_background(self, requirement: str, sample_data: str, selected_model: str):
        """在后台线程中分析处理类型"""
        try:
            result = self.processor.analyze_processing_type(
                requirement=requirement,
                sample_data=sample_data, 
                selected_model=selected_model
            )
            self.parent.after(0, self._on_analysis_complete, result)
        except Exception as e:
            error_result = {'success': False, 'error': f"分析过程中出现异常：{str(e)}"}
            self.parent.after(0, self._on_analysis_complete, error_result)
    
    def _on_analysis_complete(self, result: dict):
        """分析完成回调"""
        self.analyze_button.config(state=tk.NORMAL, text="🔍 分析处理类型")
        
        if result['success']:
            self.analysis_result = result['analysis']
            self._show_strategy_confirmation()
            self._update_progress("分析完成，请确认输出策略")
        else:
            messagebox.showerror("分析失败", f"处理类型分析失败：\n\n{result['error']}")
            self._update_progress("分析失败")
    
    def _show_strategy_confirmation(self):
        """显示策略确认界面"""
        if not self.analysis_result:
            return
        
        # 显示左侧提示信息，引导用户关注右侧
        self.attention_frame.pack(fill="x", pady=(10, 0))
        
        # 显示右侧的策略确认框架
        self.strategy_frame.pack(fill="x", pady=(0, 10))
        
        # 显示分析结果
        analysis_text = f"类型：{self.analysis_result.get('type', 'unknown')}\n"
        analysis_text += f"说明：{self.analysis_result.get('reason', '无说明')}\n"
        analysis_text += f"置信度：{self.analysis_result.get('confidence', 0):.0%}\n"
        analysis_text += f"建议列名：{', '.join(self.analysis_result.get('suggested_columns', []))}"
        
        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete("1.0", tk.END)
        self.analysis_text.insert("1.0", analysis_text)
        self.analysis_text.config(state=tk.DISABLED)
        
        # 设置默认选择
        suggested_type = self.analysis_result.get('type', 'enhancement')
        self.type_var.set(suggested_type)
        
        # 加载Excel文件选项
        self._load_excel_options()
        
        # 根据类型显示相应选项
        self._on_type_changed()
    
    def _load_excel_options(self):
        """加载Excel文件选项"""
        try:
            json_file = os.path.join("logs", "multi_excel_selections.json")
            if not os.path.exists(json_file):
                return
            
            with open(json_file, encoding='utf-8') as f:
                data = json.load(f)
            
            selections = data.get('selections', [])
            excel_files = []
            self.excel_file_mapping = {}
            
            for sel in selections:
                if 'error' in sel:
                    continue
                file_name = sel.get('file_name', '')
                file_path = sel.get('file_path', '')
                sheet_name = sel.get('sheet_name', '')
                
                if file_name not in self.excel_file_mapping:
                    self.excel_file_mapping[file_name] = {
                        'file_path': file_path,
                        'sheets': []
                    }
                    excel_files.append(file_name)
                
                if sheet_name not in self.excel_file_mapping[file_name]['sheets']:
                    self.excel_file_mapping[file_name]['sheets'].append(sheet_name)
            
            # 设置Excel文件选项
            self.main_excel_combo['values'] = excel_files
            if excel_files:
                self.main_excel_var.set(excel_files[0])  # 默认选择第一个
                self._on_main_excel_changed(None)  # 触发Sheet更新
                
        except Exception as e:
            print(f"加载Excel选项失败：{e}")
    
    def _on_main_excel_changed(self, event):
        """主Excel变化时更新Sheet选项"""
        selected_excel = self.main_excel_var.get()
        if selected_excel and selected_excel in self.excel_file_mapping:
            sheets = self.excel_file_mapping[selected_excel]['sheets']
            self.main_sheet_combo['values'] = sheets
            if sheets:
                self.main_sheet_var.set(sheets[0])  # 默认选择第一个Sheet
    
    def _on_type_changed(self):
        """处理类型变化时的处理"""
        selected_type = self.type_var.get()
        if selected_type == "enhancement":
            self.enhancement_options_frame.pack(fill="x", pady=(10, 0))
        else:
            self.enhancement_options_frame.pack_forget()
    
    def _on_cancel_strategy(self):
        """取消策略确认"""
        self.strategy_frame.pack_forget()
        self.attention_frame.pack_forget()  # 同时隐藏左侧提示信息
        self.analysis_result = None
        self._update_progress("已取消策略确认")
    
    def _on_execute_python(self):
        """执行Python代码生成和处理"""
        try:
            # 检查是否已经完成策略分析
            if not self.analysis_result:
                messagebox.showwarning("警告", "请先进行处理类型分析")
                return
            
            requirement = self.requirement_text.get("1.0", tk.END).strip()
            
            output_path = self.path_var.get()
            if not output_path:
                messagebox.showwarning("警告", "请选择结果保存路径")
                return
            
            sample_data = self.column_selector.get_sample_data()
            if not sample_data:
                messagebox.showwarning("警告", "未找到样例数据，请先在多Excel上传页面选择数据并生成预览")
                return
            
            # 构建包含策略信息的增强提示词
            strategy_info = self._build_strategy_info()
            enhanced_requirement = self.column_selector.build_enhanced_prompt(requirement, output_path)
            
            # 检查是否已包含输出策略信息，避免重复
            if "# 输出策略" not in enhanced_requirement and "# 结果保存策略" not in enhanced_requirement:
                enhanced_requirement += f"\n\n---\n\n# 输出策略\n\n{strategy_info}"
            
            self.is_processing = True
            self.execute_button.config(state=tk.DISABLED, text="🔄 处理中...")
            self.analyze_button.config(state=tk.DISABLED)
            self._clear_log()
            self._log("开始Python代码处理...")
            self._log(f"策略信息：{strategy_info.replace(chr(10), ' | ')}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            work_dir = os.path.join(output_path, f"python_processing_{timestamp}")
            os.makedirs(work_dir, exist_ok=True)
            
            # 构建完整的处理参数
            processing_params = {
                'requirement': enhanced_requirement,
                'sample_data': sample_data,
                'output_directory': work_dir,
                'selected_model': self.model_var.get(),
                'strategy': {
                    'type': self.type_var.get(),
                    'analysis_result': self.analysis_result
                }
            }
            
            # 如果是增强型，添加Excel和Sheet信息
            if self.type_var.get() == "enhancement":
                processing_params['strategy'].update({
                    'main_excel': self.main_excel_var.get(),
                    'main_sheet': self.main_sheet_var.get(),
                    'keep_original': self.keep_original_var.get(),
                    'excel_file_path': self.excel_file_mapping.get(self.main_excel_var.get(), {}).get('file_path', '')
                })
            
            self.current_thread = threading.Thread(
                target=self._process_python_in_background,
                args=(processing_params,),
                daemon=True
            )
            self.current_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动处理时出错：{str(e)}")
            self.execute_button.config(state=tk.NORMAL, text="✅ 确认并执行Python代码")
            self.analyze_button.config(state=tk.NORMAL)
    
    def _process_python_in_background(self, params: dict):
        """在后台线程中处理Python代码"""
        try:
            result = self.processor.process_python_code_with_strategy(
                **params,
                progress_callback=self._update_progress,
                log_callback=self._log
            )
            self.parent.after(0, self._on_processing_complete, result)
        except Exception as e:
            error_result = {
                'success': False, 
                'error': f"处理过程中出现异常：{str(e)}", 
                'work_directory': params.get('output_directory', '')
            }
            self.parent.after(0, self._on_processing_complete, error_result)
    
    def _on_processing_complete(self, result: dict):
        """处理完成回调"""
        self.is_processing = False
        self.execute_button.config(state=tk.NORMAL, text="✅ 确认并执行Python代码")
        self.analyze_button.config(state=tk.NORMAL)
        
        if result['success']:
            self._log("✅ Python代码处理完成！")
            self._log(f"工作目录：{result['work_directory']}")
            if messagebox.askyesno("处理完成", f"Python代码处理完成！\n\n工作目录：{result['work_directory']}\n\n是否打开结果目录？"):
                import subprocess
                import platform
                import os
                if platform.system() == "Windows":
                    # 规范化路径，确保使用正确的路径分隔符
                    normalized_path = os.path.normpath(result['work_directory'])
                    subprocess.run(["explorer", normalized_path])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", result['work_directory']])
                else:  # Linux
                    subprocess.run(["xdg-open", result['work_directory']])
        else:
            self._log(f"❌ 处理失败：{result['error']}")
            messagebox.showerror("处理失败", f"Python代码处理失败：\n\n{result['error']}")
    
    def _update_progress(self, message: str):
        """更新进度信息"""
        self.parent.after(0, lambda: self.status_label.config(text=message))
    
    def _log(self, message: str):
        """添加日志信息"""
        def add_log():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        
        try:
            add_log()
        except:
            self.parent.after(0, add_log)
    
    def _clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _build_strategy_info(self) -> str:
        """构建策略信息字符串"""
        if not self.analysis_result:
            return "未进行策略分析"
        
        strategy_lines = []
        strategy_lines.append(f"处理类型：{self.type_var.get()}")
        
        if self.type_var.get() == "enhancement":
            strategy_lines.append(f"主Excel文件：{self.main_excel_var.get()}")
            strategy_lines.append(f"主Sheet：{self.main_sheet_var.get()}")
            strategy_lines.append(f"保留原始数据：{'是' if self.keep_original_var.get() else '否'}")
            
        strategy_lines.append(f"建议新增列：{', '.join(self.analysis_result.get('suggested_columns', []))}")
        
        return "\n".join(strategy_lines)
    
    def _on_clear_all(self):
        """清空所有内容"""
        self.requirement_text.delete("1.0", tk.END)
        placeholder_text = """请详细描述您的Python数据处理需求，例如：

• 从Excel文件中读取数据，进行数据清洗和分析
• 计算各种统计指标，如平均值、中位数、标准差等
• 生成图表和可视化结果
• 将处理结果保存为新的Excel文件或CSV文件

请清空此文本后输入您的具体需求..."""
        self.requirement_text.insert("1.0", placeholder_text)
        self.path_var.set("")
        self._clear_log()
        self.strategy_frame.pack_forget()  # 隐藏策略确认区域
        self.attention_frame.pack_forget()  # 隐藏提示信息
        self.analysis_result = None
        self.status_label.config(text="已清空所有内容")
    
    def cleanup(self):
        """清理资源"""
        try:
            self.is_processing = False
            if self.processor:
                self.processor.cleanup()
        except Exception as e:
            print(f"清理PythonProcessingTab资源时出错：{e}")

# datetime导入已在文件顶部正确处理


# 测试代码
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Python代码处理Tab测试")
    root.geometry("1400x900")
    
    # 创建Python处理Tab
    python_tab = PythonProcessingTab(root)
    
    root.mainloop()