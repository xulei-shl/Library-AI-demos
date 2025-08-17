import tkinter as tk
from tkinter import ttk, messagebox
import threading
from .step1_gui import Step1GUI
from .step2_gui import Step2GUI
from .step3_gui import Step3GUI
from .step4_gui import Step4GUI
from .step5_gui import Step5GUI
from .config_gui import ConfigGUI
from .prompt_gui import PromptGUI
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_manager import ConfigManager

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CNKI 学术文献爬虫工具")
        self.root.geometry("835x700")
        
        # 创建主框架
        self.setup_main_frame()
        
        # 初始化各个步骤的GUI
        self.init_step_guis()
        
        # 创建菜单栏
        self.create_menu()
        
    def setup_main_frame(self):
        """设置主框架"""
        # 创建笔记本控件（标签页）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def init_step_guis(self):
        """初始化各个步骤的GUI"""
        # 创建配置管理器实例
        self.config_manager = ConfigManager()
        
        # 步骤1：搜索条件生成
        self.step1_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.step1_frame, text="S1: 搜索条件生成")
        self.step1_gui = Step1GUI(self.step1_frame)
        
        # 步骤2：数据爬取
        self.step2_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.step2_frame, text="S2: 数据爬取")
        self.step2_gui = Step2GUI(self.step2_frame)
        
        # 步骤3：Excel合并
        self.step3_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.step3_frame, text="S3: Excel合并")
        self.step3_gui = Step3GUI(self.step3_frame)
        
        # 步骤4：数据分析
        self.step4_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.step4_frame, text="S4: 相关性分析")
        self.step4_gui = Step4GUI(self.step4_frame, self.config_manager)
        
        # 步骤5：PDF下载
        self.step5_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.step5_frame, text="S5: PDF下载")
        self.step5_gui = Step5GUI(self.step5_frame)
        
        # 配置管理
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="配置管理")
        self.config_gui = ConfigGUI(self.config_frame)
        
        # 提示词管理
        self.prompt_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.prompt_frame, text="提示词管理")
        self.prompt_gui = PromptGUI(self.prompt_frame)
        
        # 绑定标签页切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 设置配置刷新回调
        self.step2_gui.set_config_refresh_callback(self.refresh_config_gui)
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导入配置", command=self.config_gui.import_config)
        file_menu.add_command(label="保存配置", command=self.config_gui.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="打开数据目录", command=self.open_data_directory)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        
    def open_data_directory(self):
        """打开数据目录"""
        try:
            import subprocess
            import platform
            import os
            from config_manager import ConfigManager
            
            # 尝试从配置中获取用户设置的输出路径
            config_manager = ConfigManager()
            output_path = config_manager.get_setting("default_settings", "output_path")
            
            # 如果配置中没有输出路径，则使用S2 GUI中的当前设置
            if not output_path and hasattr(self, 'step2_gui') and hasattr(self.step2_gui, 'output_path_var'):
                output_path = self.step2_gui.output_path_var.get()
            
            # 如果仍然没有路径，使用默认路径
            if not output_path:
                output_path = os.path.join(os.getcwd(), "data")
            
            # 打印调试信息
            print(f"配置中的输出路径: {config_manager.get_setting('default_settings', 'output_path')}")
            print(f"最终使用的路径: {output_path}")
            
            # 确保目录存在
            if not os.path.exists(output_path):
                os.makedirs(output_path)
                print(f"创建目录: {output_path}")
            
            # 根据操作系统打开目录
            if platform.system() == "Windows":
                subprocess.run(["explorer", output_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_path])
            else:  # Linux
                subprocess.run(["xdg-open", output_path])
                
        except Exception as e:
            messagebox.showerror("错误", f"打开数据目录失败: {str(e)}")
    
    def show_help(self):
        """显示帮助信息"""
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("600x400")
        
        help_text = """
CNKI 学术文献爬虫工具使用说明

步骤1: 搜索条件生成
- 输入关键词和搜索参数
- 生成搜索URL

步骤2: 数据爬取
- 使用生成的URL爬取数据
- 支持批量爬取和断点续传
- 实时查看爬取日志

步骤3: Excel合并
- 合并多个Excel文件
- 去重和数据清理

步骤4: 数据分析
- 生成统计图表
- 数据可视化分析

步骤5: PDF下载
- 批量下载PDF文件
- 支持多线程下载
- 实时查看下载日志

配置管理:
- 管理爬虫参数
- 保存和加载配置

注意: 各功能页面都有独立的日志显示和保存功能
        """
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        
    def show_about(self):
        """显示关于信息"""
        tk.messagebox.showinfo("关于", "CNKI 学术文献爬虫工具 v1.0\n\n一个用于爬取CNKI学术文献的工具")
    
    def on_tab_changed(self, event):
        """标签页切换事件处理"""
        selected_tab = event.widget.tab('current')['text']
        if selected_tab == "配置管理":
            # 当切换到配置管理页面时，刷新配置显示
            self.config_gui.refresh_config()
    
    def refresh_config_gui(self):
        """刷新配置管理界面"""
        self.config_gui.refresh_config()
        
    def run(self):
        """运行主窗口"""
        self.root.mainloop()
