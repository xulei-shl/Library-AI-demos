import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from step4_data_analyzer import DataAnalyzer

class Step4GUI:
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.analyzer = DataAnalyzer(config_manager)
        self.stop_event = threading.Event()
        self.analysis_thread = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面 - 左右等宽分布"""
        # 创建主容器，使用grid布局实现等宽分配
        main_container = ttk.Frame(self.parent)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 配置grid权重，左右等宽
        main_container.columnconfigure(0, weight=3)  # 左侧面板权重
        main_container.columnconfigure(1, weight=2)  # 右侧面板权重
        main_container.rowconfigure(0, weight=1)
        
        # 左侧面板
        left_panel = ttk.Frame(main_container)
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # 右侧面板
        right_panel = ttk.Frame(main_container)
        right_panel.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # === 左侧面板内容 ===
        self._setup_left_panel(left_panel)
        
        # === 右侧面板内容 ===
        self._setup_right_panel(right_panel)
    
    def _setup_left_panel(self, left_panel):
        """设置左侧面板内容"""
        # 标题
        ttk.Label(left_panel, text="🤖 文献相关性分析", 
                 font=('Microsoft YaHei UI', 14, 'bold'),
                 foreground='#2c3e50').pack(pady=(0, 15))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(left_panel, text="文献文件选择", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 文件路径显示
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, 
                              state="readonly", width=30)
        file_entry.pack(fill=tk.X, pady=(0, 10))
        
        # 浏览按钮
        browse_btn = ttk.Button(file_frame, text="📁 选择Excel文件", 
                               command=self.browse_file)
        browse_btn.pack(fill=tk.X)
        
        # 研究主题输入区域
        topic_frame = ttk.LabelFrame(left_panel, text="研究主题", padding=10)
        topic_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(topic_frame, text="请输入研究主题:").pack(anchor=tk.W, pady=(0, 5))
        
        self.topic_text = tk.Text(topic_frame, wrap=tk.WORD, font=('Microsoft YaHei UI', 10), 
                                 height=4, bg='#f8f9fa', relief=tk.FLAT, bd=1)
        self.topic_text.pack(fill=tk.X, pady=(0, 10))
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(left_panel, text="分析状态", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.status_label = ttk.Label(status_frame, text="准备就绪", 
                                     font=('Microsoft YaHei UI', 10),
                                     foreground='#2c3e50')
        self.status_label.pack(pady=5)
        
        # 按钮区域 - 2行2列布局
        button_container = ttk.Frame(left_panel)
        button_container.pack(fill=tk.X, pady=10)
        
        # 配置按钮框架的列权重 - 均匀分配
        button_container.columnconfigure(0, weight=1)
        button_container.columnconfigure(1, weight=1)
        
        # 第一行：分析控制按钮
        self.start_btn = ttk.Button(button_container, text="🚀 开始分析", 
                                   command=self.start_analysis,
                                   style="Accent.TButton")
        self.start_btn.grid(row=0, column=0, sticky='ew', padx=(0, 3), pady=(0, 5))
        
        self.stop_btn = ttk.Button(button_container, text="⏹️ 停止分析", 
                                  command=self.stop_analysis,
                                  state="disabled")
        self.stop_btn.grid(row=0, column=1, sticky='ew', padx=(3, 0), pady=(0, 5))
        
        # 第二行：日志管理按钮
        self.export_log_btn = ttk.Button(button_container, text="📤 导出日志", 
                                        command=self.export_log)
        self.export_log_btn.grid(row=1, column=0, sticky='ew', padx=(0, 3))
        
        self.clear_log_btn = ttk.Button(button_container, text="🗑️ 清空日志", 
                                       command=self.clear_log)
        self.clear_log_btn.grid(row=1, column=1, sticky='ew', padx=(3, 0))
    
    def _setup_right_panel(self, right_panel):
        """设置右侧面板内容"""
        # 日志显示标题
        ttk.Label(right_panel, text="📋 分析日志", 
                 font=('Microsoft YaHei UI', 14, 'bold'),
                 foreground='#2c3e50').pack(pady=(0, 15))
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(right_panel, text="实时分析进度与结果", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建文本框和滚动条
        text_container = ttk.Frame(log_frame)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(text_container, wrap=tk.WORD, font=('Consolas', 9),
                               bg='#2c3e50', fg='#ecf0f1', insertbackground='white',
                               state=tk.DISABLED)
        log_v_scroll = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.log_text.yview)
        
        self.log_text.configure(yscrollcommand=log_v_scroll.set)
        
        # 布局文本框和滚动条
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        text_container.columnconfigure(0, weight=1)
        text_container.rowconfigure(0, weight=1)
        
        # 初始提示文本
        self.add_log("欢迎使用文献相关性分析工具！")
        self.add_log("请选择Excel文件并输入研究主题，然后点击'开始分析'按钮。")
        self.add_log("=" * 50)
        
        # 初始化状态
        self.status_label.config(text="请选择Excel文件")
        
    def browse_file(self):
        """浏览Excel文件"""
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[
                ("Excel文件", "*.xlsx *.xls"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            self.file_path_var.set(os.path.basename(file_path))
            self.selected_file = file_path  # 保存完整路径
            self.refresh_status()
            self.add_log(f"已选择文件: {os.path.basename(file_path)}")
    
    def refresh_status(self):
        """刷新处理状态"""
        if not hasattr(self, 'selected_file') or not self.selected_file or not os.path.exists(self.selected_file):
            self.status_label.config(text="请选择Excel文件")
            return
        
        try:
            # 传递进度回调函数以便自动显示统计结果
            status = self.analyzer.get_analysis_status(self.selected_file, progress_callback=lambda progress, msg: self.add_log(msg))
            
            if status["total"] > 0:
                if status["remaining"] == 0:
                    self.status_label.config(text="所有记录已处理完成", foreground="green")
                else:
                    self.status_label.config(text=f"共 {status['total']} 条记录，已处理 {status['processed']} 条", 
                                           foreground="#2c3e50")
            else:
                self.status_label.config(text="文件中没有数据", foreground="orange")
                
        except Exception as e:
            self.add_log(f"刷新状态失败: {str(e)}")
            self.status_label.config(text="状态获取失败", foreground="red")
    
    def start_analysis(self):
        """开始分析"""
        # 验证输入
        if not hasattr(self, 'selected_file') or not self.selected_file:
            messagebox.showwarning("输入错误", "请先选择Excel文件")
            return
        
        if not os.path.exists(self.selected_file):
            messagebox.showerror("文件错误", "选择的文件不存在")
            return
        
        research_topic = self.topic_text.get("1.0", tk.END).strip()
        if not research_topic:
            messagebox.showwarning("输入错误", "请输入研究主题")
            return
        
        # 检查是否已经在分析中
        if self.analysis_thread and self.analysis_thread.is_alive():
            messagebox.showinfo("提示", "分析正在进行中")
            return
        
        # 重置停止事件
        self.stop_event.clear()
        
        # 更新UI状态
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        self.research_topic = research_topic
        self.add_log(f"开始分析文献相关性...")
        self.add_log(f"研究主题: {research_topic}")
        self.add_log(f"文件路径: {self.selected_file}")
        self.add_log("=" * 50)
        
        # 启动分析线程
        self.analysis_thread = threading.Thread(target=self._run_analysis, args=(self.selected_file,))
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
    
    def stop_analysis(self):
        """停止分析"""
        self.stop_event.set()
        self.add_log("正在停止分析...")
        
        # 更新UI状态
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def _run_analysis(self, file_path):
        """在后台线程中运行分析"""
        try:
            success = self.analyzer.analyze_data(
                file_path, 
                progress_callback=self._progress_callback,
                stop_event=self.stop_event
            )
            
            # 在主线程中更新UI
            self.parent.after(0, self._analysis_finished, success)
            
        except Exception as e:
            self.parent.after(0, self._analysis_error, str(e))
    
    def _progress_callback(self, progress, message):
        """进度回调函数"""
        def update_ui():
            self.status_label.config(text="分析进行中...", foreground="#007bff")
            self.add_log(message)
        
        self.parent.after(0, update_ui)
    
    def _analysis_finished(self, success):
        """分析完成"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        if success:
            self.add_log("=" * 50)
            self.add_log("✅ 分析完成！")
            messagebox.showinfo("完成", "数据分析已完成！")
        else:
            self.add_log("⏹️ 分析被中断")
            messagebox.showinfo("中断", "分析已被中断")
        
        # 移除refresh_status()调用，避免重复显示统计结果
        # 统计结果已在analyze_data方法中显示
    
    def _analysis_error(self, error_msg):
        """分析出错"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        self.add_log("=" * 50)
        self.add_log(f"❌ 分析出错: {error_msg}")
        messagebox.showerror("错误", f"分析过程中出现错误:\n{error_msg}")
        
        self.status_label.config(text="❌ 分析出错", foreground="red")
    
    def export_log(self):
        """导出日志"""
        try:
            # 获取日志内容
            self.log_text.config(state=tk.NORMAL)
            log_content = self.log_text.get("1.0", tk.END)
            self.log_text.config(state=tk.DISABLED)
            
            if not log_content.strip():
                messagebox.showwarning("导出失败", "没有可导出的日志内容")
                return
            
            # 选择保存位置
            filename = filedialog.asksaveasfilename(
                title="导出分析日志",
                defaultextension=".txt",
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("所有文件", "*.*")
                ]
            )
            
            if filename:
                # 保存日志文件
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"文献相关性分析日志\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(log_content)
                
                self.add_log(f"✅ 日志已导出到: {filename}")
                messagebox.showinfo("导出成功", f"分析日志已导出到:\n{filename}")
                
        except Exception as e:
            error_msg = f"导出日志时出错: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("导出失败", error_msg)
    
    def clear_log(self):
        """清空日志"""
        result = messagebox.askyesno("确认清空", "是否清空所有日志内容？")
        if result:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.config(state=tk.DISABLED)
            
            # 重新添加欢迎信息
            self.add_log("欢迎使用文献相关性分析工具！")
            self.add_log("请选择Excel文件并输入研究主题，然后点击'开始分析'按钮。")
            self.add_log("=" * 50)
    
    def add_log(self, message):
        """添加日志信息"""
        self.log_text.config(state=tk.NORMAL)
        
        # 添加时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)  # 自动滚动到底部
        self.log_text.config(state=tk.DISABLED)
        
        # 强制更新UI
        self.parent.update_idletasks()