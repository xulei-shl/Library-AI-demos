#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公式生成Tab界面
提供Excel公式生成的用户界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from typing import Dict, Any, List, Optional, Callable
import pyperclip
import json
import os

# 导入业务逻辑模块
from modules.formula_generator import OptimizedFormulaGenerator
from ui.components.multi_excel_column_selector import MultiExcelColumnSelector


class ExcelSheetColumnSelector:
    """Excel-Sheet-列三级选择器组件 - 参考多Excel上传的下拉框设计"""
    
    def __init__(self, parent, get_export_data_callback=None):
        self.parent = parent
        self.get_export_data_callback = get_export_data_callback
        self.excel_data = {}  # 完整的Excel数据结构
        self.selection_groups = []  # 存储多个选择组
        self.on_selection_changed = None
        
        # 创建主框架
        self.frame = ttk.LabelFrame(parent, text="Excel文件和Sheet选择", padding="10")
        
        # 数据来源信息
        self.info_frame = ttk.Frame(self.frame)
        self.info_frame.pack(fill="x", pady=(0, 10))
        
        self.source_info_label = ttk.Label(
            self.info_frame,
            text="正在加载数据...",
            font=("Microsoft YaHei", 9),
            foreground="blue"
        )
        self.source_info_label.pack(side="left")
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(
            self.info_frame,
            text="刷新数据",
            command=self.refresh_data
        )
        self.refresh_btn.pack(side="right")
        
        # 创建滚动区域
        self.canvas = tk.Canvas(self.frame, height=200)
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
        
        # 底部按钮区域
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(fill="x", pady=(10, 0))
        
        # 添加选择按钮
        self.add_button = ttk.Button(
            self.button_frame,
            text="+ 添加选择",
            command=self._add_selection_group
        )
        self.add_button.pack(side="left", padx=(0, 10))
        
        # 清空按钮
        self.clear_button = ttk.Button(
            self.button_frame,
            text="清空所有",
            command=self.clear_selection
        )
        self.clear_button.pack(side="left")
        
        # 加载数据并初始化
        self._load_data_with_priority()
        self._add_selection_group()  # 添加第一个选择组
    
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _load_data_with_priority(self):
        """按优先级加载数据：临时文件 > 回调函数 > 空状态"""
        try:
            # 策略1：优先读取临时文件
            if self._load_from_temp_files():
                self._show_data_source_info("temp_file")
                return True
            
            # 策略2：通过回调函数获取实时数据
            if self._load_from_callback():
                self._show_data_source_info("callback")
                return True
            
            # 策略3：显示空状态
            self._show_data_source_info("empty")
            return False
            
        except Exception as e:
            print(f"加载数据失败：{e}")
            self._show_data_source_info("error")
            return False
    
    def _load_from_temp_files(self):
        """从临时文件加载数据"""
        try:
            json_file = os.path.join("logs", "multi_excel_selections.json")
            if not os.path.exists(json_file):
                return False
            
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # 解析JSON数据到内部结构
            self._parse_json_data(json_data)
            print(f"成功从临时文件加载数据：{len(self.excel_data)} 个文件-Sheet组合")
            return True
            
        except Exception as e:
            print(f"从临时文件加载数据失败：{e}")
            return False
    
    def _load_from_callback(self):
        """通过回调函数获取实时数据"""
        try:
            if not self.get_export_data_callback:
                return False
            
            callback_data = self.get_export_data_callback()
            if not callback_data or not callback_data.get('selections'):
                return False
            
            # 解析回调数据
            self._parse_callback_data(callback_data)
            print(f"成功从回调函数加载数据：{len(self.excel_data)} 个文件-Sheet组合")
            return True
            
        except Exception as e:
            print(f"从回调函数加载数据失败：{e}")
            return False
    
    def _parse_json_data(self, json_data):
        """解析JSON数据到内部结构"""
        self.excel_data = {}
        
        for selection in json_data.get('selections', []):
            if 'error' in selection:
                continue
            
            file_name = selection['file_name']
            sheet_name = selection['sheet_name']
            
            if file_name not in self.excel_data:
                self.excel_data[file_name] = {}
            
            self.excel_data[file_name][sheet_name] = {
                'file_path': selection['file_path'],
                'columns': selection['column_names'],
                'total_rows': selection['total_rows'],
                'column_count': selection['columns']
            }
    
    def _parse_callback_data(self, callback_data):
        """解析回调数据到内部结构"""
        self.excel_data = {}
        
        for selection in callback_data.get('selections', []):
            if 'error' in selection:
                continue
            
            file_name = selection['file_name']
            sheet_name = selection['sheet_name']
            
            if file_name not in self.excel_data:
                self.excel_data[file_name] = {}
            
            self.excel_data[file_name][sheet_name] = {
                'file_path': selection['file_path'],
                'columns': selection['column_names'],
                'total_rows': selection['total_rows'],
                'column_count': selection['columns']
            }
    
    def _show_data_source_info(self, source_type):
        """显示数据来源信息"""
        if source_type == "temp_file":
            self.source_info_label.config(
                text="数据来源：已保存的选择",
                foreground="green"
            )
        elif source_type == "callback":
            self.source_info_label.config(
                text="数据来源：当前选择 (未保存)",
                foreground="orange"
            )
        elif source_type == "empty":
            self.source_info_label.config(
                text="无数据：请先在多Excel Tab中选择文件和Sheet",
                foreground="red"
            )
        else:
            self.source_info_label.config(
                text="数据加载失败",
                foreground="red"
            )
    
    def _add_selection_group(self):
        """添加一个新的选择组"""
        group_index = len(self.selection_groups)
        
        # 创建选择组框架
        group_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"选择组 {group_index + 1}",
            padding=5
        )
        group_frame.grid(row=group_index, column=0, sticky="ew", padx=5, pady=5)
        
        # 配置网格权重
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # Excel文件选择
        excel_frame = ttk.Frame(group_frame)
        excel_frame.pack(fill="x", pady=2)
        
        ttk.Label(excel_frame, text="Excel文件:").pack(side="left", padx=(0, 5))
        excel_var = tk.StringVar()
        excel_combo = ttk.Combobox(
            excel_frame,
            textvariable=excel_var,
            state="readonly",
            width=30
        )
        excel_combo.pack(side="left", padx=(0, 10))
        
        # Sheet选择
        sheet_frame = ttk.Frame(group_frame)
        sheet_frame.pack(fill="x", pady=2)
        
        ttk.Label(sheet_frame, text="Sheet:").pack(side="left", padx=(0, 5))
        sheet_var = tk.StringVar()
        sheet_combo = ttk.Combobox(
            sheet_frame,
            textvariable=sheet_var,
            state="readonly",
            width=30
        )
        sheet_combo.pack(side="left", padx=(0, 10))
        
        # 列选择（多选列表框）
        column_frame = ttk.LabelFrame(group_frame, text="列选择 (可多选)", padding=5)
        column_frame.pack(fill="both", expand=True, pady=5)
        
        # 创建列表框和滚动条
        listbox_frame = ttk.Frame(column_frame)
        listbox_frame.pack(fill="both", expand=True)
        
        column_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.EXTENDED,
            height=4,
            font=("Microsoft YaHei", 9)
        )
        column_scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=column_listbox.yview)
        column_listbox.configure(yscrollcommand=column_scrollbar.set)
        
        column_listbox.pack(side="left", fill="both", expand=True)
        column_scrollbar.pack(side="right", fill="y")
        
        # 列选择按钮
        column_button_frame = ttk.Frame(column_frame)
        column_button_frame.pack(fill="x", pady=(5, 0))
        
        ttk.Button(
            column_button_frame,
            text="全选",
            command=lambda: self._select_all_columns(column_listbox)
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            column_button_frame,
            text="清空",
            command=lambda: column_listbox.selection_clear(0, tk.END)
        ).pack(side="left", padx=(0, 5))
        
        # 删除按钮（第一个选择组不显示）
        if group_index > 0:
            ttk.Button(
                column_button_frame,
                text="删除此组",
                command=lambda: self._remove_selection_group(group_index)
            ).pack(side="right")
        
        # 存储选择组信息
        group_info = {
            'frame': group_frame,
            'excel_var': excel_var,
            'excel_combo': excel_combo,
            'sheet_var': sheet_var,
            'sheet_combo': sheet_combo,
            'column_listbox': column_listbox,
            'index': group_index
        }
        
        self.selection_groups.append(group_info)
        
        # 绑定事件
        excel_combo.bind('<<ComboboxSelected>>', lambda e: self._on_excel_selected(group_index))
        sheet_combo.bind('<<ComboboxSelected>>', lambda e: self._on_sheet_selected(group_index))
        column_listbox.bind('<<ListboxSelect>>', lambda e: self._on_column_selected())
        
        # 更新Excel文件列表
        self._update_excel_options(group_index)
    
    def _select_all_columns(self, listbox):
        """全选列"""
        listbox.selection_set(0, tk.END)
        self._on_column_selected()
    
    def _remove_selection_group(self, group_index):
        """删除指定的选择组"""
        if group_index < len(self.selection_groups):
            # 销毁组件
            self.selection_groups[group_index]['frame'].destroy()
            # 从列表中移除
            del self.selection_groups[group_index]
            
            # 重新排列剩余的选择组
            self._rearrange_selection_groups()
            
            # 触发选择变更回调
            self._on_column_selected()
    
    def _rearrange_selection_groups(self):
        """重新排列选择组"""
        for i, group in enumerate(self.selection_groups):
            group['frame'].grid(row=i, column=0, sticky="ew", padx=5, pady=5)
            group['index'] = i
            # 更新标题
            group['frame'].config(text=f"选择组 {i + 1}")
    
    def _update_excel_options(self, group_index):
        """更新Excel文件选项"""
        if group_index >= len(self.selection_groups):
            return
        
        group = self.selection_groups[group_index]
        excel_files = list(self.excel_data.keys())
        group['excel_combo']['values'] = excel_files
        
        # 清空Sheet和列选择
        group['sheet_combo']['values'] = []
        group['sheet_var'].set('')
        group['column_listbox'].delete(0, tk.END)
    
    def _on_excel_selected(self, group_index):
        """Excel文件选择事件"""
        if group_index >= len(self.selection_groups):
            return
        
        group = self.selection_groups[group_index]
        selected_excel = group['excel_var'].get()
        
        if selected_excel and selected_excel in self.excel_data:
            # 更新Sheet选项
            sheets = list(self.excel_data[selected_excel].keys())
            group['sheet_combo']['values'] = sheets
            
            # 清空当前Sheet和列选择
            group['sheet_var'].set('')
            group['column_listbox'].delete(0, tk.END)
        else:
            group['sheet_combo']['values'] = []
            group['sheet_var'].set('')
            group['column_listbox'].delete(0, tk.END)
    
    def _on_sheet_selected(self, group_index):
        """Sheet选择事件"""
        if group_index >= len(self.selection_groups):
            return
        
        group = self.selection_groups[group_index]
        selected_excel = group['excel_var'].get()
        selected_sheet = group['sheet_var'].get()
        
        if (selected_excel and selected_sheet and 
            selected_excel in self.excel_data and 
            selected_sheet in self.excel_data[selected_excel]):
            
            # 更新列选项
            columns = self.excel_data[selected_excel][selected_sheet]['columns']
            group['column_listbox'].delete(0, tk.END)
            
            for column in columns:
                group['column_listbox'].insert(tk.END, column)
        else:
            group['column_listbox'].delete(0, tk.END)
    
    def _on_column_selected(self):
        """列选择事件"""
        if self.on_selection_changed:
            selected_columns = self.get_selected_columns()
            self.on_selection_changed(selected_columns)
    
    def get_selected_columns(self):
        """获取所有选中的列"""
        selected_columns = []
        
        for group in self.selection_groups:
            excel_file = group['excel_var'].get()
            sheet_name = group['sheet_var'].get()
            
            if excel_file and sheet_name:
                # 获取选中的列索引
                selected_indices = group['column_listbox'].curselection()
                
                for index in selected_indices:
                    column_name = group['column_listbox'].get(index)
                    formatted_column = f"[{excel_file}-{sheet_name}] {column_name}"
                    selected_columns.append(formatted_column)
        
        return selected_columns
    
    def get_selected_columns_info(self):
        """获取选中列的详细信息"""
        selected_info = {}
        
        for group in self.selection_groups:
            excel_file = group['excel_var'].get()
            sheet_name = group['sheet_var'].get()
            
            if excel_file and sheet_name:
                key = f"{excel_file}#{sheet_name}"
                selected_indices = group['column_listbox'].curselection()
                
                if selected_indices:
                    columns = []
                    for index in selected_indices:
                        column_name = group['column_listbox'].get(index)
                        columns.append(column_name)
                    
                    if columns:
                        selected_info[key] = columns
        
        return selected_info
    
    def build_enhanced_prompt(self, requirement_text):
        """构建增强的用户提示词"""
        try:
            selected_info = self.get_selected_columns_info()
            
            if not selected_info:
                return requirement_text
            
            # 构建结构化提示词
            prompt_parts = [
                "## 数据处理需求",
                requirement_text,
                "",
                "## 数据结构信息"
            ]
            
            # 添加选中列的详细信息
            for file_sheet_key, columns in selected_info.items():
                file_name, sheet_name = file_sheet_key.split('#')
                
                if (file_name in self.excel_data and 
                    sheet_name in self.excel_data[file_name]):
                    
                    sheet_data = self.excel_data[file_name][sheet_name]
                    total_rows = sheet_data['total_rows']
                    
                    prompt_parts.extend([
                        "",
                        f"### {file_name} - {sheet_name} ({total_rows}行数据)",
                        "**选中的列：**"
                    ])
                    
                    for column in columns:
                        prompt_parts.append(f"- `{column}`")
            
            # 添加处理要求
            prompt_parts.extend([
                "",
                "## 处理要求",
                "请基于以上数据结构信息，生成相应的Excel公式来实现需求。",
                "注意考虑数据的实际格式和内容特征。"
            ])
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            print(f"构建提示词失败：{e}")
            return requirement_text
    
    def refresh_data(self):
        """刷新数据"""
        try:
            # 清空当前数据
            self.excel_data = {}
            
            # 重新加载数据
            success = self._load_data_with_priority()
            
            # 更新所有选择组的Excel选项
            for i in range(len(self.selection_groups)):
                self._update_excel_options(i)
            
            return success
            
        except Exception as e:
            print(f"刷新数据失败：{e}")
            return False
    
    def clear_selection(self):
        """清空所有选择"""
        # 保留第一个选择组，删除其他的
        while len(self.selection_groups) > 1:
            self._remove_selection_group(1)
        
        # 清空第一个选择组的选择
        if self.selection_groups:
            group = self.selection_groups[0]
            group['excel_var'].set('')
            group['sheet_var'].set('')
            group['sheet_combo']['values'] = []
            group['column_listbox'].delete(0, tk.END)
        
        # 触发选择变更回调
        self._on_column_selected()
    
    def get_widget(self):
        """获取组件widget"""
        return self.frame


