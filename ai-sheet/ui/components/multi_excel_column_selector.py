#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多Excel列选择器组件
优先读取临时文件，实现与多Excel Tab的深度集成
"""

import tkinter as tk
from tkinter import ttk
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable


class MultiExcelColumnSelector:
    """多Excel列选择器 - 优先读取临时文件"""
    
    def __init__(self, parent, get_export_data_callback=None):
        self.parent = parent
        self.get_export_data_callback = get_export_data_callback
        self.selected_columns = {}  # {file_sheet_key: [selected_columns]}
        self.excel_data = {}  # 完整的Excel数据结构
        self.preview_data = ""  # MD预览数据
        
        # 界面组件
        self.file_groups = {}  # 文件分组组件
        self.sheet_groups = {}  # Sheet分组组件
        self.column_checkboxes = {}  # 列复选框
        
        # 状态组件
        self.source_info_label = None  # 数据来源标签
        self.status_label = None  # 状态标签
        self.preview_text = None  # 预览文本框
        
        # 回调函数
        self.on_selection_changed = None
        
        # 创建界面并加载数据
        self._create_ui()
        self._load_data_with_priority()
    
    def _create_ui(self):
        """创建分层选择界面"""
        # 主框架
        self.main_frame = ttk.LabelFrame(self.parent, text="📊 多Excel数据选择", padding=10)
        self.main_frame.pack(fill="both", expand=True)
        
        # 数据来源信息区域
        self.info_frame = ttk.Frame(self.main_frame)
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
            text="🔄 刷新数据",
            command=self.refresh_data
        )
        self.refresh_btn.pack(side="right")
        
        # 创建滚动区域用于显示文件-Sheet-列的分层结构
        self.canvas = tk.Canvas(self.main_frame, height=300)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 配置滚动
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 布局滚动区域
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # 预览区域
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="👁️ 数据预览", padding=5)
        self.preview_frame.pack(fill="x", pady=(10, 0))
        
        self.preview_text = tk.Text(
            self.preview_frame,
            height=6,
            wrap=tk.WORD,
            font=("Consolas", 8),
            state=tk.DISABLED
        )
        self.preview_text.pack(fill="x")
        
        # 状态区域
        self.status_label = ttk.Label(
            self.main_frame,
            text="准备就绪",
            font=("Microsoft YaHei", 8),
            foreground="gray"
        )
        self.status_label.pack(anchor="w", pady=(5, 0))
    
    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _load_data_with_priority(self):
        """按优先级加载数据：临时文件 > 回调函数 > 空状态"""
        try:
            # 策略1：优先读取临时文件
            if self._load_from_temp_files():
                self._update_ui_from_temp_data()
                self._show_status("✅ 已从保存的数据中加载", "success")
                return True
            
            # 策略2：通过回调函数获取实时数据
            if self._load_from_callback():
                self._update_ui_from_callback_data()
                self._show_status("🔄 已加载当前选择数据（未保存）", "warning")
                return True
            
            # 策略3：显示空状态
            self._show_empty_state()
            self._show_status("📋 请先在多Excel Tab中选择数据", "info")
            return False
            
        except Exception as e:
            print(f"加载数据失败：{e}")
            self._show_error_state(str(e))
            return False
    
    def _load_from_temp_files(self):
        """从临时文件加载数据"""
        try:
            # 检查临时文件是否存在
            json_file = os.path.join("logs", "multi_excel_selections.json")
            md_file = os.path.join("logs", "multi_excel_preview.md")
            
            if not (os.path.exists(json_file) and os.path.exists(md_file)):
                print("临时文件不存在，跳过临时文件加载")
                return False
            
            # 读取JSON结构化数据
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # 读取MD预览数据
            with open(md_file, 'r', encoding='utf-8') as f:
                self.preview_data = f.read()
            
            # 解析JSON数据到内部结构
            self._parse_json_data(json_data)
            
            print(f"✅ 成功从临时文件加载数据：{len(self.excel_data)} 个文件-Sheet组合")
            return True
            
        except Exception as e:
            print(f"从临时文件加载数据失败：{e}")
            return False
    
    def _parse_json_data(self, json_data):
        """解析JSON数据到内部结构"""
        self.excel_data = {}
        
        for selection in json_data.get('selections', []):
            if 'error' in selection:
                continue  # 跳过错误的选择
            
            file_name = selection['file_name']
            sheet_name = selection['sheet_name']
            key = f"{file_name}#{sheet_name}"
            
            self.excel_data[key] = {
                'file_path': selection['file_path'],
                'file_name': file_name,
                'sheet_name': sheet_name,
                'columns': selection['column_names'],
                'total_rows': selection['total_rows'],
                'column_count': selection['columns'],
                'file_size': selection.get('file_size', 0),
                'truncated': selection.get('truncated', False),
                'source': 'temp_file'  # 标记数据来源
            }
    
    def _load_from_callback(self):
        """通过回调函数获取实时数据"""
        try:
            if not self.get_export_data_callback:
                print("回调函数不可用")
                return False
            
            # 调用回调函数获取数据
            callback_data = self.get_export_data_callback()
            if not callback_data or not callback_data.get('selections'):
                print("回调函数返回空数据")
                return False
            
            # 解析回调数据
            self._parse_callback_data(callback_data)
            
            print(f"✅ 成功从回调函数加载数据：{len(self.excel_data)} 个文件-Sheet组合")
            return True
            
        except Exception as e:
            print(f"从回调函数加载数据失败：{e}")
            return False
    
    def _parse_callback_data(self, callback_data):
        """解析回调数据到内部结构"""
        self.excel_data = {}
        
        for selection in callback_data.get('selections', []):
            if 'error' in selection:
                continue
            
            file_name = selection['file_name']
            sheet_name = selection['sheet_name']
            key = f"{file_name}#{sheet_name}"
            
            self.excel_data[key] = {
                'file_path': selection['file_path'],
                'file_name': file_name,
                'sheet_name': sheet_name,
                'columns': selection['column_names'],
                'total_rows': selection['total_rows'],
                'column_count': selection['columns'],
                'file_size': selection.get('file_size', 0),
                'truncated': selection.get('truncated', False),
                'source': 'callback'  # 标记数据来源
            }
        
        # 生成预览数据
        self.preview_data = self._generate_preview_from_callback(callback_data)
    
    def _generate_preview_from_callback(self, callback_data):
        """从回调数据生成预览"""
        try:
            preview_lines = ["# 数据预览（实时获取）\n"]
            
            for selection in callback_data.get('selections', []):
                if 'error' in selection:
                    continue
                
                file_name = selection['file_name']
                sheet_name = selection['sheet_name']
                preview_lines.append(f"## {file_name} - {sheet_name}")
                preview_lines.append(f"总行数: {selection['total_rows']}")
                preview_lines.append(f"列数: {selection['columns']}")
                preview_lines.append(f"列名: {', '.join(selection['column_names'])}")
                preview_lines.append("")
            
            return "\n".join(preview_lines)
            
        except Exception as e:
            print(f"生成预览数据失败：{e}")
            return "预览数据生成失败"
    
    def _update_ui_from_temp_data(self):
        """基于临时文件数据更新界面"""
        try:
            # 清空现有界面
            self._clear_selection_area()
            
            # 按文件分组显示
            file_groups = self._group_by_file()
            
            for file_name, sheets in file_groups.items():
                # 创建文件分组
                file_frame = self._create_file_group(file_name)
                
                for sheet_data in sheets:
                    # 创建Sheet分组
                    sheet_frame = self._create_sheet_group(file_frame, sheet_data)
                    
                    # 创建列选择器
                    self._create_column_selectors(sheet_frame, sheet_data)
            
            # 显示预览数据
            self._update_preview_display()
            
            # 显示数据来源信息
            self._show_data_source_info("temp_file")
            
        except Exception as e:
            print(f"更新界面失败：{e}")
    
    def _update_ui_from_callback_data(self):
        """基于回调数据更新界面"""
        # 与临时文件数据更新逻辑相同
        self._update_ui_from_temp_data()
        self._show_data_source_info("callback")
    
    def _clear_selection_area(self):
        """清空选择区域"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.file_groups = {}
        self.sheet_groups = {}
        self.column_checkboxes = {}
        self.selected_columns = {}
    
    def _group_by_file(self):
        """按文件分组数据"""
        file_groups = {}
        
        for key, data in self.excel_data.items():
            file_name = data['file_name']
            if file_name not in file_groups:
                file_groups[file_name] = []
            file_groups[file_name].append(data)
        
        return file_groups
    
    def _create_file_group(self, file_name):
        """创建文件分组"""
        file_frame = ttk.LabelFrame(
            self.scrollable_frame,
            text=f"📁 {file_name}",
            padding=5
        )
        file_frame.pack(fill="x", pady=5)
        
        self.file_groups[file_name] = file_frame
        return file_frame
    
    def _create_sheet_group(self, parent, sheet_data):
        """创建Sheet分组"""
        sheet_name = sheet_data['sheet_name']
        total_rows = sheet_data['total_rows']
        
        sheet_frame = ttk.LabelFrame(
            parent,
            text=f"📊 {sheet_name} ({total_rows}行)",
            padding=5
        )
        sheet_frame.pack(fill="x", pady=2)
        
        key = f"{sheet_data['file_name']}#{sheet_name}"
        self.sheet_groups[key] = sheet_frame
        return sheet_frame
    
    def _create_column_selectors(self, parent, sheet_data):
        """创建列选择器"""
        columns = sheet_data['columns']
        file_name = sheet_data['file_name']
        sheet_name = sheet_data['sheet_name']
        key = f"{file_name}#{sheet_name}"
        
        # 创建列选择区域
        column_frame = ttk.LabelFrame(
            parent, 
            text=f"📊 列选择 ({len(columns)} 列)",
            padding=5
        )
        column_frame.pack(fill="x", pady=5)
        
        # 创建列选择的滚动区域
        col_canvas = tk.Canvas(column_frame, height=120)
        col_scrollbar = ttk.Scrollbar(column_frame, orient="vertical", command=col_canvas.yview)
        col_scrollable_frame = ttk.Frame(col_canvas)
        
        # 为每列创建复选框
        self.selected_columns[key] = []
        column_vars = {}
        
        for i, column in enumerate(columns):
            var = tk.BooleanVar()
            column_vars[column] = var
            
            # 创建复选框
            cb = ttk.Checkbutton(
                col_scrollable_frame,
                text=f"[{file_name}-{sheet_name}] {column}",
                variable=var,
                command=lambda k=key, c=column, v=var: self._on_column_selected(k, c, v)
            )
            cb.grid(row=i, column=0, sticky="w", padx=5, pady=2)
        
        # 添加批量选择按钮
        button_frame = ttk.Frame(col_scrollable_frame)
        button_frame.grid(row=len(columns), column=0, sticky="ew", pady=10)
        
        ttk.Button(
            button_frame,
            text="全选",
            command=lambda: self._select_all_columns(key, column_vars)
        ).pack(side="left", padx=5)
        
        ttk.Button(
            button_frame,
            text="清空",
            command=lambda: self._clear_all_columns(key, column_vars)
        ).pack(side="left", padx=5)
        
        # 配置滚动
        col_scrollable_frame.bind(
            "<Configure>",
            lambda e: col_canvas.configure(scrollregion=col_canvas.bbox("all"))
        )
        
        col_canvas.create_window((0, 0), window=col_scrollable_frame, anchor="nw")
        col_canvas.configure(yscrollcommand=col_scrollbar.set)
        
        col_canvas.pack(side="left", fill="both", expand=True)
        col_scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮
        col_canvas.bind("<MouseWheel>", lambda e: col_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # 存储组件引用
        self.column_checkboxes[key] = column_vars
    
    def _on_column_selected(self, key, column, var):
        """列选择事件处理"""
        if var.get():
            if column not in self.selected_columns[key]:
                self.selected_columns[key].append(column)
        else:
            if column in self.selected_columns[key]:
                self.selected_columns[key].remove(column)
        
        # 触发选择变更回调
        if self.on_selection_changed:
            self.on_selection_changed(self.get_selected_columns_list())
    
    def _select_all_columns(self, key, column_vars):
        """全选列"""
        for column, var in column_vars.items():
            var.set(True)
            if column not in self.selected_columns[key]:
                self.selected_columns[key].append(column)
        
        if self.on_selection_changed:
            self.on_selection_changed(self.get_selected_columns_list())
    
    def _clear_all_columns(self, key, column_vars):
        """清空列选择"""
        for column, var in column_vars.items():
            var.set(False)
        
        self.selected_columns[key] = []
        
        if self.on_selection_changed:
            self.on_selection_changed(self.get_selected_columns_list())
    
    def _update_preview_display(self):
        """更新预览显示"""
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        
        if self.preview_data:
            # 限制预览数据长度
            preview_content = self.preview_data[:2000]
            if len(self.preview_data) > 2000:
                preview_content += "\n\n... (内容已截断)"
            
            self.preview_text.insert("1.0", preview_content)
        else:
            self.preview_text.insert("1.0", "暂无预览数据")
        
        self.preview_text.config(state=tk.DISABLED)
    
    def _show_data_source_info(self, source_type):
        """显示数据来源信息"""
        if source_type == "temp_file":
            # 读取保存时间
            try:
                json_file = os.path.join("logs", "multi_excel_selections.json")
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                saved_at = json_data.get('metadata', {}).get('saved_at', '')
                if saved_at:
                    dt = datetime.fromisoformat(saved_at)
                    time_str = dt.strftime('%Y-%m-%d %H:%M')
                    
                    self.source_info_label.config(
                        text=f"📁 数据来源：已保存的选择 (保存时间: {time_str})",
                        foreground="green"
                    )
                else:
                    self.source_info_label.config(
                        text="📁 数据来源：已保存的选择",
                        foreground="green"
                    )
            except:
                self.source_info_label.config(
                    text="📁 数据来源：已保存的选择",
                    foreground="green"
                )
        
        elif source_type == "callback":
            self.source_info_label.config(
                text="🔄 数据来源：当前选择 (未保存，建议先保存)",
                foreground="orange"
            )
        
        else:
            self.source_info_label.config(
                text="❌ 无数据：请先在多Excel Tab中选择文件和Sheet",
                foreground="red"
            )
    
    def _show_empty_state(self):
        """显示空状态"""
        empty_frame = ttk.Frame(self.scrollable_frame)
        empty_frame.pack(fill="both", expand=True, pady=50)
        
        empty_label = ttk.Label(
            empty_frame,
            text="📋 暂无数据\n\n请先在多Excel Tab中：\n1. 上传Excel文件\n2. 选择Sheet\n3. 保存选择\n\n然后返回此页面刷新数据",
            font=("Microsoft YaHei", 10),
            foreground="gray",
            justify="center"
        )
        empty_label.pack(anchor="center")
    
    def _show_error_state(self, error_msg):
        """显示错误状态"""
        error_frame = ttk.Frame(self.scrollable_frame)
        error_frame.pack(fill="both", expand=True, pady=50)
        
        error_label = ttk.Label(
            error_frame,
            text=f"❌ 加载数据时出错\n\n{error_msg}\n\n请检查数据源或刷新重试",
            font=("Microsoft YaHei", 10),
            foreground="red",
            justify="center"
        )
        error_label.pack(anchor="center")
    
    def _show_status(self, message, status_type):
        """显示状态信息"""
        color_map = {
            "success": "green",
            "warning": "orange", 
            "error": "red",
            "info": "blue"
        }
        
        self.status_label.config(
            text=message,
            foreground=color_map.get(status_type, "gray")
        )
    
    def refresh_data(self):
        """刷新数据 - 重新按优先级加载"""
        try:
            # 清空当前数据
            self.excel_data = {}
            self.selected_columns = {}
            self.preview_data = ""
            
            # 重新加载数据
            success = self._load_data_with_priority()
            
            if success:
                self._show_status("🔄 数据已刷新", "success")
            else:
                self._show_status("❌ 刷新失败，请检查数据源", "error")
            
            return success
            
        except Exception as e:
            print(f"刷新数据失败：{e}")
            self._show_status(f"❌ 刷新失败：{str(e)}", "error")
            return False
    
    def get_selected_columns_list(self):
        """获取选中列的列表格式（兼容原接口）"""
        selected_list = []
        
        for file_sheet_key, columns in self.selected_columns.items():
            for column in columns:
                # 格式：[文件名-Sheet名] 列名
                file_name, sheet_name = file_sheet_key.split('#')
                selected_list.append(f"[{file_name}-{sheet_name}] {column}")
        
        return selected_list
    
    def get_selected_columns_info(self):
        """获取选中列的详细信息"""
        selected_info = {}
        
        for file_sheet_key, columns in self.selected_columns.items():
            if columns:  # 只返回有选中列的
                selected_info[file_sheet_key] = columns
        
        return selected_info
    
    def build_enhanced_prompt(self, requirement_text):
        """构建增强的用户提示词"""
        try:
            selected_info = self.get_selected_columns_info()
            
            if not selected_info:
                return requirement_text
            
            # 构建结构化提示词
            prompt_parts = [
                "## 📋 数据处理需求",
                requirement_text,
                "",
                "## 📊 数据结构信息"
            ]
            
            # 添加选中列的详细信息
            for file_sheet_key, columns in selected_info.items():
                sheet_data = self.excel_data[file_sheet_key]
                file_name = sheet_data['file_name']
                sheet_name = sheet_data['sheet_name']
                total_rows = sheet_data['total_rows']
                
                prompt_parts.extend([
                    f"",
                    f"### 📁 {file_name} - {sheet_name} ({total_rows}行数据)",
                    f"**选中的列：**"
                ])
                
                for column in columns:
                    prompt_parts.append(f"- `{column}`")
            
            # 添加预览数据（如果有）
            if self.preview_data:
                prompt_parts.extend([
                    "",
                    "## 👁️ 数据预览",
                    "```markdown",
                    self.preview_data[:2000] + ("..." if len(self.preview_data) > 2000 else ""),
                    "```"
                ])
            
            # 添加处理要求
            prompt_parts.extend([
                "",
                "## 🎯 处理要求",
                "请基于以上数据结构和预览信息，生成相应的Excel公式来实现需求。",
                "注意考虑数据的实际格式和内容特征。"
            ])
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            print(f"构建提示词失败：{e}")
            return requirement_text
    
    def get_widget(self):
        """获取主组件"""
        return self.main_frame
    
    def clear_selection(self):
        """清空所有选择"""
        for key in self.selected_columns:
            self.selected_columns[key] = []
        
        # 更新UI中的复选框状态
        for key, column_vars in self.column_checkboxes.items():
            for var in column_vars.values():
                var.set(False)
        
        if self.on_selection_changed:
            self.on_selection_changed([])