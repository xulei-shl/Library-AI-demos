import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys

# 添加父目录到路径以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config_manager import ConfigManager
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"导入配置管理器失败: {e}")
    CONFIG_AVAILABLE = False

class ConfigGUI:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        
        # 初始化配置管理器
        if CONFIG_AVAILABLE:
            self.config_manager = ConfigManager()
        else:
            self.config_manager = None
            
        self.setup_ui()
        self.load_current_config()
        
    def setup_ui(self):
        """设置配置管理界面"""
        # 创建滚动容器
        canvas = tk.Canvas(self.parent_frame, bg='#f8f9fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.parent_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 主要内容区域
        content_frame = ttk.Frame(scrollable_frame, padding="20")
        content_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        ttk.Label(content_frame, text="⚙️ 配置管理", 
                 font=('Microsoft YaHei UI', 18, 'bold'),
                 foreground='#2c3e50').grid(row=0, column=0, sticky=tk.W, pady=(0, 20))
        
        # 默认搜索设置
        search_frame = ttk.LabelFrame(content_frame, text="默认搜索设置", padding=15)
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(search_frame, text="默认关键词:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.default_keyword_var = tk.StringVar()
        keyword_entry = ttk.Entry(search_frame, textvariable=self.default_keyword_var, width=40)
        keyword_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        ttk.Label(search_frame, text="默认起始年份:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.default_start_year_var = tk.StringVar()
        start_year_entry = ttk.Entry(search_frame, textvariable=self.default_start_year_var, width=15)
        start_year_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        ttk.Label(search_frame, text="默认结束年份:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.default_end_year_var = tk.StringVar()
        end_year_entry = ttk.Entry(search_frame, textvariable=self.default_end_year_var, width=15)
        end_year_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        ttk.Label(search_frame, text="最大结果数:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.default_max_results_var = tk.StringVar()
        max_results_entry = ttk.Entry(search_frame, textvariable=self.default_max_results_var, width=15)
        max_results_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        self.default_check_core_var = tk.BooleanVar()
        ttk.Checkbutton(search_frame, text="默认启用核心期刊筛选", 
                       variable=self.default_check_core_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Label(search_frame, text="默认输出路径:").grid(row=5, column=0, sticky=tk.W, pady=5)
        
        # 输出路径选择框
        output_path_frame = ttk.Frame(search_frame)
        output_path_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        self.default_output_path_var = tk.StringVar()
        output_path_entry = ttk.Entry(output_path_frame, textvariable=self.default_output_path_var, state="readonly")
        output_path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        browse_output_button = ttk.Button(output_path_frame, text="📁 浏览", command=self.browse_default_output_folder)
        browse_output_button.grid(row=0, column=1)
        
        output_path_frame.columnconfigure(0, weight=1)
        
        # AI设置
        ai_frame = ttk.LabelFrame(content_frame, text="AI模型设置", padding=15)
        ai_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(ai_frame, text="默认AI模型:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.default_ai_model_var = tk.StringVar()
        ai_model_entry = ttk.Entry(ai_frame, textvariable=self.default_ai_model_var, width=30)
        ai_model_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        ttk.Label(ai_frame, text="Base URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.base_url_var = tk.StringVar()
        base_url_entry = ttk.Entry(ai_frame, textvariable=self.base_url_var, width=50)
        base_url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        ttk.Label(ai_frame, text="API密钥:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(ai_frame, textvariable=self.api_key_var, show="*", width=40)
        api_key_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        ttk.Label(ai_frame, text="Temperature:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.temperature_var = tk.StringVar()
        temperature_entry = ttk.Entry(ai_frame, textvariable=self.temperature_var, width=15)
        temperature_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        ttk.Label(ai_frame, text="Top P:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.top_p_var = tk.StringVar()
        top_p_entry = ttk.Entry(ai_frame, textvariable=self.top_p_var, width=15)
        top_p_entry.grid(row=4, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 按钮区域
        button_frame = ttk.Frame(content_frame)
        button_frame.grid(row=4, column=0, pady=20)
        
        ttk.Button(button_frame, text="💾 保存配置", 
                  command=self.save_config).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="🔄 重置为默认", 
                  command=self.reset_to_default).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="📁 导入配置", 
                  command=self.import_config).grid(row=0, column=3, padx=(0, 10))
        ttk.Button(button_frame, text="📤 导出配置", 
                  command=self.export_config).grid(row=0, column=4)
        
        # 配置网格权重
        content_frame.columnconfigure(0, weight=1)
        search_frame.columnconfigure(1, weight=1)
        ai_frame.columnconfigure(1, weight=1)
        
        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def load_current_config(self):
        """加载当前配置"""
        try:
            # 重新加载配置文件以获取最新的配置
            self.config_manager.reload_config()
            config = self.config_manager.get_default_settings()
            
            # 加载搜索设置
            self.default_keyword_var.set(config.get('keyword', ''))
            
            # 处理时间范围设置
            start_year = config.get('start_year')
            end_year = config.get('end_year')
            
            # 直接显示配置文件中的年份值，不管time_range设置
            if start_year is not None:
                self.default_start_year_var.set(str(start_year))
            else:
                self.default_start_year_var.set('')
                
            if end_year is not None:
                self.default_end_year_var.set(str(end_year))
            else:
                self.default_end_year_var.set('')
            
            self.default_max_results_var.set(str(config.get('max_results', 60)))
            self.default_check_core_var.set(config.get('check_core', False))
            
            # 加载输出路径设置
            self.default_output_path_var.set(config.get('output_path', os.path.join(os.getcwd(), "data")))
            
            # 加载AI设置
            self.default_ai_model_var.set(config.get('ai_model', 'glm-4.5-flash'))
            self.base_url_var.set(config.get('base_url', 'https://open.bigmodel.cn/api/paas/v4/'))
            self.api_key_var.set(config.get('api_key', ''))
            self.temperature_var.set(str(config.get('temperature', 0.6)))
            self.top_p_var.set(str(config.get('top_p', 0.9)))
            
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {str(e)}")
    
    def browse_default_output_folder(self):
        """浏览默认输出文件夹"""
        folder = filedialog.askdirectory(initialdir=self.default_output_path_var.get())
        if folder:
            self.default_output_path_var.set(folder)
    
    def refresh_config(self):
        """刷新配置显示"""
        self.load_current_config()
    
    def save_config(self):
        """保存配置"""
        try:
            # 处理年份值，空字符串转换为None或保持为空字符串
            start_year = self.default_start_year_var.get().strip()
            end_year = self.default_end_year_var.get().strip()
            
            # 根据年份设置判断time_range
            if not start_year and not end_year:
                # 如果年份都为空，默认使用最近一年
                time_range = "recent_year"
            else:
                # 如果设置了年份，使用自定义范围
                time_range = "custom"
            
            config = {
                'keyword': self.default_keyword_var.get().strip(),
                'time_range': time_range,
                'start_year': start_year if start_year else "",
                'end_year': end_year if end_year else "",
                'max_results': int(self.default_max_results_var.get() or 60),
                'check_core': self.default_check_core_var.get(),
                'output_path': self.default_output_path_var.get() or os.path.join(os.getcwd(), "data"),  # 使用界面上的输出路径
                'ai_model': self.default_ai_model_var.get().strip() or "glm-4.5-flash",
                'base_url': self.base_url_var.get().strip() or "https://open.bigmodel.cn/api/paas/v4/",
                'api_key': self.api_key_var.get().strip(),
                'temperature': float(self.temperature_var.get().strip() or 0.6),
                'top_p': float(self.top_p_var.get().strip() or 0.9)
            }
            
            success = self.config_manager.update_default_settings(**config)
            
            if success:
                messagebox.showinfo("成功", "配置已保存！")
            else:
                messagebox.showerror("错误", "保存配置失败！")
                
        except ValueError as e:
            messagebox.showerror("错误", f"配置值无效: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
    
    def reset_to_default(self):
        """重置为默认配置"""
        if messagebox.askyesno("确认", "确定要重置为默认配置吗？"):
            try:
                # 重置配置文件
                self.config_manager.reset_to_default()
                # 重新加载界面
                self.load_current_config()
                messagebox.showinfo("成功", "已重置为默认配置！")
            except Exception as e:
                messagebox.showerror("错误", f"重置配置失败: {str(e)}")
    
    def import_config(self):
        """导入配置文件"""
        file = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 更新界面
                self.default_keyword_var.set(config.get('keyword', ''))
                self.default_start_year_var.set(config.get('start_year', '2024'))
                self.default_end_year_var.set(config.get('end_year', '2025'))
                self.default_max_results_var.set(str(config.get('max_results', 60)))
                self.default_check_core_var.set(config.get('check_core', False))
                self.default_ai_model_var.set(config.get('ai_model', 'glm-4.5-flash'))
                self.base_url_var.set(config.get('base_url', 'https://open.bigmodel.cn/api/paas/v4/'))
                self.api_key_var.set(config.get('api_key', ''))
                self.temperature_var.set(str(config.get('temperature', 0.6)))
                self.top_p_var.set(str(config.get('top_p', 0.9)))
                
                # 直接保存配置到文件，不显示额外提示
                try:
                    # 处理年份值，空字符串转换为None或保持为空字符串
                    start_year = self.default_start_year_var.get().strip()
                    end_year = self.default_end_year_var.get().strip()
                    
                    # 根据年份设置判断time_range
                    if not start_year and not end_year:
                        # 如果年份都为空，默认使用最近一年
                        time_range = "recent_year"
                    else:
                        # 如果设置了年份，使用自定义范围
                        time_range = "custom"
                    
                    config_to_save = {
                        'keyword': self.default_keyword_var.get().strip(),
                        'time_range': time_range,
                        'start_year': start_year if start_year else "",
                        'end_year': end_year if end_year else "",
                        'max_results': int(self.default_max_results_var.get() or 60),
                        'check_core': self.default_check_core_var.get(),
                        'ai_model': self.default_ai_model_var.get().strip() or "glm-4.5-flash",
                        'base_url': self.base_url_var.get().strip() or "https://open.bigmodel.cn/api/paas/v4/",
                        'api_key': self.api_key_var.get().strip(),
                        'temperature': float(self.temperature_var.get().strip() or 0.6),
                        'top_p': float(self.top_p_var.get().strip() or 0.9),
                        'output_path': self.default_output_path_var.get() or os.path.join(os.getcwd(), "data")  # 使用界面上的输出路径
                    }
                    
                    success = self.config_manager.update_default_settings(**config_to_save)
                    
                    if success:
                        messagebox.showinfo("成功", "配置已导入并保存！")
                    else:
                        messagebox.showerror("错误", "导入配置成功，但保存到文件失败！")
                        
                except ValueError as e:
                    messagebox.showerror("错误", f"配置值无效: {str(e)}")
                
            except Exception as e:
                messagebox.showerror("错误", f"导入配置失败: {str(e)}")
    
    def export_config(self):
        """导出配置文件"""
        file = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file:
            try:
                # 处理年份值，空字符串转换为None或保持为空字符串
                start_year = self.default_start_year_var.get().strip()
                end_year = self.default_end_year_var.get().strip()
                
                # 根据年份设置判断time_range
                if not start_year and not end_year:
                    # 如果年份都为空，默认使用最近一年
                    time_range = "recent_year"
                else:
                    # 如果设置了年份，使用自定义范围
                    time_range = "custom"
                
                config = {
                    'keyword': self.default_keyword_var.get().strip(),
                    'time_range': time_range,
                    'start_year': start_year if start_year else "",
                    'end_year': end_year if end_year else "",
                    'max_results': int(self.default_max_results_var.get() or 60),
                    'check_core': self.default_check_core_var.get(),
                    'output_path': self.default_output_path_var.get() or os.path.join(os.getcwd(), "data"),  # 使用界面上的输出路径
                    'ai_model': self.default_ai_model_var.get().strip() or "glm-4.5-flash",
                    'base_url': self.base_url_var.get().strip() or "https://open.bigmodel.cn/api/paas/v4/",
                    'api_key': self.api_key_var.get().strip(),
                    'temperature': float(self.temperature_var.get().strip() or 0.6),
                    'top_p': float(self.top_p_var.get().strip() or 0.9)
                }
                
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("成功", f"配置已导出到: {file}")
                
            except Exception as e:
                messagebox.showerror("错误", f"导出配置失败: {str(e)}")
