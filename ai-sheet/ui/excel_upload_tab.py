#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel上传Tab模块
提供Excel文件上传、解析和预览功能
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 导入共享模块
from modules.excel_utils import (
    validate_excel_file, parse_excel_data, 
    generate_markdown_preview, get_excel_config,
    format_file_size
)
from modules.data_validator import DataValidator
from .markdown_text import MarkdownText


class ExcelUploadTab:
    """Excel上传Tab主类"""
    
    def __init__(self, parent, shared_data=None):
        self.parent = parent
        self.shared_data = shared_data or {}
        self.validator = DataValidator()
        self.excel_data = None
        self.file_path = None
        
        # 获取Excel配置
        self.config = get_excel_config()
        
        # 创建界面
        self.setup_ui()
    
    def setup_ui(self):
        """创建界面元素"""
        # 创建主框架
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 上传区域
        upload_frame = ttk.LabelFrame(main_frame, text="📤 Excel文件上传", padding=15)
        upload_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 文件选择按钮和路径显示
        file_frame = ttk.Frame(upload_frame)
        file_frame.pack(fill=tk.X)
        
        self.upload_btn = ttk.Button(
            file_frame, 
            text="选择Excel文件", 
            command=self.select_file
        )
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_path_var = tk.StringVar()
        file_path_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=50)
        file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 文件信息显示区域
        self.info_frame = ttk.Frame(upload_frame)
        self.info_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 初始状态隐藏信息区域
        self.info_frame.pack_forget()
        
        # 文件信息标签
        self.file_info_var = tk.StringVar(value="未选择文件")
        self.file_info_label = ttk.Label(self.info_frame, textvariable=self.file_info_var)
        self.file_info_label.pack(anchor=tk.W)
        
        # 数据预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="👁️ 数据预览", padding=15)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Markdown预览文本框
        self.preview_text = MarkdownText(
            preview_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 10),
            height=20
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # 初始提示信息
        self.preview_text.set_markdown_content("*请选择Excel文件以查看数据预览*")
        
        # 底部按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(
            button_frame, 
            text="🔄 刷新数据", 
            command=self.refresh_data,
            state=tk.DISABLED
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清除按钮
        self.clear_btn = ttk.Button(
            button_frame, 
            text="🗑️ 清除数据", 
            command=self.clear_data,
            state=tk.DISABLED
        )
        self.clear_btn.pack(side=tk.LEFT)
    
    def select_file(self):
        """选择Excel文件"""
        # 获取支持的文件格式
        formats = self.config['supported_formats']
        file_types = [("Excel文件", " ".join([f"*{fmt}" for fmt in formats])), ("所有文件", "*.*")]
        
        # 打开文件选择对话框
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=file_types
        )
        
        if not file_path:
            return
        
        # 验证文件
        is_valid, error_msg = validate_excel_file(file_path)
        if not is_valid:
            messagebox.showerror("文件错误", error_msg)
            return
        
        # 保存文件路径
        self.file_path = file_path
        self.file_path_var.set(file_path)
        
        # 将文件路径写入共享数据，供其他Tab使用
        if self.shared_data is not None:
            self.shared_data['excel_path'] = file_path
        
        # 将文件路径保存到临时文件，供其他Tab使用
        self._save_excel_path_to_temp_file(file_path)
        
        # 清理旧的临时文件（如果存在）
        self._remove_temp_file()
        
        # 解析数据
        try:
            self.excel_data = parse_excel_data(file_path)
            
            # 更新文件信息
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            total_rows = self.excel_data['total_rows']
            truncated = self.excel_data['truncated']
            columns = len(self.excel_data['column_names'])
            
            # 构建信息文本
            info_text = f"文件名：{file_name}\n"
            info_text += f"大小：{format_file_size(file_size)}\n"
            info_text += f"总行数：{total_rows}" + (f" (已截取前{self.config['max_rows']}行)" if truncated else "") + "\n"
            info_text += f"列数：{columns}\n"
            info_text += f"上传时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            self.file_info_var.set(info_text)
            
            # 显示信息区域
            self.info_frame.pack(fill=tk.X, pady=(15, 0))
            
            # 更新预览
            self.preview_text.set_markdown_content(self.excel_data['preview'])
            
            # 保存样本数据到临时文件
            self._save_sample_data_to_temp_file()
            
            # 启用按钮
            self.refresh_btn.config(state=tk.NORMAL)
            self.clear_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("解析错误", f"解析Excel文件时出错：{str(e)}")
    
    def refresh_data(self):
        """刷新数据"""
        if self.file_path:
            # 清理旧的临时文件
            self._remove_temp_file()
            # 重新选择并解析文件
            current_path = self.file_path
            self.file_path_var.set(current_path)
            
            # 验证文件
            is_valid, error_msg = validate_excel_file(current_path)
            if not is_valid:
                messagebox.showerror("文件错误", error_msg)
                return
            
            # 重新解析数据
            try:
                self.excel_data = parse_excel_data(current_path)
                
                # 更新文件信息
                file_size = os.path.getsize(current_path)
                file_name = os.path.basename(current_path)
                total_rows = self.excel_data['total_rows']
                truncated = self.excel_data['truncated']
                columns = len(self.excel_data['column_names'])
                
                # 构建信息文本
                info_text = f"文件名：{file_name}\n"
                info_text += f"大小：{format_file_size(file_size)}\n"
                info_text += f"总行数：{total_rows}" + (f" (已截取前{self.config['max_rows']}行)" if truncated else "") + "\n"
                info_text += f"列数：{columns}\n"
                info_text += f"刷新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.file_info_var.set(info_text)
                
                # 显示信息区域
                self.info_frame.pack(fill=tk.X, pady=(15, 0))
                
                # 更新预览
                self.preview_text.set_markdown_content(self.excel_data['preview'])
                
                # 更新共享数据中的文件路径
                if self.shared_data is not None:
                    self.shared_data['excel_path'] = current_path
                
                # 将文件路径保存到临时文件，供其他Tab使用
                self._save_excel_path_to_temp_file(current_path)
                
                # 保存样本数据到临时文件
                self._save_sample_data_to_temp_file()
                
                # 启用按钮
                self.refresh_btn.config(state=tk.NORMAL)
                self.clear_btn.config(state=tk.NORMAL)
                
            except Exception as e:
                messagebox.showerror("解析错误", f"刷新Excel文件时出错：{str(e)}")
    
    def clear_data(self):
        """清除数据"""
        self.file_path = None
        self.excel_data = None
        self.file_path_var.set("")
        self.file_info_var.set("未选择文件")
        self.preview_text.set_markdown_content("*请选择Excel文件以查看数据预览*")
        
        # 清除共享数据中的文件路径
        if self.shared_data is not None and 'excel_path' in self.shared_data:
            del self.shared_data['excel_path']
        
        # 删除临时文件
        self._remove_temp_file()
        
        # 删除路径临时文件
        self._remove_excel_path_temp_file()
        
        # 隐藏信息区域
        self.info_frame.pack_forget()
        
        # 禁用按钮
        self.refresh_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.DISABLED)
    
    def get_excel_data(self):
        """获取Excel数据，供其他模块使用"""
        return self.excel_data
    
    def get_column_list(self):
        """获取列列表，供公式生成模块使用"""
        if not self.excel_data:
            return []
        
        try:
            # 返回格式化的列信息：A列-列名
            columns = []
            column_names = self.excel_data.get('column_names', [])
            
            for i, col_name in enumerate(column_names):
                # 将索引转换为Excel列标识（A, B, C...）
                col_letter = self._index_to_column_letter(i)
                columns.append(f"{col_letter}列-{col_name}")
            
            return columns
        except Exception as e:
            print(f"获取列列表失败：{e}")
            return []
    
    def get_sample_data(self):
        """获取样本数据（前5行），供公式生成模块使用"""
        if not self.excel_data:
            return ""
        
        try:
            # 首先尝试从临时文件读取
            temp_file_path = os.path.join("logs", "excel_sample_data.md")
            if os.path.exists(temp_file_path):
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            # 如果临时文件不存在，从内存数据生成
            df = self.excel_data.get('data')  # 修正：使用'data'而不是'dataframe'
            if df is None or df.empty:
                return ""
            
            # 获取前5行数据
            sample_df = df.head(5)
            
            # 转换为Markdown格式
            markdown_data = sample_df.to_markdown(index=False)
            
            return markdown_data
        except Exception as e:
            print(f"获取样本数据失败：{e}")
            return ""
    
    def _save_sample_data_to_temp_file(self):
        """将样本数据保存到临时文件"""
        try:
            # 确保logs目录存在
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # 获取DataFrame数据
            df = self.excel_data.get('data')
            if df is None or df.empty:
                return
            
            # 获取5行数据
            sample_df = df.head(5)
            
            # 转换为Markdown格式
            markdown_data = sample_df.to_markdown(index=False)
            
            # 保存到临时文件
            temp_file_path = os.path.join(logs_dir, "excel_sample_data.md")
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_data)
            
            print(f"样本数据已保存到: {temp_file_path}")
            
        except Exception as e:
            print(f"保存样本数据到临时文件失败：{e}")
    
    def _save_excel_path_to_temp_file(self, file_path):
        """将Excel文件路径保存到临时文件"""
        try:
            # 确保logs目录存在
            logs_dir = "logs"
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # 保存路径到临时文件
            path_file = os.path.join(logs_dir, "excel_path.txt")
            with open(path_file, 'w', encoding='utf-8') as f:
                f.write(file_path)
            
            print(f"Excel路径已保存到: {path_file}")
            
        except Exception as e:
            print(f"保存Excel路径到临时文件失败：{e}")
    
    def _remove_excel_path_temp_file(self):
        """删除Excel路径临时文件"""
        try:
            path_file = os.path.join("logs", "excel_path.txt")
            if os.path.exists(path_file):
                os.remove(path_file)
                print(f"Excel路径临时文件已删除: {path_file}")
        except Exception as e:
            print(f"删除Excel路径临时文件失败：{e}")
    
    def _remove_temp_file(self):
        """删除临时文件"""
        try:
            temp_file_path = os.path.join("logs", "excel_sample_data.md")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"临时文件已删除: {temp_file_path}")
        except Exception as e:
            print(f"删除临时文件失败：{e}")
    
    def _index_to_column_letter(self, index):
        """将数字索引转换为Excel列字母"""
        result = ""
        while index >= 0:
            result = chr(index % 26 + ord('A')) + result
            index = index // 26 - 1
        return result