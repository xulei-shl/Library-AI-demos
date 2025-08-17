"""
第三步：Excel合并去重模块
选择多个excel文件，将其合并去重
去重规则：首先判断DOI重复，再判断"题名+作者+文献来源"
"""

import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import datetime

class ExcelMergerTab:
    """Excel合并去重Tab类"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.selected_files = []
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.parent_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding=10)
        file_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(file_frame, text="选择Excel文件", command=self.select_excel_files).pack(side='left')
        
        # 文件列表
        self.file_listbox = tk.Listbox(file_frame, height=6)
        self.file_listbox.pack(fill='x', pady=(10, 0))
        
        # 操作按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="开始合并去重", command=self.start_merge).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="清空列表", command=self.clear_files).pack(side='left')
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="处理结果", padding=10)
        result_frame.pack(fill='both', expand=True)
        
        self.result_text = tk.Text(result_frame, height=10, wrap='word')
        scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def select_excel_files(self):
        """
        选择多个Excel文件
        
        Returns:
            list: 选中的Excel文件路径列表
        """
        file_paths = filedialog.askopenfilenames(
            title="选择Excel文件",
            filetypes=[
                ("Excel文件", "*.xlsx *.xls"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_paths:
            # 添加到已选文件列表
            for file_path in file_paths:
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)
            
            # 更新界面显示
            self.update_file_list()
            self.log_message(f"已选择 {len(file_paths)} 个文件")
        
        return list(file_paths)
    
    def merge_excel_files(self, file_paths):
        """
        合并多个Excel文件
        
        Args:
            file_paths (list): Excel文件路径列表
            
        Returns:
            pd.DataFrame: 合并后的数据框
        """
        if not file_paths:
            return pd.DataFrame()
        
        all_dataframes = []
        
        for i, file_path in enumerate(file_paths):
            try:
                self.log_message(f"正在读取: {os.path.basename(file_path)}")
                
                # 读取文件，支持Excel和HTML格式
                df = None
                
                # 首先检查文件是否为HTML格式（CNKI导出的特殊情况）
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.read(100).lower()
                        if 'html' in first_line or '<table' in first_line:
                            # 这是HTML格式的表格文件
                            df = pd.read_html(file_path, encoding='utf-8')[0]  # 取第一个表格
                            self.log_message(f"  检测到HTML格式，使用 read_html 读取成功")
                        else:
                            raise ValueError("不是HTML格式")
                except:
                    # 不是HTML格式，按Excel文件处理
                    if file_path.endswith('.xlsx'):
                        # .xlsx文件使用openpyxl引擎
                        df = pd.read_excel(file_path, engine='openpyxl')
                        self.log_message(f"  使用 openpyxl 引擎读取成功")
                    elif file_path.endswith('.xls'):
                        # .xls文件使用xlrd引擎
                        try:
                            df = pd.read_excel(file_path, engine='xlrd')
                            self.log_message(f"  使用 xlrd 引擎读取成功")
                        except Exception as e:
                            # 如果xlrd失败，尝试openpyxl（某些.xls文件实际上是.xlsx格式）
                            try:
                                df = pd.read_excel(file_path, engine='openpyxl')
                                self.log_message(f"  使用 openpyxl 引擎读取成功")
                            except:
                                raise e
                    else:
                        # 其他格式，先尝试openpyxl，再尝试xlrd
                        try:
                            df = pd.read_excel(file_path, engine='openpyxl')
                            self.log_message(f"  使用 openpyxl 引擎读取成功")
                        except:
                            df = pd.read_excel(file_path, engine='xlrd')
                            self.log_message(f"  使用 xlrd 引擎读取成功")
                
                if not df.empty:
                    # 如果列名是默认的数字索引，说明表头在第一行数据里
                    if all(isinstance(c, int) for c in df.columns) and len(df) > 0:
                        self.log_message(f"  检测到数字列名，将第一行提升为表头")
                        df.columns = df.iloc[0]
                        df = df.drop(df.index[0]).reset_index(drop=True)

                    # 添加来源文件信息
                    df['_source_file'] = os.path.basename(file_path)
                    all_dataframes.append(df)
                    self.log_message(f"  读取成功，共 {len(df)} 条记录")
                else:
                    self.log_message(f"  文件为空")
                    
            except Exception as e:
                self.log_message(f"  读取失败: {str(e)}")
                continue
        
        if not all_dataframes:
            self.log_message("没有成功读取任何文件")
            return pd.DataFrame()
        
        # 合并所有数据框，确保不产生数字索引表头
        merged_df = pd.concat(all_dataframes, ignore_index=True, sort=False)
        self.log_message(f"合并完成，总计 {len(merged_df)} 条记录")
        
        return merged_df
    
    def remove_duplicates(self, df):
        """
        去重处理
        1. 首先基于DOI去重
        2. 再基于"题名+作者+文献来源"去重
        
        Args:
            df (pd.DataFrame): 待去重的数据框
            
        Returns:
            pd.DataFrame: 去重后的数据框
        """
        if df.empty:
            return df
        
        # 检查并删除数字表头行
        if len(df) > 0:
            # 检查第一行是否是数字索引（0,1,2...）
            first_row = df.iloc[0]
            if first_row.astype(str).str.isdigit().all():
                self.log_message("检测到数字表头行，直接删除")
                df = df.drop(df.index[0]).reset_index(drop=True)
        
        original_count = len(df)
        self.log_message(f"原始记录数: {original_count}")
        
        # 动态查找列名（支持不同的列名格式）
        title_col = None
        author_col = None
        source_col = None
        doi_col = None
        
        # 查找题名列 - 支持 "Title-题名" 格式
        for col in df.columns:
            col_str = str(col).lower()
            if '题名' in str(col) or 'title' in col_str or 'Title-题名' in col_str:
                title_col = col
                break
        
        # 查找作者列 - 支持 "Author-作者" 格式
        for col in df.columns:
            col_str = str(col).lower()
            if '作者' in str(col) or 'author' in col_str or 'Author-作者' in col_str:
                author_col = col
                break
        
        # 查找来源列 - 支持 "Source-文献来源" 格式
        for col in df.columns:
            col_str = str(col).lower()
            if ('来源' in str(col) or '文献来源' in str(col) or 
                'source' in col_str or 'Source-文献来源' in col_str):
                source_col = col
                break
        
        # 查找DOI列 - 支持 "DOI-DOI" 格式
        for col in df.columns:
            col_str = str(col).lower()
            if 'doi' in col_str or 'DOI-DOI' in col_str:
                doi_col = col
                break
        
        # 检查必要列是否存在
        missing_info = []
        if not title_col:
            missing_info.append("题名列")
        if not author_col:
            missing_info.append("作者列")
        if not source_col:
            missing_info.append("来源列")
        if not doi_col:
            missing_info.append("DOI列")
        
        if missing_info:
            self.log_message(f"警告：未找到 {', '.join(missing_info)}，将跳过相关去重")
            return df
        
        self.log_message(f"使用列进行去重: 题名={title_col}, 作者={author_col}, 来源={source_col}, DOI={doi_col}")
        
        # 第一步：基于DOI去重（保留非空DOI的第一条记录）
        df_with_doi = df[df[doi_col].notna() & (df[doi_col].astype(str).str.strip() != '') & (df[doi_col].astype(str).str.strip() != 'nan')]
        df_without_doi = df[df[doi_col].isna() | (df[doi_col].astype(str).str.strip() == '') | (df[doi_col].astype(str).str.strip() == 'nan')]
        
        self.log_message(f"有DOI的记录: {len(df_with_doi)} 条")
        self.log_message(f"无DOI的记录: {len(df_without_doi)} 条")
        
        if not df_with_doi.empty:
            # 清理DOI列，去除空格和特殊字符
            df_with_doi = df_with_doi.copy()
            df_with_doi[doi_col] = df_with_doi[doi_col].astype(str).str.strip().str.lower()
            
            # 对有DOI的记录按DOI去重，保留第一条
            before_doi_dedup = len(df_with_doi)
            df_with_doi_dedup = df_with_doi.drop_duplicates(subset=[doi_col], keep='first')
            after_doi_dedup = len(df_with_doi_dedup)
            self.log_message(f"DOI去重：{before_doi_dedup} -> {after_doi_dedup}，去除 {before_doi_dedup - after_doi_dedup} 条重复")
        else:
            df_with_doi_dedup = df_with_doi
            self.log_message("没有DOI记录需要去重")
        
        # 第二步：对无DOI的记录基于"题名+作者+文献来源"去重
        if not df_without_doi.empty:
            df_without_doi = df_without_doi.copy()
            
            # 创建组合键用于去重，清理数据
            df_without_doi['_temp_key'] = (
                df_without_doi[title_col].fillna('').astype(str).str.strip().str.lower() + '|' +
                df_without_doi[author_col].fillna('').astype(str).str.strip().str.lower() + '|' +
                df_without_doi[source_col].fillna('').astype(str).str.strip().str.lower()
            )
            
            # 基于组合键去重
            before_title_dedup = len(df_without_doi)
            df_without_doi_dedup = df_without_doi.drop_duplicates(subset=['_temp_key'], keep='first')
            after_title_dedup = len(df_without_doi_dedup)
            
            # 删除临时列
            df_without_doi_dedup = df_without_doi_dedup.drop(columns=['_temp_key'])
            
            self.log_message(f"题名+作者+来源去重：{before_title_dedup} -> {after_title_dedup}，去除 {before_title_dedup - after_title_dedup} 条重复")
        else:
            df_without_doi_dedup = df_without_doi
            self.log_message("没有无DOI记录需要去重")
        
        # 合并去重后的结果
        if not df_with_doi_dedup.empty and not df_without_doi_dedup.empty:
            df_final = pd.concat([df_with_doi_dedup, df_without_doi_dedup], ignore_index=True)
        elif not df_with_doi_dedup.empty:
            df_final = df_with_doi_dedup
        elif not df_without_doi_dedup.empty:
            df_final = df_without_doi_dedup
        else:
            df_final = pd.DataFrame()
        
        final_count = len(df_final)
        removed_count = original_count - final_count
        self.log_message(f"总去重效果：{original_count} -> {final_count}，去除 {removed_count} 条重复记录")
        
        return df_final.reset_index(drop=True)
    
    def save_merged_file(self, df, output_path):
        """
        保存合并后的Excel文件
        
        Args:
            df (pd.DataFrame): 合并去重后的数据框
            output_path (str): 输出文件路径
        """
        try:
            # 移除临时的来源文件列（如果存在）
            if '_source_file' in df.columns:
                df_to_save = df.drop(columns=['_source_file'])
            else:
                df_to_save = df.copy()
            
            # 确保不会产生数字索引表头，使用index=False
            # 同时确保列名正确保存
            self.log_message(f"准备保存 {len(df_to_save)} 条记录，{len(df_to_save.columns)} 列")
            self.log_message(f"列名: {list(df_to_save.columns)}")
            
            # 保存为Excel文件，不包含行索引
            df_to_save.to_excel(output_path, index=False, engine='openpyxl', header=True)
            self.log_message(f"文件已保存: {output_path}")
            return True
            
        except Exception as e:
            self.log_message(f"保存文件失败: {str(e)}")
            return False
    
    def get_duplicate_stats(self, original_count, final_count):
        """
        获取去重统计信息
        
        Args:
            original_count (int): 原始记录数
            final_count (int): 去重后记录数
            
        Returns:
            dict: 统计信息
        """
        removed_count = original_count - final_count
        removal_rate = (removed_count / original_count * 100) if original_count > 0 else 0
        
        return {
            'original_count': original_count,
            'final_count': final_count,
            'removed_count': removed_count,
            'removal_rate': round(removal_rate, 2)
        }
    
    def update_file_list(self):
        """更新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(file_path))
    
    def clear_files(self):
        """清空文件列表"""
        self.selected_files.clear()
        self.update_file_list()
        self.log_message("已清空文件列表")
    
    def log_message(self, message):
        """在结果区域显示消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        if hasattr(self, 'result_text'):
            self.result_text.insert(tk.END, formatted_message)
            self.result_text.see(tk.END)
        else:
            print(formatted_message.strip())
    
    def start_merge(self):
        """开始合并去重处理"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择Excel文件")
            return
        
        try:
            # 选择输出文件路径
            output_path = filedialog.asksaveasfilename(
                title="保存合并后的文件",
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
            )
            
            if not output_path:
                return
            
            self.log_message("开始处理...")
            self.log_message(f"共选择 {len(self.selected_files)} 个文件")
            
            # 合并文件
            merged_df = self.merge_excel_files(self.selected_files)
            
            if merged_df.empty:
                self.log_message("合并结果为空，处理终止")
                return
            
            # 去重处理
            self.log_message("开始去重处理...")
            original_count = len(merged_df)
            deduped_df = self.remove_duplicates(merged_df)
            
            # 获取统计信息
            stats = self.get_duplicate_stats(original_count, len(deduped_df))
            
            # 保存文件
            if self.save_merged_file(deduped_df, output_path):
                self.log_message("=" * 50)
                self.log_message("处理完成！")
                self.log_message(f"原始记录数: {stats['original_count']}")
                self.log_message(f"去重后记录数: {stats['final_count']}")
                self.log_message(f"去除重复记录: {stats['removed_count']} 条")
                self.log_message(f"去重率: {stats['removal_rate']}%")
                self.log_message("=" * 50)
                
                messagebox.showinfo("成功", f"处理完成！\n去重前: {stats['original_count']} 条\n去重后: {stats['final_count']} 条")
            
        except Exception as e:
            error_msg = f"处理过程中出现错误: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("错误", error_msg)

if __name__ == "__main__":
    # 测试代码
    root = tk.Tk()
    root.title("Excel合并去重测试")
    
    tab = ExcelMergerTab(root)
    
    root.mainloop()