class FormulaGenerationTab:
    """公式生成Tab主界面"""
    
    def __init__(self, parent, multi_excel_tab=None, 
                 get_column_list_callback: Optional[Callable] = None,
                 get_sample_data_callback: Optional[Callable] = None):
        """
        初始化公式生成Tab
        
        Args:
            parent: 父窗口
            multi_excel_tab: 多Excel Tab实例，用于获取数据
            get_column_list_callback: 获取列列表的回调函数（保持兼容性）
            get_sample_data_callback: 获取样本数据的回调函数（保持兼容性）
        """
        self.parent = parent
        self.multi_excel_tab = multi_excel_tab
        self.get_column_list_callback = get_column_list_callback
        self.get_sample_data_callback = get_sample_data_callback
        
        # 设置回调函数
        self.get_export_data_callback = None
        if multi_excel_tab:
            self.get_export_data_callback = multi_excel_tab.get_export_data
        
        # 初始化业务逻辑
        self.formula_generator = OptimizedFormulaGenerator()
        
        # 创建主框架
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 初始化UI组件
        self._setup_ui()
        
        # 加载初始数据
        self._load_initial_data()
        
        # 加载配置选项
        self._load_config_options()
    
    def _setup_ui(self):
        """设置UI界面"""
        # 创建左右分栏
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill="both", expand=True)
        
        # 左侧面板
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # 右侧面板
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=1)
        
        # 设置左侧面板
        self._setup_left_panel()
        
        # 设置右侧面板
        self._setup_right_panel()
    
    def _setup_left_panel(self):
        """设置左侧面板"""
        # 使用新的Excel-Sheet-列三级选择器
        self.column_selector = ExcelSheetColumnSelector(
            self.left_frame, 
            get_export_data_callback=self.get_export_data_callback
        )
        self.column_selector.on_selection_changed = self._on_column_selection_changed
        self.column_selector.get_widget().pack(fill="both", expand=True, pady=(0, 10))
        
        # 需求描述区域
        self.requirement_frame = ttk.LabelFrame(self.left_frame, text="需求描述", padding="10")
        self.requirement_frame.pack(fill="both", expand=True)
        
        # 需求输入框
        self.requirement_text = scrolledtext.ScrolledText(
            self.requirement_frame,
            height=6,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10)
        )
        self.requirement_text.pack(fill="both", expand=True, pady=(0, 10))
        
        # 添加占位符文本
        placeholder_text = """请详细描述您的数据处理需求，例如：

• 从H列的书目信息中提取时间。
• 如：时间：光绪十年一月五日(1884年2月1日) $$ 版本：手稿 $$ 附件：封1 $$ 主题词：苏州府；杭州府；盛宣怀；盛海颐 $$ 架位：3号架
• 提取后结果为：光绪十年一月五日(1884年2月1日)
• 也就是将`时间`和`$$`的内容提取出来

请清空此文本后输入您的具体需求..."""
        
        self.requirement_text.insert("1.0", placeholder_text)
        self.requirement_text.bind("<FocusIn>", self._on_requirement_focus_in)
        
        # 配置选项区域
        self.config_frame = ttk.LabelFrame(self.requirement_frame, text="生成配置", padding="10")
        self.config_frame.pack(fill="x", pady=(10, 10))
        
        # 第一行：提示词和大模型
        self.config_row1 = ttk.Frame(self.config_frame)
        self.config_row1.pack(fill="x", pady=(0, 5))
        
        # 提示词选择
        ttk.Label(self.config_row1, text="提示词:").pack(side="left", padx=(0, 5))
        self.prompt_var = tk.StringVar()
        self.prompt_combo = ttk.Combobox(
            self.config_row1,
            textvariable=self.prompt_var,
            state="readonly",
            width=20
        )
        self.prompt_combo.pack(side="left", padx=(0, 15))
        
        # 大模型选择
        ttk.Label(self.config_row1, text="大模型:").pack(side="left", padx=(0, 5))
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            self.config_row1,
            textvariable=self.model_var,
            state="readonly",
            width=20
        )
        self.model_combo.pack(side="left")
        
        # 第二行：temperature和top_p
        self.config_row2 = ttk.Frame(self.config_frame)
        self.config_row2.pack(fill="x")
        
        # Temperature
        ttk.Label(self.config_row2, text="Temperature:").pack(side="left", padx=(0, 5))
        self.temperature_var = tk.StringVar(value="0.3")
        self.temperature_entry = ttk.Entry(
            self.config_row2,
            textvariable=self.temperature_var,
            width=8
        )
        self.temperature_entry.pack(side="left", padx=(0, 15))
        
        # Top_p
        ttk.Label(self.config_row2, text="Top_p:").pack(side="left", padx=(0, 5))
        self.top_p_var = tk.StringVar(value="0.9")
        self.top_p_entry = ttk.Entry(
            self.config_row2,
            textvariable=self.top_p_var,
            width=8
        )
        self.top_p_entry.pack(side="left")
        
        # 按钮区域
        self.button_frame = ttk.Frame(self.requirement_frame)
        self.button_frame.pack(fill="x")
        
        # 生成公式按钮
        self.generate_button = ttk.Button(
            self.button_frame,
            text="生成公式",
            command=self._on_generate_formula,
            style="Accent.TButton"
        )
        self.generate_button.pack(side="left", padx=(0, 10))
        
        # 清空按钮
        self.clear_button = ttk.Button(
            self.button_frame,
            text="清空",
            command=self._on_clear_all
        )
        self.clear_button.pack(side="left", padx=(0, 10))
        
        # 刷新数据按钮
        self.refresh_button = ttk.Button(
            self.button_frame,
            text="刷新数据",
            command=self._on_refresh_data
        )
        self.refresh_button.pack(side="left")
    
    def _setup_right_panel(self):
        """设置右侧面板"""
        # 结果显示区域
        self.result_frame = ttk.LabelFrame(self.right_frame, text="生成结果", padding="10")
        self.result_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 创建结果显示区域
        self.result_text = scrolledtext.ScrolledText(
            self.result_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 10)
        )
        self.result_text.pack(fill="both", expand=True)
        
        # 创建按钮框架
        self.result_button_frame = ttk.Frame(self.result_frame)
        self.result_button_frame.pack(fill="x", pady=(10, 0))
        
        # 复制结果按钮
        self.copy_button = ttk.Button(
            self.result_button_frame,
            text="复制结果",
            command=self._copy_result,
            state=tk.DISABLED
        )
        self.copy_button.pack(side="left", padx=(0, 10))
        
        # 清空结果按钮
        self.clear_result_button = ttk.Button(
            self.result_button_frame,
            text="清空结果",
            command=self._clear_result
        )
        self.clear_result_button.pack(side="left")
        
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
    
    def _load_initial_data(self):
        """加载初始数据"""
        try:
            # 新的多Excel列选择器会自动加载数据，无需手动加载
            # 保持此方法以维持兼容性，但实际工作由ExcelSheetColumnSelector完成
            self.status_label.config(text="数据加载完成")
        except Exception as e:
            self.status_label.config(text=f"加载数据失败：{str(e)}")
    
    def _load_config_options(self):
        """加载配置选项"""
        try:
            print("开始加载配置选项...")
            
            # 加载提示词选项
            prompts = self.formula_generator.prompt_manager.get_all_prompts()
            print(f"获取到 {len(prompts)} 个提示词")
            
            # 移除过滤机制，显示所有提示词
            prompt_options = []
            formula_prompt_exists = False
            default_formula_prompt = None
            
            for prompt in prompts:
                prompt_name = prompt.get('name', prompt.get('id', ''))
                prompt_options.append(prompt_name)
                
                # 检查是否存在"Excel公式生成"提示词
                if 'Excel公式生成' in prompt_name:
                    formula_prompt_exists = True
                    default_formula_prompt = prompt_name
            
            print(f"提示词选项: {prompt_options}")
            self.prompt_combo['values'] = prompt_options
            
            # 设置默认值：优先选择"Excel公式生成"，没有则留空
            if formula_prompt_exists and default_formula_prompt:
                self.prompt_var.set(default_formula_prompt)
                print(f"设置默认提示词: {default_formula_prompt}")
            else:
                # 没有找到"Excel公式生成"相关提示词，留空让用户选择
                self.prompt_var.set("")
                print("未找到'Excel公式生成'提示词，留空让用户选择")
            
            # 加载大模型选项（保持不变）
            models = self.formula_generator.config_manager.get_all_models()
            print(f"获取到 {len(models)} 个模型配置")
            
            model_options = [model.get('name', model.get('model_id', '')) for model in models]
            
            if not model_options:
                model_options = ["默认模型"]
                print("未找到模型配置，使用默认值")
            
            print(f"模型选项: {model_options}")
            self.model_combo['values'] = model_options
            if model_options:
                self.model_var.set(model_options[0])
                
            print("配置选项加载完成")
                
        except Exception as e:
            print(f"加载配置选项失败：{e}")
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
            print("开始刷新配置选项...")
            
            # 保存当前选中的值
            current_prompt = self.prompt_var.get()
            current_model = self.model_var.get()
            print(f"当前选中 - 提示词: {current_prompt}, 模型: {current_model}")
            
            # 强制重新初始化配置管理器和提示词管理器，确保读取最新数据
            try:
                print("重新初始化配置管理器...")
                self.formula_generator.config_manager.reload_config()
                print("重新初始化提示词管理器...")
                self.formula_generator.prompt_manager.reload_prompts()
            except Exception as reload_error:
                print(f"重新加载配置时出现错误: {reload_error}")
            
            # 重新加载配置选项
            self._load_config_options()
            print("配置选项重新加载完成")
            
            # 尝试恢复之前的选择，如果不存在则检查默认值
            prompt_values = list(self.prompt_combo['values'])
            
            if current_prompt in prompt_values:
                self.prompt_var.set(current_prompt)
                print(f"恢复提示词选择: {current_prompt}")
            else:
                # 检查是否存在"Excel公式生成"作为默认值
                formula_prompt = None
                for value in prompt_values:
                    if 'Excel公式生成' in value:
                        formula_prompt = value
                        break
                
                if formula_prompt:
                    self.prompt_var.set(formula_prompt)
                    print(f"使用默认提示词: {formula_prompt}")
                else:
                    # 没有找到"Excel公式生成"相关提示词，留空让用户选择
                    self.prompt_var.set("")
                    print("未找到'Excel公式生成'提示词，留空让用户选择")
            
            # 模型选择逻辑保持不变...
            model_values = list(self.model_combo['values'])
            if current_model in model_values:
                self.model_var.set(current_model)
                print(f"恢复模型选择: {current_model}")
            else:
                print(f"原模型 '{current_model}' 不存在，使用默认值")
                
            # 强制更新UI显示
            self.prompt_combo.update()
            self.model_combo.update()
            print("UI更新完成")
                
            print("配置选项刷新完成")
                
        except Exception as e:
            print(f"刷新配置选项失败：{e}")
            import traceback
            traceback.print_exc()
    
    def _on_column_selection_changed(self, selected_columns: List[str]):
        """列选择变更回调"""
        count = len(selected_columns)
        if count == 0:
            self.status_label.config(text="请选择至少一列数据")
        else:
            # 限制显示的列名长度，避免状态栏过长
            if count <= 3:
                display_text = f"已选择 {count} 列：{', '.join(selected_columns)}"
            else:
                display_text = f"已选择 {count} 列：{', '.join(selected_columns[:2])} 等..."
            
            self.status_label.config(text=display_text)
    
    def _on_requirement_focus_in(self, event):
        """需求输入框获得焦点时的处理"""
        current_text = self.requirement_text.get("1.0", tk.END).strip()
        if "请清空此文本后输入您的具体需求" in current_text:
            self.requirement_text.delete("1.0", tk.END)
    
    def _on_generate_formula(self):
        """生成公式按钮点击事件 - 使用增强的提示词"""
        try:
            # 获取选中的列信息
            selected_info = self.column_selector.get_selected_columns_info()
            requirement = self.requirement_text.get("1.0", tk.END).strip()
            
            if not selected_info:
                messagebox.showwarning("警告", "请至少选择一列数据")
                return
            
            # 验证需求描述
            if not requirement or len(requirement) < 10:
                messagebox.showwarning("警告", "请输入详细的需求描述（至少10个字符）")
                return
            
            if "请清空此文本后输入您的具体需求" in requirement:
                messagebox.showwarning("警告", "请输入您的具体需求")
                return
            
            # 使用增强的提示词构建
            enhanced_prompt = self.column_selector.build_enhanced_prompt(requirement)
            
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
            self._show_generating_status()
            self.generate_button.config(state=tk.DISABLED, text="生成中...")
            self.status_label.config(text="正在生成公式...")
            
            # 异步生成公式（使用增强的提示词）
            self.formula_generator.generate_formula_async(
                requirement=enhanced_prompt,  # 使用增强的提示词
                columns=list(selected_info.keys()),  # 传递文件-Sheet键
                sample_data="",  # 预览数据已包含在enhanced_prompt中
                selected_prompt=selected_prompt,
                selected_model=selected_model,
                temperature=temperature,
                top_p=top_p,
                success_callback=self._on_formula_generated,
                error_callback=self._on_formula_error,
                progress_callback=self._on_generation_progress
            )
            
        except Exception as e:
            messagebox.showerror("错误", f"生成公式时出错：{str(e)}")
            self._reset_generate_button()
    
    def _show_generating_status(self, message: str = "正在生成公式，请稍候..."):
        """显示生成状态"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", f"⏳ {message}")
        self.result_text.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
    
    def _on_formula_generated(self, result: Dict[str, Any]):
        """公式生成成功回调"""
        # 使用after方法确保在主线程中更新UI
        self.parent.after(0, self._update_ui_after_generation, result)
    
    def _on_formula_error(self, result: Dict[str, Any]):
        """公式生成失败回调"""
        # 使用after方法确保在主线程中更新UI
        self.parent.after(0, self._update_ui_after_generation, result)
    
    def _on_generation_progress(self, message: str):
        """生成进度回调"""
        self.parent.after(0, lambda: self.status_label.config(text=message))
    
    def _update_ui_after_generation(self, result: Dict[str, Any]):
        """在主线程中更新UI"""
        try:
            # 显示结果
            self._display_result(result)
            
            # 更新状态
            if result['success']:
                self.status_label.config(text="公式生成成功")
            else:
                self.status_label.config(text=f"生成失败：{result['error']}")
            
            # 更新统计信息
            self._update_statistics()
            
        except Exception as e:
            print(f"更新UI时出错：{e}")
        finally:
            # 恢复按钮状态
            self._reset_generate_button()
    
    def _display_result(self, result: Dict[str, Any]):
        """显示生成结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        
        if result['success']:
            # 成功结果 - 直接显示大模型返回的内容
            content = f"✅ 公式生成成功\n\n"
            content += result['explanation']  # 直接显示大模型的完整响应
            
            self.result_text.insert("1.0", content)
            self.copy_button.config(state=tk.NORMAL)
            
        else:
            # 失败结果
            content = f"❌ 公式生成失败\n\n"
            content += f"错误信息：{result['error']}\n"
            
            if result['explanation']:
                content += f"\nAI响应：{result['explanation']}"
            
            self.result_text.insert("1.0", content)
            self.copy_button.config(state=tk.DISABLED)
            
            # 设置错误信息样式
            self.result_text.tag_add("error", "3.5", "3.end")
            self.result_text.tag_config("error", foreground="red")
        
        self.result_text.config(state=tk.DISABLED)
    
    def _copy_result(self):
        """复制全部结果文本到剪贴板"""
        try:
            # 启用文本编辑状态
            self.result_text.config(state=tk.NORMAL)
            # 获取全部文本内容
            all_text = self.result_text.get("1.0", tk.END).strip()
            # 恢复只读状态
            self.result_text.config(state=tk.DISABLED)
            
            # 复制到剪贴板
            pyperclip.copy(all_text)
            messagebox.showinfo("成功", "全部内容已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败：{str(e)}")
    
    def _clear_result(self):
        """清空结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
    
    def _reset_generate_button(self):
        """重置生成按钮状态"""
        self.generate_button.config(state=tk.NORMAL, text="生成公式")
    
    def _on_clear_all(self):
        """清空所有内容"""
        # 清空列选择
        self.column_selector.clear_selection()
        
        # 清空需求描述
        self.requirement_text.delete("1.0", tk.END)
        placeholder_text = """请详细描述您的数据处理需求，例如：

