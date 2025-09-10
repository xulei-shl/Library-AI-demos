#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多Excel多Sheet选择组件
可复用的UI组件，支持动态添加/删除Excel-Sheet选择组合
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from typing import List, Tuple, Callable, Optional
from modules.multi_excel_utils import MultiExcelManager


class ExcelSheetSelector:
    """单个Excel-Sheet选择器"""
    
    def __init__(self, parent, manager: MultiExcelManager, on_change: Callable = None, on_remove: Callable = None):
        self.parent = parent
        self.manager = manager
        self.on_change = on_change
        self.on_remove = on_remove
        
        # 变量
        self.excel_var = tk.StringVar()
        self.sheet_var = tk.StringVar()
        self.selected_columns = []  # 存储选中的列
        
        # 创建UI
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        
        # 绑定事件
        self.excel_var.trace('w', self._on_excel_change)
        self.sheet_var.trace('w', self._on_sheet_change)
    
    def setup_ui(self):
        """创建UI元素"""
        # Excel文件选择
        excel_frame = ttk.Frame(self.frame)
        excel_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(excel_frame, text="Excel文件:", width=10).pack(side=tk.LEFT)
        
        self.excel_combo = ttk.Combobox(
            excel_frame, 
            textvariable=self.excel_var,
            state="readonly",
            width=40
        )
        self.excel_combo.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
        
        # 浏览按钮
        browse_btn = ttk.Button(
            excel_frame,
            text="浏览",
            command=self._browse_excel,
            width=8
        )
        browse_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 删除按钮
        remove_btn = ttk.Button(
            excel_frame,
            text="删除",
            command=self._remove_selector,
            width=8
        )
        remove_btn.pack(side=tk.LEFT)
        
        # Sheet选择
        sheet_frame = ttk.Frame(self.frame)
        sheet_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(sheet_frame, text="Sheet:", width=10).pack(side=tk.LEFT)
        
        self.sheet_combo = ttk.Combobox(
            sheet_frame,
            textvariable=self.sheet_var,
            state="readonly",
            width=40
        )
        self.sheet_combo.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # 列选择区域
        columns_frame = ttk.Frame(self.frame)
        columns_frame.pack(fill=tk.X)
        
        ttk.Label(columns_frame, text="列选择:", width=10).pack(side=tk.LEFT, anchor=tk.N, pady=(5, 0))
        
        # 列选择右侧容器
        columns_right_frame = ttk.Frame(columns_frame)
        columns_right_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 列选择下拉框
        columns_select_frame = ttk.Frame(columns_right_frame)
        columns_select_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.columns_combo = ttk.Combobox(
            columns_select_frame,
            state="readonly",
            width=25  # 减少宽度以为按钮留出更多空间
        )
        self.columns_combo.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)  # 添加自适应宽度
        self.columns_combo.bind('<<ComboboxSelected>>', self._on_column_select)
        
        # 添加列按钮
        add_column_btn = ttk.Button(
            columns_select_frame,
            text="添加列",
            command=self._add_selected_column,
            width=8
        )
        add_column_btn.pack(side=tk.LEFT)
        
        # 已选择列显示区域 - 添加滚动条支持
        selected_scroll_frame = ttk.Frame(columns_right_frame)
        selected_scroll_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 创建Canvas和Scrollbar用于滚动
        self.selected_canvas = tk.Canvas(selected_scroll_frame, height=100)  # 增加高度以适应网格布局
        self.selected_scrollbar = ttk.Scrollbar(selected_scroll_frame, orient="vertical", command=self.selected_canvas.yview)
        self.selected_scrollable_frame = ttk.Frame(self.selected_canvas)
        
        self.selected_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))
        )
        
        self.selected_canvas.create_window((0, 0), window=self.selected_scrollable_frame, anchor="nw")
        self.selected_canvas.configure(yscrollcommand=self.selected_scrollbar.set)
        
        # 添加鼠标滚轮支持
        def _on_mousewheel(event):
            self.selected_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.selected_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.selected_scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # 布局Canvas和Scrollbar
        self.selected_canvas.pack(side="left", fill="both", expand=True)
        self.selected_scrollbar.pack(side="right", fill="y")
        
        # 选中的列显示区域（现在在可滚动框架内）
        self.selected_columns_frame = self.selected_scrollable_frame
        
        # 更新Excel文件列表
        self._update_excel_list()
    
    def _browse_excel(self):
        """浏览选择Excel文件"""
        file_types = [("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=file_types
        )
        
        if not file_path:
            return
        
        # 添加到管理器
        success, error_msg, sheets = self.manager.add_excel_file(file_path)
        if not success:
            messagebox.showerror("文件错误", error_msg)
            return
        
        # 更新Excel列表
        self._update_excel_list()
        
        # 选择新添加的文件
        self.excel_var.set(file_path)
    
    def _update_excel_list(self):
        """更新Excel文件列表"""
        files = self.manager.get_all_files()
        file_display_names = [f"{os.path.basename(f)} ({f})" for f in files]
        self.excel_combo['values'] = file_display_names
    
    def _update_sheet_list(self, file_path: str):
        """更新Sheet列表"""
        if file_path:
            sheets = self.manager.get_file_sheets(file_path)
            self.sheet_combo['values'] = sheets
            if sheets:
                self.sheet_var.set(sheets[0])  # 默认选择第一个Sheet
            else:
                self.sheet_var.set("")
        else:
            self.sheet_combo['values'] = []
            self.sheet_var.set("")
    
    def _on_excel_change(self, *args):
        """Excel选择变化事件"""
        display_name = self.excel_var.get()
        if display_name:
            # 从显示名称中提取文件路径
            file_path = display_name.split(" (")[-1].rstrip(")")
            self._update_sheet_list(file_path)
        else:
            self._update_sheet_list("")
        
        if self.on_change:
            self.on_change()
    
    def _on_sheet_change(self, *args):
        """Sheet选择变化事件"""
        self._update_columns_list()
        if self.on_change:
            self.on_change()
    
    def _update_columns_list(self):
        """更新列选择下拉框"""
        display_name = self.excel_var.get()
        sheet_name = self.sheet_var.get()
        
        if display_name and sheet_name:
            try:
                # 从显示名称中提取文件路径
                file_path = display_name.split(" (")[-1].rstrip(")")
                
                # 获取Sheet数据以获取列信息
                sheet_data = self.manager.get_sheet_data(file_path, sheet_name)
                columns = sheet_data['columns']
                
                # 更新下拉框选项
                self.columns_combo['values'] = columns
                
                # 清空当前选择
                self.columns_combo.set("")
                
            except Exception as e:
                print(f"更新列列表失败: {e}")
                self.columns_combo['values'] = []
        else:
            self.columns_combo['values'] = []
    
    def _on_column_select(self, event):
        """列选择事件"""
        pass  # 选择后不自动添加，需要点击添加按钮
    
    def _add_selected_column(self):
        """添加选中的列"""
        selected_column = self.columns_combo.get()
        if selected_column and selected_column not in self.selected_columns:
            self.selected_columns.append(selected_column)
            self._update_selected_columns_display()
            if self.on_change:
                self.on_change()
    
    def _update_selected_columns_display(self):
        """更新已选择列的显示"""
        # 清除现有显示
        for widget in self.selected_columns_frame.winfo_children():
            widget.destroy()
        
        # 如果没有选中的列，显示提示信息
        if not self.selected_columns:
            tip_label = ttk.Label(
                self.selected_columns_frame,
                text="尚未选择任何列",
                font=("微软雅黑", 9),
                foreground="#888888"
            )
            tip_label.grid(row=0, column=0, pady=5, sticky="w")
            return
        
        # 使用网格布局实现响应式换行
        self._layout_selected_columns_grid()
        
        # 更新滚动区域
        if hasattr(self, 'selected_canvas'):
            self.selected_canvas.update_idletasks()
            self.selected_canvas.configure(scrollregion=self.selected_canvas.bbox("all"))
    
    def _layout_selected_columns_grid(self):
        """使用网格布局排列列标签，实现响应式换行"""
        # 估算每个列标签的宽度（包括删除按钮和间距）
        estimated_item_width = 120  # 根据字体和按钮大小估算
        padding_x = 8  # 水平间距
        
        # 获取容器宽度，如果无法获取则使用默认值
        try:
            self.selected_canvas.update_idletasks()
            container_width = self.selected_canvas.winfo_width()
            if container_width <= 1:  # 如果还没有渲染完成
                container_width = 400  # 使用默认宽度
        except:
            container_width = 400
        
        # 计算每行可容纳的列数
        columns_per_row = max(1, (container_width - 20) // (estimated_item_width + padding_x))
        
        # 使用网格布局排列列标签
        for i, column in enumerate(self.selected_columns):
            row = i // columns_per_row
            col = i % columns_per_row
            
            # 每个列标签和删除按钮的容器
            column_item = ttk.Frame(self.selected_columns_frame)
            column_item.grid(row=row, column=col, padx=(0, padding_x), pady=2, sticky="w")
            
            # 列名标签 - 使用更紧凑的样式
            column_label = ttk.Label(
                column_item,
                text=column,
                font=("微软雅黑", 8),
                background="#e3f2fd",
                relief="solid",
                borderwidth=1,
                padding=(4, 2)
            )
            column_label.pack(side=tk.LEFT, padx=(0, 2))
            
            # 删除按钮 - 使用更小的按钮
            remove_btn = ttk.Button(
                column_item,
                text="×",
                command=lambda col=column: self._remove_selected_column(col),
                width=2
            )
            remove_btn.pack(side=tk.LEFT)
    
    def _remove_selected_column(self, column):
        """删除选中的列"""
        if column in self.selected_columns:
            self.selected_columns.remove(column)
            self._update_selected_columns_display()
            if self.on_change:
                self.on_change()
    
    def _remove_selector(self):
        """删除当前选择器"""
        if self.on_remove:
            self.on_remove(self)
    
    def get_selection(self) -> Optional[Tuple[str, str, List[str]]]:
        """获取当前选择的文件、Sheet和列
        
        返回:
            (file_path, sheet_name, selected_columns) 或 None
        """
        display_name = self.excel_var.get()
        sheet_name = self.sheet_var.get()
        
        if display_name and sheet_name:
            # 从显示名称中提取文件路径
            file_path = display_name.split(" (")[-1].rstrip(")")
            return file_path, sheet_name, self.selected_columns.copy()
        
        return None
    
    def set_selection(self, file_path: str, sheet_name: str, selected_columns: List[str] = None):
        """设置选择"""
        # 确保文件在管理器中
        if file_path not in self.manager.get_all_files():
            success, error_msg, sheets = self.manager.add_excel_file(file_path)
            if not success:
                return False
            self._update_excel_list()
        
        # 设置Excel文件
        display_name = f"{os.path.basename(file_path)} ({file_path})"
        self.excel_var.set(display_name)
        
        # 设置Sheet
        self.sheet_var.set(sheet_name)
        
        # 设置选中的列
        if selected_columns:
            self.selected_columns = selected_columns.copy()
            self._update_selected_columns_display()
        
        return True
    
    def destroy(self):
        """销毁组件"""
        self.frame.destroy()


class MultiExcelSelector:
    """多Excel多Sheet选择器组合"""
    
    def __init__(self, parent, on_change: Callable = None):
        self.parent = parent
        self.on_change = on_change
        self.manager = MultiExcelManager()
        self.selectors = []
        
        # 创建主框架
        self.main_frame = ttk.Frame(parent)
        self.setup_ui()
        
        # 默认添加一个选择器
        self.add_selector()
    
    def setup_ui(self):
        """创建UI元素"""
        # 标题和按钮区域
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="📊 Excel文件和Sheet选择", font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT)
        
        # 添加按钮
        add_btn = ttk.Button(
            header_frame,
            text="➕ 添加",
            command=self.add_selector,
            width=10
        )
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 创建滚动容器
        scroll_container = ttk.Frame(self.main_frame)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建Canvas和Scrollbar用于主容器滚动
        self.main_canvas = tk.Canvas(scroll_container)
        self.main_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_main_frame = ttk.Frame(self.main_canvas)
        
        # 配置滚动
        self.scrollable_main_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.main_canvas.create_window((0, 0), window=self.scrollable_main_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        # 添加鼠标滚轮支持
        def _on_main_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.main_canvas.bind("<MouseWheel>", _on_main_mousewheel)
        self.scrollable_main_frame.bind("<MouseWheel>", _on_main_mousewheel)
        
        # 布局Canvas和Scrollbar
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_scrollbar.pack(side="right", fill="y")
        
        # 选择器容器（现在在可滚动框架内）
        self.selectors_frame = self.scrollable_main_frame
    
    def add_selector(self):
        """添加新的选择器"""
        # 创建分隔框架
        if self.selectors:
            separator = ttk.Separator(self.selectors_frame, orient='horizontal')
            separator.pack(fill=tk.X, pady=10)
        
        # 创建选择器
        selector = ExcelSheetSelector(
            self.selectors_frame,
            self.manager,
            on_change=self._on_selector_change,
            on_remove=self._remove_selector
        )
        selector.frame.pack(fill=tk.X, pady=5)
        
        self.selectors.append(selector)
        
        # 更新滚动区域
        self._update_scroll_region()
        
        if self.on_change:
            self.on_change()
    
    def _update_scroll_region(self):
        """更新滚动区域"""
        if hasattr(self, 'main_canvas'):
            self.main_canvas.update_idletasks()
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
    
    def _remove_selector(self, selector: ExcelSheetSelector):
        """删除选择器"""
        # 如果只有一个选择器，清空其内容而不是删除
        if len(self.selectors) <= 1:
            selector.excel_var.set("")
            selector.sheet_var.set("")
            selector.selected_columns.clear()
            selector._update_selected_columns_display()
            selector._update_excel_list()
            if self.on_change:
                self.on_change()
            return
        
        # 找到选择器的索引
        try:
            index = self.selectors.index(selector)
            
            # 获取选择器框架的所有相邻组件（包括分隔线）
            selector_frame = selector.frame
            all_children = list(self.selectors_frame.winfo_children())
            
            # 找到选择器框架在子组件中的位置
            try:
                frame_index = all_children.index(selector_frame)
                
                # 删除选择器框架
                selector.destroy()
                
                # 处理分隔线：如果不是第一个选择器，删除前面的分隔线
                # 如果是第一个选择器但不是最后一个，删除后面的分隔线
                if index > 0 and frame_index > 0:
                    # 删除前面的分隔线（通常在选择器前面）
                    prev_widget = all_children[frame_index - 1]
                    if isinstance(prev_widget, ttk.Separator):
                        prev_widget.destroy()
                elif index == 0 and len(self.selectors) > 1 and frame_index + 1 < len(all_children):
                    # 如果删除的是第一个选择器，删除后面的分隔线
                    next_widget = all_children[frame_index + 1]
                    if isinstance(next_widget, ttk.Separator):
                        next_widget.destroy()
                        
            except (ValueError, IndexError):
                # 如果找不到框架位置，只销毁选择器
                selector.destroy()
            
            # 从列表中移除
            self.selectors.remove(selector)
            
            # 更新滚动区域
            self._update_scroll_region()
            
            if self.on_change:
                self.on_change()
                
        except ValueError:
            pass
    

    
    def _on_selector_change(self):
        """选择器变化事件"""
        # 更新滚动区域以适应内容变化
        self._update_scroll_region()
        
        if self.on_change:
            self.on_change()
    
    def get_all_selections(self) -> List[Tuple[str, str, List[str]]]:
        """获取所有有效的选择
        
        返回:
            [(file_path, sheet_name, selected_columns), ...] 列表
        """
        selections = []
        for selector in self.selectors:
            selection = selector.get_selection()
            if selection:
                selections.append(selection)
        return selections
    
    def get_preview_data(self) -> str:
        """获取预览数据"""
        selections = self.get_all_selections()
        return self.manager.generate_combined_preview(selections)
    
    def get_export_data(self) -> dict:
        """获取导出数据"""
        selections = self.get_all_selections()
        return self.manager.export_selections_info(selections)
    
    def clear_all(self):
        """清除所有数据"""
        self.manager.clear_all()
        
        # 销毁所有选择器
        for selector in self.selectors:
            selector.destroy()
        self.selectors.clear()
        
        # 清除选择器容器中的所有组件（包括分隔线）
        for widget in self.selectors_frame.winfo_children():
            widget.destroy()
        
        # 重新添加一个空的选择器
        self.add_selector()
    
    def pack(self, **kwargs):
        """打包主框架"""
        self.main_frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """网格布局主框架"""
        self.main_frame.grid(**kwargs)