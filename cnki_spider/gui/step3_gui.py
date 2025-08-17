import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
from datetime import datetime
import sys

# 添加父目录到路径以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from step3_excel_merger import ExcelMergerTab
    MERGER_AVAILABLE = True
except ImportError as e:
    print(f"导入Excel合并器失败: {e}")
    MERGER_AVAILABLE = False

class Step3GUI:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.selected_files = []
        self.setup_ui()
        
    def setup_ui(self):
        """设置Excel合并去重界面"""
        # 创建主容器，使用左右分布
        main_container = ttk.Frame(self.parent_frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 左侧内容区域
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # 右侧日志区域
        right_frame = ttk.Frame(main_container, width=400)
        right_frame.pack(side='right', fill='both', padx=(10, 0))
        right_frame.pack_propagate(False)
        
        # === 左侧内容 ===
        # 标题
        ttk.Label(left_frame, text="📊 Excel合并去重", 
                 font=('Microsoft YaHei UI', 18, 'bold'),
                 foreground='#2c3e50').pack(anchor='w', pady=(0, 20))
        
        # 功能说明
        ttk.Label(left_frame, text="选择多个Excel文件进行合并和去重处理", 
                 font=('Microsoft YaHei UI', 10, 'bold'),
                 foreground='#34495e').pack(anchor='w', pady=(0, 10))
        
        # 功能列表
        features_text = """• 选择多个Excel文件（CNKI爬取结果）
• 自动基于DOI进行去重
• 自动基于'题名+作者+文献来源'进行二次去重
• 生成合并后的Excel文件"""
        
        ttk.Label(left_frame, text=features_text, 
                 font=('Microsoft YaHei UI', 9),
                 foreground='#7f8c8d').pack(anchor='w', pady=(0, 20))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(left_frame, text="文件选择", padding=15)
        file_frame.pack(fill='x', pady=(0, 20))
        
        # 文件列表
        self.file_listbox = tk.Listbox(file_frame, height=6, selectmode=tk.MULTIPLE)
        self.file_listbox.pack(fill='x', pady=(0, 10))
        
        # 文件操作按钮
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill='x')
        
        ttk.Button(btn_frame, text="📁 添加文件", 
                  command=self.add_files).pack(side='left', padx=(0, 10))
        ttk.Button(btn_frame, text="🗑️ 移除选中", 
                  command=self.remove_files).pack(side='left', padx=(0, 10))
        ttk.Button(btn_frame, text="🧹 清空列表", 
                  command=self.clear_files).pack(side='left')
        
        # 输出设置
        output_frame = ttk.LabelFrame(left_frame, text="输出设置", padding=15)
        output_frame.pack(fill='x', pady=(0, 20))
        
        # 输出文件名
        name_frame = ttk.Frame(output_frame)
        name_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(name_frame, text="输出文件名:").pack(side='left')
        self.output_name_var = tk.StringVar(value="合并结果.xlsx")
        ttk.Entry(name_frame, textvariable=self.output_name_var).pack(side='left', fill='x', expand=True, padx=(10, 0))
        
        # 输出目录
        dir_frame = ttk.Frame(output_frame)
        dir_frame.pack(fill='x')
        ttk.Label(dir_frame, text="输出目录:").pack(side='left')
        self.output_dir_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(dir_frame, textvariable=self.output_dir_var, state="readonly").pack(side='left', fill='x', expand=True, padx=(10, 10))
        ttk.Button(dir_frame, text="📁 浏览", command=self.browse_output_dir).pack(side='right')
        
        # 按钮区域
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="🚀 开始合并去重", 
                  command=self.start_merge).pack(side='left', padx=5)
        
        # === 右侧日志区域 ===
        log_frame = ttk.LabelFrame(right_frame, text="📋 处理日志", padding=10)
        log_frame.pack(fill='both', expand=True)
        
        # 日志文本框
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_container, wrap='word', font=('Consolas', 9), bg='#2C3E50', fg='white')
        log_scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # 日志控制按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(log_btn_frame, text="🧹 清空日志", 
                  command=self.clear_log).pack(side='left', padx=(0, 10))
        ttk.Button(log_btn_frame, text="💾 保存日志", 
                  command=self.save_log).pack(side='left')
        
        # 初始化Excel合并器
        if MERGER_AVAILABLE:
            self.excel_merger = ExcelMergerTab(None)
            # 重定向日志输出到GUI
            self.excel_merger.log_message = self.log_message
            
            # 初始日志
            self.log_message("Excel合并去重工具已就绪")
            self.log_message("去重规则：1.DOI去重 → 2.题名+作者+来源去重")
        else:
            self.excel_merger = None
            self.log_message("⚠️ 警告：Excel合并器模块不可用")
            self.log_message("❌ 请检查 step3_excel_merger.py 文件")
        
    def add_files(self):
        """添加Excel文件"""
        files = filedialog.askopenfilenames(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        
        added_count = 0
        for file in files:
            if file not in self.selected_files:
                self.selected_files.append(file)
                self.file_listbox.insert(tk.END, os.path.basename(file))
                added_count += 1
        
        if added_count > 0:
            self.log_message(f"已添加 {added_count} 个文件")
    
    def remove_files(self):
        """移除选中的文件"""
        selected = self.file_listbox.curselection()
        if not selected:
            self.log_message("请先选择要移除的文件")
            return
        
        # 从后往前删除，避免索引变化
        for index in reversed(selected):
            removed_file = self.selected_files.pop(index)
            self.file_listbox.delete(index)
            self.log_message(f"已移除: {os.path.basename(removed_file)}")
    
    def clear_files(self):
        """清空文件列表"""
        if self.selected_files:
            count = len(self.selected_files)
            self.selected_files.clear()
            self.file_listbox.delete(0, tk.END)
            self.log_message(f"已清空 {count} 个文件")
        else:
            self.log_message("文件列表已为空")
    
    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
            self.log_message(f"输出目录已设置: {directory}")
    
    def start_merge(self):
        """开始合并去重处理"""
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择Excel文件")
            return
        
        # 构建输出文件路径
        output_path = os.path.join(
            self.output_dir_var.get(),
            self.output_name_var.get()
        )
        
        # 检查输出文件是否已存在
        if os.path.exists(output_path):
            if not messagebox.askyesno("确认", f"文件 {self.output_name_var.get()} 已存在，是否覆盖？"):
                return
        
        # 在新线程中执行合并操作，避免界面卡顿
        def merge_thread():
            try:
                self.log_message("=" * 50)
                self.log_message("开始Excel合并去重处理...")
                self.log_message(f"共选择 {len(self.selected_files)} 个文件")
                
                # 合并文件
                merged_df = self.excel_merger.merge_excel_files(self.selected_files)
                
                if merged_df.empty:
                    self.log_message("合并结果为空，处理终止")
                    return
                
                # 去重处理
                self.log_message("开始去重处理...")
                original_count = len(merged_df)
                deduped_df = self.excel_merger.remove_duplicates(merged_df)
                
                # 获取统计信息
                stats = self.excel_merger.get_duplicate_stats(original_count, len(deduped_df))
                
                # 保存文件
                if self.excel_merger.save_merged_file(deduped_df, output_path):
                    self.log_message("=" * 50)
                    self.log_message("✅ 处理完成！")
                    self.log_message(f"📊 原始记录数: {stats['original_count']}")
                    self.log_message(f"📊 去重后记录数: {stats['final_count']}")
                    self.log_message(f"📊 去除重复记录: {stats['removed_count']} 条")
                    self.log_message(f"📊 去重率: {stats['removal_rate']}%")
                    self.log_message(f"💾 文件已保存: {output_path}")
                    self.log_message("=" * 50)
                    
                    # 在主线程中显示完成对话框
                    self.parent_frame.after(0, lambda: messagebox.showinfo(
                        "处理完成", 
                        f"Excel合并去重完成！\n\n"
                        f"原始记录: {stats['original_count']} 条\n"
                        f"去重后: {stats['final_count']} 条\n"
                        f"去除重复: {stats['removed_count']} 条\n"
                        f"去重率: {stats['removal_rate']}%"
                    ))
                
            except Exception as e:
                error_msg = f"❌ 处理过程中出现错误: {str(e)}"
                self.log_message(error_msg)
                self.parent_frame.after(0, lambda: messagebox.showerror("错误", str(e)))
        
        # 启动处理线程
        threading.Thread(target=merge_thread, daemon=True).start()
    
    def log_message(self, message):
        """在日志区域显示消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # 在主线程中更新UI
        def update_log():
            self.log_text.insert(tk.END, formatted_message)
            self.log_text.see(tk.END)
        
        if threading.current_thread() == threading.main_thread():
            update_log()
        else:
            self.parent_frame.after(0, update_log)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("日志已清空")
    
    def save_log(self):
        """保存日志到文件"""
        log_content = self.log_text.get(1.0, tk.END)
        if not log_content.strip():
            messagebox.showinfo("提示", "日志为空，无需保存")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="保存日志文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log_message(f"日志已保存: {file_path}")
                messagebox.showinfo("成功", "日志保存成功！")
            except Exception as e:
                messagebox.showerror("错误", f"保存日志失败: {str(e)}")
