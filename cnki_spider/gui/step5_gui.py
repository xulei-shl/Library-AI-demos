import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import pandas as pd
from datetime import datetime

# 导入真正的PDF下载器
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from step5_pdf_downloader import PDFDownloader
    DOWNLOADER_AVAILABLE = True
except ImportError as e:
    print(f"导入PDF下载器失败: {e}")
    DOWNLOADER_AVAILABLE = False

class Step5GUI:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.selected_file = None
        self.is_downloading = False
        self.download_thread = None
        self.downloader_instance = None
        self.setup_ui()
        
    def setup_ui(self):
        """设置PDF下载界面"""
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
        ttk.Label(left_frame, text="📄 PDF文献下载", 
                 font=('Microsoft YaHei UI', 18, 'bold'),
                 foreground='#2c3e50').pack(anchor='w', pady=(0, 20))
        
        # 功能说明
        ttk.Label(left_frame, text="根据评分结果批量下载PDF文献", 
                 font=('Microsoft YaHei UI', 10, 'bold'),
                 foreground='#34495e').pack(anchor='w', pady=(0, 10))
        
        # 功能列表
        features_text = """• 选择包含评分的Excel文件
• 设置评分阈值（可选）
• 自动下载文献的PDF"""
        
        ttk.Label(left_frame, text=features_text, 
                 font=('Microsoft YaHei UI', 9),
                 foreground='#7f8c8d').pack(anchor='w', pady=(0, 20))
        
        # 检查下载器可用性
        if not DOWNLOADER_AVAILABLE:
            warning_frame = ttk.Frame(left_frame)
            warning_frame.pack(fill='x', pady=(0, 20))
            ttk.Label(warning_frame, text="⚠️ 警告: PDF下载器模块不可用", 
                     font=('Microsoft YaHei UI', 10, 'bold'),
                     foreground='#e74c3c').pack(anchor='w')
            ttk.Label(warning_frame, text="请确保 step5_pdf_downloader.py 文件存在且可导入", 
                     font=('Microsoft YaHei UI', 9),
                     foreground='#e74c3c').pack(anchor='w')
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(left_frame, text="文件选择", padding=15)
        file_frame.pack(fill='x', pady=(0, 20))
        
        # 文件选择行
        file_row = ttk.Frame(file_frame)
        file_row.pack(fill='x', pady=5)
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_row, textvariable=self.file_path_var, state="readonly")
        file_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(file_row, text="📁 浏览", command=self.browse_file).pack(side='right')
        
        # 下载筛选
        download_frame = ttk.LabelFrame(left_frame, text="下载筛选", padding=15)
        download_frame.pack(fill='x', pady=(0, 20))
        
        # 启用阈值筛选
        self.use_threshold_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(download_frame, text="启用评分筛选", 
                       variable=self.use_threshold_var).pack(anchor='w', pady=5)
        
        # 评分阈值设置
        threshold_row = ttk.Frame(download_frame)
        threshold_row.pack(fill='x', pady=5)
        ttk.Label(threshold_row, text="最低评分阈值:").pack(side='left')
        self.score_threshold = tk.DoubleVar(value=7.0)
        score_scale = ttk.Scale(threshold_row, from_=0, to=10, 
                               variable=self.score_threshold, orient=tk.HORIZONTAL)
        score_scale.pack(side='left', fill='x', expand=True, padx=(10, 10))
        self.score_label = ttk.Label(threshold_row, text="7.0")
        self.score_label.pack(side='right')
        
        # 绑定阈值变化事件
        score_scale.configure(command=self.update_score_label)
        
        # 下载目录设置
        output_frame = ttk.LabelFrame(left_frame, text="下载目录", padding=15)
        output_frame.pack(fill='x', pady=(0, 20))
        
        # 下载目录行
        dir_row = ttk.Frame(output_frame)
        dir_row.pack(fill='x', pady=5)
        self.output_dir_var = tk.StringVar(value="")
        output_dir_entry = ttk.Entry(dir_row, textvariable=self.output_dir_var, state="readonly")
        output_dir_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(dir_row, text="📁 浏览", command=self.browse_output_dir).pack(side='right')
        
        # 按钮区域
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(pady=20)
        
        self.start_btn = ttk.Button(button_frame, text="🚀 开始下载", 
                                   command=self.start_download,
                                   state="disabled" if not DOWNLOADER_AVAILABLE else "normal")
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹ 停止下载", 
                                  command=self.stop_download, state="disabled")
        self.stop_btn.pack(side='left', padx=5)
        
        # === 右侧日志区域 ===
        log_frame = ttk.LabelFrame(right_frame, text="📋 下载日志", padding=10)
        log_frame.pack(fill='both', expand=True)
        
        # 进度显示区域
        progress_frame = ttk.Frame(log_frame)
        progress_frame.pack(fill='x', pady=(0, 10))
        
        self.progress_var = tk.StringVar(value="等待开始...")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
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
        
        # 初始日志
        if DOWNLOADER_AVAILABLE:
            self.log_message("PDF下载工具已就绪 (使用浏览器自动化)")
            self.log_message("支持根据评分阈值筛选文献进行批量下载")
        else:
            self.log_message("PDF下载器模块不可用，请检查依赖")
        
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
        
    def browse_file(self):
        """浏览Excel文件"""
        file = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        if file:
            self.selected_file = file
            self.file_path_var.set(file)
            
            # 自动设置输出目录
            if not self.output_dir_var.get():
                excel_dir = os.path.dirname(file)
                output_dir = os.path.join(excel_dir, "pdfs")
                self.output_dir_var.set(output_dir)
            
            # 检查文件内容
            try:
                df = pd.read_excel(file)
                self.log_message(f"已选择文件: {os.path.basename(file)}")
                self.log_message(f"文件包含 {len(df)} 条记录")
                
                # 检查是否有评分列
                score_columns = [col for col in df.columns if '评分' in col or 'score' in col.lower()]
                if score_columns:
                    self.log_message(f"发现评分列: {', '.join(score_columns)}")
                else:
                    self.log_message("未发现评分列，将下载所有文献")
                
                # 检查URL列
                url_columns = [col for col in df.columns if 'URL' in col or '网址' in col]
                if url_columns:
                    self.log_message(f"发现URL列: {', '.join(url_columns)}")
                else:
                    self.log_message("警告: 未发现URL列")
                    
            except Exception as e:
                self.log_message(f"读取文件出错: {str(e)}")
    
    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
    
    def update_score_label(self, value):
        """更新评分标签"""
        self.score_label.config(text=f"{float(value):.1f}")
        
    def filter_by_score(self, df, threshold=None):
        """根据评分阈值筛选文献"""
        if threshold is None or not self.use_threshold_var.get():
            self.log_message("未启用阈值筛选，将处理所有记录")
            return df
        
        # 查找评分列
        score_columns = [col for col in df.columns if '评分' in col or 'score' in col.lower()]
        
        if not score_columns:
            self.log_message("未找到评分列，将处理所有记录")
            return df
        
        score_col = score_columns[0]  # 使用第一个评分列
        self.log_message(f"使用评分列: {score_col}")
        
        # 筛选数据
        try:
            # 统计空值情况
            original_count = len(df)
            df[score_col] = pd.to_numeric(df[score_col], errors='coerce')
            
            # 分别统计空值和有效值
            null_count = df[score_col].isnull().sum()
            
            # 跳过空值行，只保留有评分且满足阈值的行
            df_with_score = df.dropna(subset=[score_col])  # 移除空值行
            filtered_df = df_with_score[df_with_score[score_col] >= threshold]  # 应用阈值筛选
            
            # 构建筛选结果消息
            filter_msg = f"阈值筛选: {original_count} -> {len(filtered_df)} 条记录"
            if null_count > 0:
                filter_msg += f"，其中{null_count}条没有评分"
            self.log_message(filter_msg)
            
            return filtered_df
            
        except Exception as e:
            self.log_message(f"筛选出错: {str(e)}")
            return df
    
    def batch_download_pdfs(self, df, output_folder):
        """使用真正的PDF下载器进行批量下载"""
        if not DOWNLOADER_AVAILABLE:
            self.log_message("错误: PDF下载器模块不可用")
            return
        
        try:
            # 创建PDF下载器实例
            self.downloader_instance = PDFDownloader(
                download_dir=output_folder, 
                headless=False,  # 显示浏览器窗口，便于处理验证码
                min_delay=3, 
                max_delay=8
            )
            
            # 设置停止检查函数
            def should_stop():
                return not self.is_downloading
            self.downloader_instance.should_stop = should_stop
            
            # 重定向下载器的日志到GUI
            original_log_info = self.downloader_instance.logger.info
            original_log_error = self.downloader_instance.logger.error
            original_log_warning = self.downloader_instance.logger.warning
            
            def gui_log_info(message):
                if self.is_downloading:
                    self.log_message(f"[INFO] {message}")
                    
            def gui_log_error(message):
                if self.is_downloading:
                    self.log_message(f"[ERROR] {message}")
                    
            def gui_log_warning(message):
                if self.is_downloading:
                    self.log_message(f"[WARNING] {message}")
            
            self.downloader_instance.logger.info = gui_log_info
            self.downloader_instance.logger.error = gui_log_error
            self.downloader_instance.logger.warning = gui_log_warning
            
            # 准备下载列表
            download_list = []
            
            # 查找URL和标题列
            url_columns = [col for col in df.columns if 'URL' in col or '网址' in col or '链接' in col]
            title_columns = [col for col in df.columns if '标题' in col or 'title' in col.lower()]
            
            if not url_columns:
                self.log_message("错误: 未找到URL列")
                return
            
            url_col = url_columns[0]
            title_col = title_columns[0] if title_columns else None
            
            self.log_message(f"使用URL列: {url_col}")
            if title_col:
                self.log_message(f"使用标题列: {title_col}")
            
            # 准备下载列表
            for index, row in df.iterrows():
                url = row.get(url_col, "")
                title = row.get(title_col, f"文档_{index+1}") if title_col else f"文档_{index+1}"
                
                if url:
                    download_list.append((url, title))
            
            self.log_message(f"准备下载 {len(download_list)} 个文件")
            
            # 同步下载状态
            self.downloader_instance.is_downloading = self.is_downloading
            
            # 执行批量下载
            result = self.downloader_instance.download_pdfs_batch(download_list)
            
            # 显示结果
            if self.is_downloading:  # 只有在正常完成时才显示结果
                self.log_message(f"下载完成: 成功 {result['success']}, 失败 {result['failed']}, 跳过 {result['skipped']}")
                self.progress_var.set("下载完成")
                self.progress_bar['value'] = 100
            else:
                self.log_message("下载已停止")
                self.progress_var.set("下载已停止")
            
        except Exception as e:
            self.log_message(f"下载过程出错: {str(e)}")
            messagebox.showerror("错误", f"下载失败: {str(e)}")
        
        finally:
            # 清理下载器实例
            if self.downloader_instance:
                try:
                    self.downloader_instance.close_browser()
                    self.log_message("浏览器已关闭")
                except Exception as e:
                    self.log_message(f"关闭浏览器时出错: {str(e)}")
                finally:
                    self.downloader_instance = None
    
    def start_download(self):
        """开始下载任务"""
        if not DOWNLOADER_AVAILABLE:
            messagebox.showerror("错误", "PDF下载器模块不可用")
            return
            
        if not self.selected_file:
            messagebox.showerror("错误", "请先选择Excel文件")
            return
        
        if not self.output_dir_var.get():
            messagebox.showerror("错误", "请设置输出目录")
            return
        
        if self.is_downloading:
            messagebox.showwarning("警告", "下载任务正在进行中")
            return
        
        try:
            # 读取Excel文件
            df = pd.read_excel(self.selected_file)
            
            # 应用评分筛选
            threshold = None
            if self.use_threshold_var.get():
                threshold = self.score_threshold.get()
            
            filtered_df = self.filter_by_score(df, threshold)
            
            if len(filtered_df) == 0:
                messagebox.showwarning("警告", "筛选后没有记录需要下载")
                return
            
            # 开始下载
            self.is_downloading = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            self.log_message(f"开始下载 {len(filtered_df)} 个PDF文件到: {self.output_dir_var.get()}")
            
            # 在新线程中执行下载
            self.download_thread = threading.Thread(
                target=self._download_worker,
                args=(filtered_df, self.output_dir_var.get())
            )
            self.download_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动下载失败: {str(e)}")
            self.log_message(f"启动下载失败: {str(e)}")
    
    def _download_worker(self, df, output_folder):
        """下载工作线程"""
        try:
            self.batch_download_pdfs(df, output_folder)
        except Exception as e:
            self.log_message(f"下载线程异常: {str(e)}")
        finally:
            # 重置状态 - 使用 after 方法确保在主线程中执行
            def reset_ui_state():
                self.is_downloading = False
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                if hasattr(self, 'progress_bar'):
                    self.progress_bar['value'] = 0
                
            self.parent_frame.after(0, reset_ui_state)
    
    def stop_download(self):
        """停止下载任务"""
        if self.is_downloading:
            self.is_downloading = False
            self.log_message("正在停止下载...")
            self.progress_var.set("正在停止...")
            
            # 如果有下载器实例，也停止它
            if self.downloader_instance:
                self.downloader_instance.is_downloading = False
                try:
                    self.downloader_instance.close_browser()
                    self.log_message("浏览器已关闭")
                except Exception as e:
                    self.log_message(f"关闭浏览器时出错: {str(e)}")
            
            # 强制更新按钮状态
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.progress_var.set("下载已停止")
            
            # 如果下载线程还在运行，等待其结束
            if self.download_thread and self.download_thread.is_alive():
                self.log_message("等待下载线程结束...")
                # 在新线程中等待，避免阻塞UI
                threading.Thread(target=self._wait_for_thread_stop).start()
        else:
            self.log_message("当前没有正在进行的下载任务")
    
    def _wait_for_thread_stop(self):
        """等待下载线程停止"""
        try:
            if self.download_thread:
                self.download_thread.join(timeout=5)  # 最多等待5秒
                if self.download_thread.is_alive():
                    self.log_message("下载线程未能及时停止")
                else:
                    self.log_message("下载线程已停止")
        except Exception as e:
            self.log_message(f"等待线程停止时出错: {str(e)}")
