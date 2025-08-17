import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
from datetime import datetime

# 添加父目录到路径以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from step2_cnki_spider import cnki_spider_with_stop
    SPIDER_AVAILABLE = True
except ImportError as e:
    print(f"导入爬虫模块失败: {e}")
    SPIDER_AVAILABLE = False

try:
    from config_manager import ConfigManager
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"导入配置管理器失败: {e}")
    CONFIG_AVAILABLE = False

class Step2GUI:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.config_manager = ConfigManager()
        self.default_settings = self.config_manager.get_default_settings()
        self.crawl_thread = None
        self.is_crawling = False
        self.stop_flag = False  # 添加停止标志
        self.config_refresh_callback = None
        # 预检索相关状态
        self.pre_search_completed = False  # 预检索完成标志
        self.search_results_count = 0      # 检索结果数量
        self.pre_search_thread = None      # 预检索线程
        self.is_pre_searching = False      # 预检索进行中标志
        self.setup_ui()
    
    def set_config_refresh_callback(self, callback):
        """设置配置刷新回调函数"""
        self.config_refresh_callback = callback
        
    def setup_ui(self):
        """设置CNKI爬取界面"""

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
        
        # 左列：参数设置
        self.setup_left_panel(left_frame)
        
        # 右列：状态和日志
        self.setup_right_panel(right_frame)
        
        # 初始化
        self.on_year_mode_change()
        self.log_message("🎉 欢迎使用CNKI文献爬虫工具！")
        self.log_message("📝 请设置检索参数，然后点击'开始爬取'按钮")
        
    def setup_left_panel(self, parent):
        """设置左侧参数面板"""
        # 检索词输入区域
        search_frame = ttk.LabelFrame(parent, text="🔎 检索词", padding="15")
        search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        self.keyword_var = tk.StringVar(value="")
        keyword_entry = ttk.Entry(search_frame, textvariable=self.keyword_var, 
                                 font=('Microsoft YaHei UI', 11))
        keyword_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(search_frame, text="💡 提示：支持多个关键词，用空格分隔", 
                 font=('Microsoft YaHei UI', 9),
                 foreground='#7f8c8d').grid(row=2, column=0, sticky=tk.W)
        
        # 年份设置区域
        year_frame = ttk.LabelFrame(parent, text="📅 时间范围", padding="15")
        year_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        self.year_mode = tk.StringVar(value="recent")
        
        # 年份选择按钮
        year_btn_frame = ttk.Frame(year_frame)
        year_btn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        recent_radio = ttk.Radiobutton(year_btn_frame, text="📈 最近一年", 
                                      variable=self.year_mode, value="recent",
                                      command=self.on_year_mode_change)
        recent_radio.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        custom_radio = ttk.Radiobutton(year_btn_frame, text="🗓️ 自定义年份范围", 
                                      variable=self.year_mode, value="custom",
                                      command=self.on_year_mode_change)
        custom_radio.grid(row=0, column=1, sticky=tk.W)
        
        # 年份输入区域
        year_input_frame = ttk.Frame(year_frame)
        year_input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(year_input_frame, text="起始年份:", 
                 font=('Microsoft YaHei UI', 10, 'bold')).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        default_start_year = self.default_settings.get('start_year', '2024')
        self.start_year_var = tk.StringVar(value=default_start_year)
        self.start_year_entry = ttk.Entry(year_input_frame, textvariable=self.start_year_var, width=12)
        self.start_year_entry.grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(year_input_frame, text="结束年份:", 
                 font=('Microsoft YaHei UI', 10, 'bold')).grid(
            row=0, column=2, sticky=tk.W, padx=(0, 5))
        
        default_end_year = self.default_settings.get('end_year', '2025')
        self.end_year_var = tk.StringVar(value=default_end_year)
        self.end_year_entry = ttk.Entry(year_input_frame, textvariable=self.end_year_var, width=12)
        self.end_year_entry.grid(row=0, column=3)
        
        # 期刊类型选择
        journal_frame = ttk.LabelFrame(parent, text="📚 期刊类型", padding="15")
        journal_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        self.check_core_var = tk.BooleanVar(value=self.default_settings.get('check_core', False))
        core_checkbox = ttk.Checkbutton(journal_frame, 
                                       text="🏆 仅搜索核心期刊 (SCI/EI/北大核心/CSSCI等)", 
                                       variable=self.check_core_var)
        core_checkbox.grid(row=0, column=0, sticky=tk.W)

        # 结果数量设置
        results_frame = ttk.LabelFrame(parent, text="📊 结果数量", padding="15")
        results_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        results_input_frame = ttk.Frame(results_frame)
        results_input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(results_input_frame, text="最大结果数:", 
                 font=('Microsoft YaHei UI', 10, 'bold')).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        default_max_results = self.default_settings.get('max_results', 50)
        self.max_results_var = tk.StringVar(value=str(default_max_results))
        max_results_entry = ttk.Entry(results_input_frame, textvariable=self.max_results_var, width=12)
        max_results_entry.grid(row=0, column=1)
        
        ttk.Label(results_frame, text="💡 设置爬取的最大文献数量，建议不超过200", 
                 font=('Microsoft YaHei UI', 9),
                 foreground='#7f8c8d').grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # 输出设置
        output_frame = ttk.LabelFrame(parent, text="💾 输出设置", padding="15")
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(output_frame, text="输出文件夹:", 
                 font=('Microsoft YaHei UI', 10, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        path_frame = ttk.Frame(output_frame)
        path_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # 从配置中读取输出路径，如果没有则使用默认值
        saved_output_path = self.default_settings.get('output_path', os.path.join(os.getcwd(), "data"))
        self.output_path_var = tk.StringVar(value=saved_output_path)
        output_path_entry = ttk.Entry(path_frame, textvariable=self.output_path_var, state="readonly")
        output_path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        browse_button = ttk.Button(path_frame, text="📁 浏览", command=self.browse_output_folder)
        browse_button.grid(row=0, column=1)
        
        # 控制按钮区域 - 分成上下两行，每行2个按钮
        control_frame = ttk.Frame(output_frame)
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 第一行按钮：预检索、开始爬取
        self.pre_search_button = ttk.Button(control_frame, text="🔍 预检索", 
                                           command=self.start_pre_search, width=15,
                                           state="disabled" if not SPIDER_AVAILABLE else "normal")
        self.pre_search_button.grid(row=0, column=0, padx=(0, 10), pady=(0, 5), sticky=(tk.W, tk.E))
        
        self.start_button = ttk.Button(control_frame, text="🚀 开始爬取", 
                                      command=self.start_crawling, width=15,
                                      state="disabled" if not SPIDER_AVAILABLE else "normal")
        self.start_button.grid(row=0, column=1, pady=(0, 5), sticky=(tk.W, tk.E))
        
        # 第二行按钮：保存配置、停止
        save_settings_btn = ttk.Button(control_frame, text="⚙️ 保存配置", 
                                      command=self.save_current_as_default, width=15)
        save_settings_btn.grid(row=1, column=0, padx=(0, 10), sticky=(tk.W, tk.E))
        
        self.stop_button = ttk.Button(control_frame, text="⏹️ 停止", 
                                     command=self.stop_crawling,
                                     state="disabled", width=15)
        self.stop_button.grid(row=1, column=1, sticky=(tk.W, tk.E))
        
        # 配置按钮区域的列权重，使两列平均分配宽度
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        
        # 配置网格权重
        parent.columnconfigure(0, weight=1)  # 让左侧面板的列也能扩展
        search_frame.columnconfigure(0, weight=1)
        year_frame.columnconfigure(0, weight=1)
        journal_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        path_frame.columnconfigure(0, weight=1)
        
    def setup_right_panel(self, parent):
        """设置右侧状态面板"""
        # 状态区域
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill='x', pady=(0, 15))
        
        # 进度条
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=(0, 10))
        
        # 状态标签
        self.status_var = tk.StringVar(value="🟢 就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                font=('Microsoft YaHei UI', 10, 'bold'))
        status_label.pack(anchor='w')
        
        # 实时日志区域
        log_frame = ttk.LabelFrame(parent, text="📋 实时日志", padding=10)
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
        
    def on_year_mode_change(self):
        """年份模式改变时的回调"""
        if self.year_mode.get() == "recent":
            self.start_year_entry.config(state="disabled")
            self.end_year_entry.config(state="disabled")
        else:
            self.start_year_entry.config(state="normal")
            self.end_year_entry.config(state="normal")
    
    def browse_output_folder(self):
        """浏览输出文件夹"""
        folder = filedialog.askdirectory(initialdir=self.output_path_var.get())
        if folder:
            self.output_path_var.set(folder)
            self.log_message(f"📁 输出文件夹已设置为: {folder}")
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.parent_frame.update_idletasks()
    
    def save_current_as_default(self):
        """保存当前检索设置为默认值（不影响其他配置）"""
        try:
            # 验证max_results输入
            try:
                max_results = int(self.max_results_var.get())
                if max_results <= 0:
                    messagebox.showerror("错误", "最大结果数必须是正整数！")
                    return
            except ValueError:
                messagebox.showerror("错误", "请输入有效的最大结果数！")
                return
            
            # 根据时间范围模式设置年份
            if self.year_mode.get() == "recent":
                # 使用"最近一年"时，设置time_range并将年份设为None
                current_settings = {
                    'keyword': self.keyword_var.get().strip(),
                    'time_range': 'recent_year',
                    'start_year': None,
                    'end_year': None,
                    'check_core': self.check_core_var.get(),
                    'max_results': max_results,
                    'output_path': self.output_path_var.get()
                }
            else:
                # 使用自定义年份时，设置具体年份和time_range
                start_year = self.start_year_var.get().strip()
                end_year = self.end_year_var.get().strip()
                current_settings = {
                    'keyword': self.keyword_var.get().strip(),
                    'time_range': 'custom',
                    'start_year': start_year if start_year else None,
                    'end_year': end_year if end_year else None,
                    'check_core': self.check_core_var.get(),
                    'max_results': max_results,
                    'output_path': self.output_path_var.get()
                }
            
            # 使用专门的方法只更新检索设置
            success = self.config_manager.update_search_settings_only(**current_settings)
            
            if success:
                self.log_message("⚙️ 当前检索设置已保存为默认值（其他配置保持不变）")
                messagebox.showinfo("成功", "当前检索设置已保存为默认值！\n其他配置（爬虫配置、AI模型设置等）保持不变。")
                
                # 调用配置刷新回调，通知配置管理页面更新显示
                if self.config_refresh_callback:
                    self.config_refresh_callback()
            else:
                self.log_message("❌ 保存默认设置失败")
                messagebox.showerror("错误", "保存默认设置失败！")
                
        except Exception as e:
            error_msg = f"保存默认设置时出错: {str(e)}"
            self.log_message(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
    
    def save_search_config(self):
        """保存当前检索配置到配置管理器"""
        try:
            # 验证max_results输入
            try:
                max_results = int(self.max_results_var.get())
                if max_results <= 0:
                    raise ValueError("最大结果数必须是正整数")
            except ValueError:
                max_results = 100  # 使用默认值
            
            # 根据时间范围模式设置年份和time_range
            if self.year_mode.get() == "recent":
                current_settings = {
                    'keyword': self.keyword_var.get().strip(),
                    'time_range': 'recent_year',
                    'start_year': None,
                    'end_year': None,
                    'check_core': self.check_core_var.get(),
                    'max_results': max_results,
                    'output_path': self.output_path_var.get()
                }
            else:
                start_year = self.start_year_var.get().strip()
                end_year = self.end_year_var.get().strip()
                current_settings = {
                    'keyword': self.keyword_var.get().strip(),
                    'time_range': 'custom',
                    'start_year': start_year if start_year else None,
                    'end_year': end_year if end_year else None,
                    'check_core': self.check_core_var.get(),
                    'max_results': max_results,
                    'output_path': self.output_path_var.get()
                }
            
            # 更新配置管理器中的设置
            self.config_manager.update_search_settings_only(**current_settings)
            return True
            
        except Exception as e:
            self.log_message(f"❌ 保存检索配置失败: {str(e)}")
            return False
    
    def validate_inputs(self):
        """验证输入参数"""
        if not self.keyword_var.get().strip():
            messagebox.showerror("❌ 错误", "请输入检索词！")
            return False
        
        if self.year_mode.get() == "custom":
            try:
                start_year = int(self.start_year_var.get())
                end_year = int(self.end_year_var.get())
                
                if start_year > end_year:
                    messagebox.showerror("❌ 错误", "起始年份不能大于结束年份！")
                    return False
                
                current_year = datetime.now().year
                if start_year > current_year or end_year > current_year:
                    messagebox.showwarning("⚠️ 警告", f"年份不能超过当前年份({current_year})！")
                    return False
                    
            except ValueError:
                messagebox.showerror("❌ 错误", "请输入有效的年份！")
                return False
        
        return True
    
    def start_pre_search(self):
        """开始预检索"""
        if not self.validate_inputs():
            return
        
        # 保存当前检索配置
        self.save_search_config()
        self.log_message("💾 已保存当前检索配置")
        
        # 重置状态
        self.stop_flag = False
        self.pre_search_completed = False
        self.search_results_count = 0
        
        # 更新UI状态
        self.is_pre_searching = True
        self.pre_search_button.config(state="disabled")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress.start()
        self.status_var.set("🔍 正在预检索...")
        
        # 获取参数
        keyword = self.keyword_var.get().strip()
        check_core = self.check_core_var.get()
        
        if self.year_mode.get() == "recent":
            start_year = None
            end_year = None
            self.log_message(f"🔍 开始预检索: {keyword} (最近一年)")
        else:
            start_year = self.start_year_var.get().strip()
            end_year = self.end_year_var.get().strip()
            # 确保年份不为空字符串
            if not start_year:
                start_year = None
            if not end_year:
                end_year = None
            self.log_message(f"🔍 开始预检索: {keyword} ({start_year}-{end_year})")
        
        if check_core:
            self.log_message("🏆 已启用核心期刊筛选")
        
        # 在新线程中运行预检索
        self.pre_search_thread = threading.Thread(
            target=self.run_pre_search,
            args=(keyword, start_year, end_year, check_core),
            daemon=True
        )
        self.pre_search_thread.start()
    
    def start_crawling(self):
        """开始爬取"""
        if not self.validate_inputs():
            return
        
        # 保存当前检索配置
        self.save_search_config()
        self.log_message("💾 已保存当前检索配置")
        
        # 重置停止标志
        self.stop_flag = False
        
        # 更新UI状态
        self.is_crawling = True
        self.pre_search_button.config(state="disabled")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress.start()
        
        # 获取参数
        keyword = self.keyword_var.get().strip()
        check_core = self.check_core_var.get()
        
        if self.year_mode.get() == "recent":
            start_year = None
            end_year = None
        else:
            start_year = self.start_year_var.get().strip()
            end_year = self.end_year_var.get().strip()
            # 确保年份不为空字符串
            if not start_year:
                start_year = None
            if not end_year:
                end_year = None
        
        # 检查是否已完成预检索
        if self.pre_search_completed:
            self.status_var.set("🔄 继续爬取...")
            self.log_message(f"🚀 继续爬取 (已找到 {self.search_results_count} 条结果)")
            # 在新线程中继续爬取
            self.crawl_thread = threading.Thread(
                target=self.run_continue_crawler,
                daemon=True
            )
        else:
            self.status_var.set("🔄 正在爬取...")
            if self.year_mode.get() == "recent":
                self.log_message(f"🔍 开始完整爬取: {keyword} (最近一年)")
            else:
                self.log_message(f"🔍 开始完整爬取: {keyword} ({start_year}-{end_year})")
            
            if check_core:
                self.log_message("🏆 已启用核心期刊筛选")
            
            # 在新线程中运行完整爬虫
            self.crawl_thread = threading.Thread(
                target=self.run_crawler,
                args=(keyword, start_year, end_year, check_core),
                daemon=True
            )
        
        self.crawl_thread.start()
    
    def run_pre_search(self, keyword, start_year, end_year, check_core):
        """在后台线程中运行预检索"""
        try:
            self.log_message("🌐 正在启动浏览器进行预检索...")
            
            # 重定向原始爬虫的print输出
            original_print = print
            def gui_print(*args, **kwargs):
                message = ' '.join(str(arg) for arg in args)
                self.parent_frame.after(0, lambda msg=message: self.log_message(msg))
                original_print(*args, **kwargs)
            
            # 临时替换print函数
            import builtins
            builtins.print = gui_print
            
            try:
                # 导入预检索函数
                from step2_cnki_spider import cnki_pre_search
                
                # 调用预检索函数
                output_path = self.output_path_var.get()
                results_count = cnki_pre_search(keyword, start_year, end_year, check_core, lambda: self.stop_flag, output_path)
                
                if self.is_pre_searching and not self.stop_flag:
                    self.search_results_count = results_count
                    self.log_message(f"🎯 预检索完成！找到 {results_count} 条结果")
                    self.parent_frame.after(0, self.pre_search_finished, True, results_count)
                elif self.stop_flag:
                    self.log_message("⏹️ 预检索已被用户停止")
                    self.parent_frame.after(0, self.pre_search_finished, False)
            finally:
                # 恢复原始print函数
                builtins.print = original_print
            
        except Exception as e:
            if "用户停止" in str(e):
                self.log_message("⏹️ 预检索已被用户停止")
            else:
                error_msg = f"❌ 预检索过程中出现错误: {str(e)}"
                self.log_message(error_msg)
            self.parent_frame.after(0, self.pre_search_finished, False)
    
    def run_continue_crawler(self):
        """在后台线程中继续爬取"""
        try:
            self.log_message("🔄 继续爬取过程...")
            
            # 重定向原始爬虫的print输出
            original_print = print
            def gui_print(*args, **kwargs):
                message = ' '.join(str(arg) for arg in args)
                if "准备下载论文元数据" in message:
                    message = f"📥 {message}"
                self.parent_frame.after(0, lambda msg=message: self.log_message(msg))
                original_print(*args, **kwargs)
            
            # 临时替换print函数
            import builtins
            builtins.print = gui_print
            
            try:
                # 导入继续爬取函数
                from step2_cnki_spider import cnki_continue_crawl
                
                # 调用继续爬取函数
                output_path = self.output_path_var.get()
                max_results = int(self.max_results_var.get())
                cnki_continue_crawl(lambda: self.stop_flag, output_path, max_results)
                
                if self.is_crawling and not self.stop_flag:
                    self.log_message("✅ 爬取完成！")
                    self.parent_frame.after(0, self.crawling_finished, True)
                elif self.stop_flag:
                    self.log_message("⏹️ 爬取已被用户停止")
                    self.parent_frame.after(0, self.crawling_finished, False)
            finally:
                # 恢复原始print函数
                builtins.print = original_print
            
        except Exception as e:
            if "用户停止" in str(e):
                self.log_message("⏹️ 爬取已被用户停止")
            else:
                error_msg = f"❌ 继续爬取过程中出现错误: {str(e)}"
                self.log_message(error_msg)
            self.parent_frame.after(0, self.crawling_finished, False)
    
    def run_crawler(self, keyword, start_year, end_year, check_core):
        """在后台线程中运行完整爬虫"""
        try:
            self.log_message("🌐 正在启动浏览器...")
            
            # 重定向原始爬虫的print输出
            original_print = print
            def gui_print(*args, **kwargs):
                message = ' '.join(str(arg) for arg in args)
                if "准备下载论文元数据" in message:
                    message = f"📥 {message}"
                self.parent_frame.after(0, lambda msg=message: self.log_message(msg))
                original_print(*args, **kwargs)
            
            # 临时替换print函数
            import builtins
            builtins.print = gui_print
            
            try:
                # 调用修改后的爬虫函数，传入停止标志检查函数和输出路径
                output_path = self.output_path_var.get()
                cnki_spider_with_stop(keyword, start_year, end_year, check_core, lambda: self.stop_flag, output_path)
                
                if self.is_crawling and not self.stop_flag:
                    self.log_message("✅ 爬取完成！")
                    self.parent_frame.after(0, self.crawling_finished, True)
                elif self.stop_flag:
                    self.log_message("⏹️ 爬取已被用户停止")
                    self.parent_frame.after(0, self.crawling_finished, False)
            finally:
                # 恢复原始print函数
                builtins.print = original_print
            
        except Exception as e:
            if "用户停止" in str(e):
                self.log_message("⏹️ 爬取已被用户停止")
            else:
                error_msg = f"❌ 爬取过程中出现错误: {str(e)}"
                self.log_message(error_msg)
            self.parent_frame.after(0, self.crawling_finished, False)
    
    def stop_crawling(self):
        """停止爬取或预检索"""
        self.stop_flag = True
        
        if self.is_pre_searching:
            self.is_pre_searching = False
            self.log_message("⏹️ 正在停止预检索...")
            
            # 如果预检索线程还在运行，等待一小段时间让它检查停止标志
            if self.pre_search_thread and self.pre_search_thread.is_alive():
                self.log_message("⏹️ 等待预检索进程停止...")
                self.parent_frame.after(2000, lambda: self.pre_search_finished(False))
            else:
                self.pre_search_finished(False)
        elif self.is_crawling:
            self.is_crawling = False
            self.log_message("⏹️ 正在停止爬取...")
            
            # 如果爬虫线程还在运行，等待一小段时间让它检查停止标志
            if self.crawl_thread and self.crawl_thread.is_alive():
                self.log_message("⏹️ 等待爬虫进程停止...")
                self.parent_frame.after(2000, lambda: self.crawling_finished(False))
            else:
                self.crawling_finished(False)
    
    def pre_search_finished(self, success, results_count=0):
        """预检索完成后的UI更新"""
        self.is_pre_searching = False
        self.pre_search_button.config(state="normal")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress.stop()
        
        if success:
            self.pre_search_completed = True
            self.search_results_count = results_count
            self.status_var.set(f"🎯 预检索完成 ({results_count}条)")
            self.log_message(f"🎉 预检索完成！找到 {results_count} 条结果，可以点击'开始爬取'继续。")
            messagebox.showinfo("🎯 预检索完成", f"找到 {results_count} 条结果！\n\n点击'开始爬取'按钮继续下载文献数据。")
        else:
            self.pre_search_completed = False
            self.search_results_count = 0
            self.status_var.set("⏹️ 预检索停止")
            self.log_message("⏹️ 预检索任务已停止")
    
    def crawling_finished(self, success):
        """爬取完成后的UI更新"""
        self.is_crawling = False
        self.pre_search_button.config(state="normal")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress.stop()
        
        if success:
            self.status_var.set("✅ 爬取完成")
            self.log_message("🎉 所有任务已完成！请查看输出文件夹。")
            messagebox.showinfo("🎉 完成", "文献爬取完成！\n请查看输出文件夹中的结果。")
            # 重置预检索状态，允许下次重新预检索
            self.pre_search_completed = False
            self.search_results_count = 0
        else:
            self.status_var.set("⏹️ 爬取停止")
            self.log_message("⏹️ 爬取任务已停止")
    
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