#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多Excel多Sheet上传Tab模块
提供多Excel文件上传、Sheet选择和预览功能
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入共享模块
from modules.multi_excel_utils import (
    MultiExcelManager, save_multi_excel_data_to_temp, 
    clear_multi_excel_temp_files, get_save_status_info
)
from .multi_excel_selector import MultiExcelSelector
from .markdown_text import MarkdownText


class MultiExcelTab:
    """多Excel多Sheet上传Tab主类"""
    
    def __init__(self, parent, shared_data=None):
        self.parent = parent
        self.shared_data = shared_data or {}
        self.manager = MultiExcelManager()
        
        # 预先初始化关键属性
        self.excel_selector = None
        self.preview_text = None
        self.info_var = None
        self.refresh_btn = None
        self.clear_btn = None
        
        # 保存状态提醒相关属性
        self.status_reminder_frame = None
        self.status_reminder_label = None
        self.status_message_label = None
        self.status_button = None
        
        # 创建界面
        try:
            self.setup_ui()
        except Exception as e:
            print(f"❌ MultiExcelTab初始化失败: {e}")
            import traceback
            traceback.print_exc()
            # 确保基本属性存在，避免后续访问错误
            if self.excel_selector is None:
                self.excel_selector = None
            if self.info_var is None:
                import tkinter as tk
                self.info_var = tk.StringVar(value="初始化失败，请重试")
    
    def setup_ui(self):
        """创建界面元素"""
        # 创建主框架
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建PanedWindow用于分割选择区域和预览区域
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：选择区域 - 增加权重以提供更宽的操作空间
        left_frame = ttk.LabelFrame(paned_window, text="📊 多Excel文件选择", padding=10)
        paned_window.add(left_frame, weight=3)
        
        # 创建多Excel选择器
        try:
            self.excel_selector = MultiExcelSelector(
                left_frame, 
                on_change=self._on_selection_change
            )
            self.excel_selector.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            print(f"❌ 创建MultiExcelSelector失败: {e}")
            import traceback
            traceback.print_exc()
            # 创建错误提示标签
            error_label = ttk.Label(left_frame, text=f"组件初始化失败: {str(e)}", foreground="red")
            error_label.pack(pady=20)
            self.excel_selector = None
        
        # 底部按钮区域
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(
            button_frame, 
            text="🔄 刷新预览", 
            command=self.refresh_preview
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清除按钮
        self.clear_btn = ttk.Button(
            button_frame, 
            text="🗑️ 清除所有", 
            command=self.clear_all
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 移除重复的导出按钮，使用状态提醒区域的动态按钮
        
        # 保存状态提醒区域（在左侧底部）
        self._create_status_reminder(left_frame)
        
        # 右侧：预览区域
        right_frame = ttk.LabelFrame(paned_window, text="👁️ 数据预览", padding=10)
        paned_window.add(right_frame, weight=1)
        
        # 预览信息区域
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.info_var = tk.StringVar(value="请选择Excel文件和Sheet以查看预览")
        info_label = ttk.Label(info_frame, textvariable=self.info_var, font=("微软雅黑", 10, "bold"))
        info_label.pack(anchor=tk.W)
        
        # 创建Markdown预览文本框
        self.preview_text = MarkdownText(
            right_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            height=25
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # 初始提示信息
        self.preview_text.set_markdown_content("*请选择Excel文件和Sheet以查看数据预览*")
        
        # 设置PanedWindow初始分割比例 - 增加左侧宽度以确保按钮不被遮挡
        # 使用700像素确保在1920x1080分辨率下有足够的操作空间
        self.root.after(100, lambda: paned_window.sashpos(0, 950))
    
    def _create_status_reminder(self, parent):
        """创建保存状态提醒区域"""
        # 创建提醒框架
        self.status_reminder_frame = ttk.Frame(parent)
        self.status_reminder_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 创建提醒标签（标题）
        self.status_reminder_label = ttk.Label(
            self.status_reminder_frame,
            text="请选择Excel文件和Sheet",
            font=("微软雅黑", 10, "bold"),
            foreground="#666666"
        )
        self.status_reminder_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 创建消息标签（详细信息）
        self.status_message_label = ttk.Label(
            self.status_reminder_frame,
            text="上传Excel文件并选择需要的Sheet",
            font=("微软雅黑", 9),
            foreground="#888888"
        )
        self.status_message_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 创建状态按钮（动态按钮）
        self.status_button = ttk.Button(
            self.status_reminder_frame,
            text="保存选择",
            command=self.save_selections,
            state="disabled"
        )
        self.status_button.pack(anchor=tk.W)
        
        # 初始化状态
        self._update_status_reminder()
    
    def _update_status_reminder(self):
        """更新保存状态提醒显示"""
        try:
            if not self.status_reminder_frame:
                return
            
            # 获取当前选择
            current_selections = []
            if self.excel_selector:
                current_selections = self.excel_selector.get_all_selections()
            
            # 获取保存状态信息
            status_info = get_save_status_info(current_selections)
            
            # 更新提醒标题
            if self.status_reminder_label:
                self.status_reminder_label.config(text=status_info['reminder_title'])
                
                # 根据提醒类型设置颜色
                if status_info['reminder_type'] == 'warning':
                    self.status_reminder_label.config(foreground="#d63384")  # 警告红色
                elif status_info['reminder_type'] == 'success':
                    self.status_reminder_label.config(foreground="#198754")  # 成功绿色
                else:
                    self.status_reminder_label.config(foreground="#666666")  # 默认灰色
            
            # 更新消息内容
            if self.status_message_label:
                self.status_message_label.config(text=status_info['reminder_message'])
                
                # 根据提醒类型设置消息颜色
                if status_info['reminder_type'] == 'warning':
                    self.status_message_label.config(foreground="#dc3545")
                elif status_info['reminder_type'] == 'success':
                    self.status_message_label.config(foreground="#20c997")
                else:
                    self.status_message_label.config(foreground="#888888")
            
            # 更新按钮
            if self.status_button:
                self.status_button.config(text=status_info['button_text'])
                
                # 根据按钮样式设置状态
                if status_info['button_style'] == 'disabled':
                    self.status_button.config(state="disabled")
                else:
                    self.status_button.config(state="normal")
            
            # 如果需要显示醒目提醒，添加背景色
            if status_info['show_reminder']:
                if status_info['reminder_type'] == 'warning':
                    # 警告样式：浅黄色背景
                    self.status_reminder_frame.config(style="Warning.TFrame")
                    self._configure_warning_style()
                else:
                    # 移除特殊样式
                    self.status_reminder_frame.config(style="TFrame")
            else:
                # 移除特殊样式
                self.status_reminder_frame.config(style="TFrame")
                
        except Exception as e:
            print(f"更新保存状态提醒失败：{e}")
    
    def _configure_warning_style(self):
        """配置警告样式"""
        try:
            style = ttk.Style()
            style.configure("Warning.TFrame", background="#fff3cd", relief="solid", borderwidth=1)
        except Exception as e:
            print(f"配置警告样式失败：{e}")
    
    @property
    def root(self):
        """获取根窗口"""
        widget = self.parent
        while widget.master:
            widget = widget.master
        return widget
    
    def _on_selection_change(self):
        """选择变化事件处理"""
        if self.excel_selector is not None:
            self.update_preview()
            # 实时更新保存状态提醒
            self._update_status_reminder()
        else:
            print("❌ excel_selector未初始化，无法处理选择变化事件")
    
    def update_preview(self):
        """更新预览"""
        try:
            # 检查关键组件是否存在
            if self.excel_selector is None:
                if self.info_var:
                    self.info_var.set("组件未正确初始化")
                if self.preview_text:
                    self.preview_text.set_markdown_content("*组件初始化失败，请重启应用*")
                return
            
            # 获取所有选择
            selections = self.excel_selector.get_all_selections()
            
            if not selections:
                if self.info_var:
                    self.info_var.set("请选择Excel文件和Sheet以查看预览")
                if self.preview_text:
                    self.preview_text.set_markdown_content("*请选择Excel文件和Sheet以查看数据预览*")
                return
            
            # 更新信息
            total_files = len(set(file_path for file_path, _, _ in selections))
            total_sheets = len(selections)
            if self.info_var:
                self.info_var.set(f"已选择 {total_files} 个文件，{total_sheets} 个Sheet")
            
            # 生成预览
            preview_content = self.excel_selector.get_preview_data()
            if self.preview_text:
                self.preview_text.set_markdown_content(preview_content)
            
            # 更新共享数据
            self._update_shared_data(selections)
            
        except Exception as e:
            print(f"❌ 更新预览失败: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("预览错误", f"更新预览时出错：{str(e)}")
    
    def refresh_preview(self):
        """刷新预览"""
        self.update_preview()
    
    def clear_all(self):
        """清除所有数据"""
        if messagebox.askyesno("确认清除", "确定要清除所有选择的Excel文件和Sheet吗？"):
            if self.excel_selector is not None:
                self.excel_selector.clear_all()
            else:
                print("❌ excel_selector未初始化，无法清除数据")
            
            if self.info_var is not None:
                self.info_var.set("请选择Excel文件和Sheet以查看预览")
            
            if self.preview_text is not None:
                self.preview_text.set_markdown_content("*请选择Excel文件和Sheet以查看数据预览*")
            
            # 清除共享数据
            if 'multi_excel_data' in self.shared_data:
                del self.shared_data['multi_excel_data']
            
            # 清除临时文件
            clear_multi_excel_temp_files()
            
            # 更新保存状态提醒
            self._update_status_reminder()
    
    def save_selections(self):
        """保存选择到临时文件"""
        try:
            if self.excel_selector is None:
                messagebox.showwarning("提示", "组件未正确初始化，无法保存选择")
                return
            
            selections = self.excel_selector.get_all_selections()
            
            if not selections:
                messagebox.showwarning("提示", "请先选择Excel文件和Sheet")
                return
            
            # 保存到临时文件
            success = save_multi_excel_data_to_temp(self.manager, selections)
            
            if success:
                messagebox.showinfo("保存成功", "选择的Excel数据已保存，可在其他Tab中使用")
                # 更新保存状态提醒
                self._update_status_reminder()
            else:
                messagebox.showerror("保存失败", "保存Excel数据时出错")
                
        except Exception as e:
            messagebox.showerror("保存错误", f"保存选择时出错：{str(e)}")
    
    def _update_shared_data(self, selections):
        """更新共享数据"""
        try:
            if self.excel_selector is None:
                print("❌ excel_selector未初始化，无法更新共享数据")
                return
            
            # 获取导出数据
            export_data = self.excel_selector.get_export_data()
            
            # 更新共享数据
            self.shared_data['multi_excel_data'] = {
                'selections': selections,
                'export_data': export_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"更新共享数据失败：{e}")
    
    def get_all_selections(self):
        """获取所有选择，供其他模块使用"""
        if self.excel_selector is not None:
            return self.excel_selector.get_all_selections()
        else:
            print("❌ excel_selector未初始化，返回空列表")
            return []
    
    def get_export_data(self):
        """获取导出数据，供其他模块使用"""
        if self.excel_selector is not None:
            return self.excel_selector.get_export_data()
        else:
            print("❌ excel_selector未初始化，返回空字典")
            return {}
    
    def get_combined_preview(self):
        """获取组合预览，供其他模块使用"""
        if self.excel_selector is not None:
            return self.excel_selector.get_preview_data()
        else:
            print("❌ excel_selector未初始化，返回默认提示")
            return "*组件未正确初始化*"
    
    def get_column_list(self):
        """获取所有选择的列列表，供公式生成模块使用"""
        try:
            selections = self.get_all_selections()
            if not selections:
                return []
            
            all_columns = []
            for file_path, sheet_name, selected_columns in selections:
                try:
                    sheet_data = self.manager.get_sheet_data(file_path, sheet_name)
                    file_name = os.path.basename(file_path)
                    
                    # 为每列添加文件和Sheet信息
                    for col in sheet_data['columns']:
                        formatted_col = f"[{file_name}-{sheet_name}] {col}"
                        all_columns.append(formatted_col)
                        
                except Exception as e:
                    print(f"获取列信息失败 {file_path}-{sheet_name}: {e}")
                    continue
            
            return all_columns
            
        except Exception as e:
            print(f"获取列列表失败：{e}")
            return []
    
    def get_sample_data(self):
        """获取样本数据，供公式生成模块使用"""
        try:
            # 首先尝试从临时文件读取
            import os
            temp_file_path = os.path.join("logs", "multi_excel_preview.md")
            if os.path.exists(temp_file_path):
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # 如果临时文件不存在，生成当前预览
            return self.get_combined_preview()
            
        except Exception as e:
            print(f"获取样本数据失败：{e}")
            return ""