• 从H列的书目信息中提取时间。
• 如：时间：光绪十年一月五日(1884年2月1日) $$ 版本：手稿 $$ 附件：封1 $$ 主题词：苏州府；杭州府；盛宣怀；盛海颐 $$ 架位：3号架
• 提取后结果为：光绪十年一月五日(1884年2月1日)
• 也就是将`时间`和`$$`的内容提取出来

请清空此文本后输入您的具体需求..."""
        self.requirement_text.insert("1.0", placeholder_text)
        
        # 清空结果
        self._clear_result()
        
        # 更新状态
        self.status_label.config(text="已清空所有内容")
    
    def _on_refresh_data(self):
        """刷新数据"""
        # 刷新多Excel列选择器的数据
        success = self.column_selector.refresh_data()
        
        if success:
            self.status_label.config(text="数据刷新成功")
        else:
            self.status_label.config(text="数据刷新失败，请检查数据源")
        
        # 更新统计信息
        self._update_statistics()
    
    def _update_statistics(self):
        """更新统计信息"""
        try:
            cache_stats = self.formula_generator.get_cache_statistics()
            history_stats = self.formula_generator.get_history_statistics()
            
            stats_text = f"缓存: {cache_stats['cache_size']}/{cache_stats['max_cache_size']} | "
            stats_text += f"历史: {history_stats['total_formulas']}"
            
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
            self.formula_generator.clear_cache()
        except Exception as e:
            print(f"清理资源时出错：{e}")


# 测试代码
if __name__ == "__main__":
    def test_get_columns():
        return ["A列-姓名", "B列-年龄", "C列-部门", "D列-薪资", "E列-入职日期", "F列-绩效"]
    
    def test_get_sample_data():
        return """姓名,年龄,部门,薪资,入职日期,绩效
张三,28,技术部,8000,2022-01-15,优秀
李四,32,销售部,6500,2021-03-20,良好
王五,25,技术部,7200,2023-02-10,优秀
赵六,35,人事部,5800,2020-05-12,良好
钱七,29,技术部,9500,2022-08-30,优秀"""
    
    root = tk.Tk()
    root.title("公式生成Tab测试")
    root.geometry("1200x800")
    
    # 创建公式生成Tab
    formula_tab = FormulaGenerationTab(
        root, 
        get_column_list_callback=test_get_columns,
        get_sample_data_callback=test_get_sample_data
    )
    
    root.mainloop()