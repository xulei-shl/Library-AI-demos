import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from typing import Optional, List, Dict, Any
import logging
from modules.prompt_generator import OptimizedPromptGenerator
from modules.config_manager import ConfigManager
from modules.prompt_manager import PromptManager
# 导入后台处理模块（这些模块已创建）
try:
    from modules.excel_processor import ExcelProcessor
    from modules.llm_batch_processor import LLMBatchProcessor
    from modules.task_scheduler import TaskScheduler
except ImportError as e:
    print(f"导入后台模块失败: {e}")
    # 创建占位符类以避免运行时错误
    class ExcelProcessor:
        def get_file_info(self, file_path): return {'sheet_count': 0, 'row_count': 0}
    class LLMBatchProcessor:
        def process_excel_batch(self, **kwargs): pass
    class TaskScheduler:
        pass

class LLMProcessingTab:
    """大模型处理Tab - 实现Excel数据的批量AI处理功能"""
    
    def __init__(self, parent_notebook, shared_data=None):
        self.parent_notebook = parent_notebook
        self.shared_data = shared_data or {}
        
        # 初始化核心组件（复用现有架构）
        self.config_manager = ConfigManager()
        self.prompt_manager = PromptManager()
        self.prompt_generator = OptimizedPromptGenerator()
        
        # 新增组件
        self.excel_processor = ExcelProcessor()
        self.batch_processor = LLMBatchProcessor()
        self.task_scheduler = TaskScheduler()
        
        # 状态管理
        self.is_processing = False
        self.is_paused = False
        self.current_task = None
        
        # 优雅停止相关状态
        self.pending_stop = False      # 待停止标志
        self.pending_pause = False     # 待暂停标志
        self.current_processing_row = None  # 当前处理的行号
        
        # 创建主框架 - parent_notebook 实际上是已经创建好的 frame
        self.frame = parent_notebook
        
        # 初始化UI
        self._setup_ui()
        self._load_config_options()
        self._setup_logging()
        
    def _setup_ui(self):
        """设置UI界面 - 左右分栏布局（左 75% / 右 25%）"""
        # 主容器 - 水平分割
        self.main_paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧控制面板 (75 %)
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=10)
        
        # 右侧日志面板 (25 %)
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=6)
        
        # 设置左右面板内容
        self._setup_left_panel()
        self._setup_right_panel()
        
    def set_paned_position(self):
        """设置PanedWindow的分割位置 - 强制左侧占75%"""
        try:
            if hasattr(self, 'main_paned'):
                # 获取总宽度
                self.frame.update_idletasks()
                total_width = self.main_paned.winfo_width()
                if total_width > 1:
                    # 设置左侧占75%的位置
                    left_width = int(total_width * 0.5)
                    self.main_paned.sashpos(0, left_width)
                    # print(f"🔧 LLM处理Tab: 设置PanedWindow位置 - 总宽度: {total_width}, 左侧宽度: {left_width}")
        except Exception as e:
            print(f"❌ 设置LLM处理Tab PanedWindow位置失败: {e}")
        
    def _setup_left_panel(self):
        """设置左侧控制面板"""
        # 创建滚动区域
        canvas = tk.Canvas(self.left_frame)
        scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 配置滚动区域的列权重
        scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # 1. Excel文件上传组件
        file_frame = self._create_file_upload_section(scrollable_frame)
        file_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # 2. 数据列选择组件
        column_frame = self._create_column_selection_section(scrollable_frame)
        column_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        # 3. 生成配置组件（复用现有逻辑）
        config_frame = self._create_generation_config_section(scrollable_frame)
        config_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        # 4. 操作按钮组件
        button_frame = self._create_operation_buttons_section(scrollable_frame)
        button_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        
    def _create_file_upload_section(self, parent):
        """创建Excel文件上传组件"""
        # 文件上传区域
        file_frame = ttk.LabelFrame(parent, text="Excel文件选择", padding=10)
        
        # 配置列权重 - 标签列不扩展，输入框列扩展
        file_frame.grid_columnconfigure(1, weight=1)
        
        # 文件路径显示
        ttk.Label(file_frame, text="文件路径:").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.file_path_var = tk.StringVar()
        self.file_path_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly")
        self.file_path_entry.grid(row=0, column=1, sticky="ew", pady=(0, 5))
        
        # 按钮区域
        button_frame = ttk.Frame(file_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        # 从Excel上传Tab获取路径按钮
        self.get_default_btn = ttk.Button(
            button_frame, 
            text="获取默认路径", 
            command=self._get_default_excel_path
        )
        self.get_default_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 手动选择文件按钮
        self.select_file_btn = ttk.Button(
            button_frame, 
            text="选择文件", 
            command=self._select_excel_file
        )
        self.select_file_btn.pack(side=tk.LEFT)
        
        # 文件信息显示
        self.file_info_var = tk.StringVar(value="未选择文件")
        self.file_info_label = ttk.Label(file_frame, textvariable=self.file_info_var, foreground="gray")
        self.file_info_label.grid(row=2, column=0, columnspan=2, sticky="w")
        
        return file_frame
        
    def _create_column_selection_section(self, parent):
        """创建数据列选择组件"""
        column_frame = ttk.LabelFrame(parent, text="数据列选择", padding=10)
        
        # 配置列权重
        column_frame.grid_columnconfigure(0, weight=1)
        
        # 说明文本
        info_label = ttk.Label(
            column_frame, 
            text="请输入要处理的列名，支持中英文逗号分隔（如：A,B,C 或 A，B，C）",
            foreground="gray"
        )
        info_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # 列选择输入框
        self.columns_var = tk.StringVar()
        self.columns_entry = ttk.Entry(column_frame, textvariable=self.columns_var)
        self.columns_entry.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.columns_entry.bind('<KeyRelease>', self._on_columns_change)
        
        # 预览区域
        preview_frame = ttk.Frame(column_frame)
        preview_frame.grid(row=2, column=0, sticky="ew")
        
        ttk.Label(preview_frame, text="选中的列:").pack(anchor=tk.W)
        self.columns_preview_var = tk.StringVar(value="无")
        self.columns_preview_label = ttk.Label(
            preview_frame, 
            textvariable=self.columns_preview_var, 
            foreground="blue"
        )
        self.columns_preview_label.pack(anchor=tk.W, pady=(2, 0))
        
        return column_frame
        
    def _create_generation_config_section(self, parent):
        """创建生成配置组件（完全复用现有逻辑）"""
        config_frame = ttk.LabelFrame(parent, text="生成配置", padding=10)
        
        # 配置列权重 - 标签列不扩展，输入框列扩展
        config_frame.grid_columnconfigure(1, weight=1)
        
        # 大模型选择（复用现有逻辑）
        ttk.Label(config_frame, text="大模型:").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(config_frame, textvariable=self.model_var, state="readonly")
        self.model_combo.grid(row=0, column=1, sticky="ew", pady=(0, 5))
        
        # 提示词选择（复用现有逻辑）
        ttk.Label(config_frame, text="提示词:").grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.prompt_var = tk.StringVar()
        self.prompt_combo = ttk.Combobox(config_frame, textvariable=self.prompt_var, state="readonly")
        self.prompt_combo.grid(row=1, column=1, sticky="ew", pady=(0, 5))
        
        # 参数设置（复用现有逻辑）
        params_frame = ttk.Frame(config_frame)
        params_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        
        # Temperature设置
        ttk.Label(params_frame, text="Temperature (0.0-1.0):").grid(row=0, column=0, sticky="w", pady=(0, 3))
        self.temperature_var = tk.StringVar(value="0.3")
        temp_entry = ttk.Entry(params_frame, textvariable=self.temperature_var, width=10)
        temp_entry.grid(row=0, column=1, sticky="e", pady=(0, 3))
        
        # Top-p设置
        ttk.Label(params_frame, text="Top-p (0.0-1.0):").grid(row=1, column=0, sticky="w")
        self.top_p_var = tk.StringVar(value="0.9")
        top_p_entry = ttk.Entry(params_frame, textvariable=self.top_p_var, width=10)
        top_p_entry.grid(row=1, column=1, sticky="e")
        
        return config_frame
        
    def _create_operation_buttons_section(self, parent):
        """创建操作按钮组件"""
        button_frame = ttk.LabelFrame(parent, text="操作控制", padding=10)
        
        # 配置列权重
        button_frame.grid_columnconfigure(0, weight=1)
        
        # 第一行按钮
        row1_frame = ttk.Frame(button_frame)
        row1_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        self.start_btn = ttk.Button(
            row1_frame, 
            text="开始处理", 
            command=self._start_processing,
            style="Accent.TButton"
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.pause_btn = ttk.Button(
            row1_frame, 
            text="暂停", 
            command=self._pause_processing,
            state=tk.DISABLED
        )
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(
            row1_frame, 
            text="停止", 
            command=self._stop_processing,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT)
        
        # 第二行按钮
        row2_frame = ttk.Frame(button_frame)
        row2_frame.grid(row=1, column=0, sticky="ew")
        
        self.clear_btn = ttk.Button(
            row2_frame, 
            text="清空日志", 
            command=self._clear_logs
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.reset_btn = ttk.Button(
            row2_frame, 
            text="重置状态", 
            command=self._reset_all_states
        )
        self.reset_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_log_btn = ttk.Button(
            row2_frame, 
            text="导出日志", 
            command=self._export_logs
        )
        self.export_log_btn.pack(side=tk.LEFT)
        
        return button_frame
        
    def _setup_right_panel(self):
        """设置右侧日志面板"""
        # 进度显示区域
        progress_frame = ttk.LabelFrame(self.right_frame, text="处理进度", padding=10)
        progress_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # 总体进度条
        progress_info_frame = ttk.Frame(progress_frame)
        progress_info_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(progress_info_frame, text="总体进度:").pack(side=tk.LEFT)
        self.progress_text_var = tk.StringVar(value="0/0 (0%)")
        ttk.Label(progress_info_frame, textvariable=self.progress_text_var).pack(side=tk.RIGHT)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # 统计信息
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill=tk.X)
        
        # 左列统计
        left_stats = ttk.Frame(stats_frame)
        left_stats.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.processed_var = tk.StringVar(value="已处理: 0")
        ttk.Label(left_stats, textvariable=self.processed_var).pack(anchor=tk.W)
        
        self.success_var = tk.StringVar(value="成功: 0")
        ttk.Label(left_stats, textvariable=self.success_var, foreground="green").pack(anchor=tk.W)
        
        # 右列统计
        right_stats = ttk.Frame(stats_frame)
        right_stats.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        self.failed_var = tk.StringVar(value="失败: 0")
        ttk.Label(right_stats, textvariable=self.failed_var, foreground="red").pack(anchor=tk.E)
        
        self.speed_var = tk.StringVar(value="速度: 0/min")
        ttk.Label(right_stats, textvariable=self.speed_var).pack(anchor=tk.E)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(self.right_frame, text="实时日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建日志文本区域
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        # 日志文本框和滚动条
        self.log_text = tk.Text(
            log_container, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=("Consolas", 9)
        )
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
        
        # 配置日志颜色标签
        self.log_text.tag_configure("INFO", foreground="black")
        self.log_text.tag_configure("WARNING", foreground="orange")
        self.log_text.tag_configure("ERROR", foreground="red")
        self.log_text.tag_configure("SUCCESS", foreground="green")
        
    def _load_config_options(self):
        """加载配置选项（完全复用现有逻辑）"""
        try:
            print("🔄 开始加载大模型处理配置选项...")
            
            # 加载大模型选项 - models 是 List[Dict[str, str]]
            models = self.config_manager.get_all_models()
            print(f"🤖 获取到 {len(models)} 个模型配置")
            
            if models:
                # 从模型列表中提取名称
                model_names = [model.get('name', '') for model in models if model.get('name')]
                self.model_combo['values'] = model_names
                if model_names:
                    self.model_var.set(model_names[0])
                print(f"🤖 模型选项: {model_names}")
            else:
                self.model_combo['values'] = []
                self._log_message("未找到可用的大模型配置", "WARNING")
            
            # 加载提示词选项 - prompts 是 List[Dict[str, Any]]
            prompts = self.prompt_manager.get_all_prompts()
            print(f"📝 获取到 {len(prompts)} 个提示词")
            
            if prompts:
                # 从提示词列表中提取名称
                prompt_names = [prompt.get('name', '') for prompt in prompts if prompt.get('name')]
                self.prompt_combo['values'] = prompt_names
                if prompt_names:
                    self.prompt_var.set(prompt_names[0])
                print(f"📝 提示词选项: {prompt_names}")
            else:
                self.prompt_combo['values'] = []
                self._log_message("未找到可用的提示词配置", "WARNING")
            
            print("✅ 大模型处理配置选项加载完成")
                
        except Exception as e:
            print(f"❌ 加载配置选项失败：{e}")
            import traceback
            traceback.print_exc()
            self._log_message(f"加载配置选项失败: {str(e)}", "ERROR")
    
    def refresh_config_options(self):
        """刷新配置选项（供外部调用）"""
        try:
            print("🔄 开始刷新大模型处理配置选项...")
            
            # 保存当前选中的值
            current_prompt = self.prompt_var.get()
            current_model = self.model_var.get()
            print(f"📝 当前选中 - 提示词: {current_prompt}, 模型: {current_model}")
            
            # 强制重新初始化配置管理器和提示词管理器
            try:
                print("🔄 重新初始化配置管理器...")
                self.config_manager.reload_config()
                print("🔄 重新初始化提示词管理器...")
                self.prompt_manager.reload_prompts()
            except Exception as reload_error:
                print(f"⚠️ 重新加载配置时出现错误: {reload_error}")
            
            # 重新加载配置选项
            self._load_config_options()
            print("✅ 大模型处理配置选项重新加载完成")
            
            # 尝试恢复之前的选择
            prompt_values = list(self.prompt_combo['values'])
            model_values = list(self.model_combo['values'])
            
            if current_prompt in prompt_values:
                self.prompt_var.set(current_prompt)
                print(f"✅ 恢复提示词选择: {current_prompt}")
            else:
                print(f"⚠️ 原提示词 '{current_prompt}' 不存在，使用默认值")
            
            if current_model in model_values:
                self.model_var.set(current_model)
                print(f"✅ 恢复模型选择: {current_model}")
            else:
                print(f"⚠️ 原模型 '{current_model}' 不存在，使用默认值")
            
            # 强制更新UI显示
            self.prompt_combo.update()
            self.model_combo.update()
            print("✅ UI更新完成")
                
            print("✅ 大模型处理配置选项刷新完成")
                
        except Exception as e:
            print(f"❌ 刷新大模型处理配置选项失败：{e}")
            import traceback
            traceback.print_exc()
            
    def _setup_logging(self):
        """设置日志系统"""
        self.logger = logging.getLogger("LLMProcessing")
        self.logger.setLevel(logging.INFO)
        
        # 创建自定义处理器，将日志输出到UI
        class UILogHandler(logging.Handler):
            def __init__(self, ui_callback):
                super().__init__()
                self.ui_callback = ui_callback
                
            def emit(self, record):
                msg = self.format(record)
                level = record.levelname
                self.ui_callback(msg, level)
        
        ui_handler = UILogHandler(self._log_message)
        ui_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S'))
        self.logger.addHandler(ui_handler)
        
    def _get_default_excel_path(self):
        """从multi_excel_selections.json文件获取默认路径"""
        try:
            excel_path_str = None
            
            # 优先从multi_excel_selections.json文件中获取第一个Excel文件路径
            try:
                import json
                from pathlib import Path
                selections_file = Path("logs/multi_excel_selections.json")
                if selections_file.exists():
                    with open(selections_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 获取selections数组中第一个文件的路径
                    if 'selections' in data and len(data['selections']) > 0:
                        excel_path_str = data['selections'][0]['file_path']
                        if excel_path_str and os.path.exists(excel_path_str):
                            self._log_message(f"从multi_excel_selections.json获取到Excel路径: {excel_path_str}", "INFO")
                        else:
                            self._log_message(f"文件路径不存在: {excel_path_str}", "WARNING")
                            excel_path_str = None
                    else:
                        self._log_message("multi_excel_selections.json中没有找到文件选择记录", "WARNING")
                else:
                    self._log_message("multi_excel_selections.json文件不存在", "WARNING")
            except Exception as e:
                self._log_message(f"从multi_excel_selections.json读取路径失败: {str(e)}", "WARNING")
            
            # 如果主要方案失败，尝试从临时文件读取Excel路径（备用方案）
            if not excel_path_str:
                try:
                    path_file = os.path.join("logs", "excel_path.txt")
                    if os.path.exists(path_file):
                        with open(path_file, 'r', encoding='utf-8') as f:
                            excel_path_str = f.read().strip()
                        self._log_message(f"从临时文件读取到Excel路径: {excel_path_str}", "INFO")
                except Exception as e:
                    self._log_message(f"从临时文件读取路径失败: {str(e)}", "WARNING")
            
            # 如果临时文件中没有路径，尝试从共享数据获取（备用方案）
            if not excel_path_str:
                if self.shared_data and 'excel_path' in self.shared_data:
                    excel_path = self.shared_data['excel_path']
                    
                    # 类型检查：确保excel_path是字符串类型
                    if not isinstance(excel_path, (str, bytes, os.PathLike)):
                        self._log_message(f"Excel路径类型错误: 期望字符串，实际类型为 {type(excel_path)}", "ERROR")
                        messagebox.showerror("错误", f"Excel路径数据类型错误，请重新选择文件")
                        return
                    
                    # 转换为字符串（如果是bytes或PathLike）
                    excel_path_str = str(excel_path)
                    self._log_message(f"从共享数据读取到Excel路径: {excel_path_str}", "INFO")
            
            # 检查是否获取到路径
            if not excel_path_str or excel_path_str.strip() == "":
                self._log_message("未找到Excel路径", "INFO")
                messagebox.showinfo("提示", "未找到默认Excel路径，请先在Excel上传Tab中选择文件，或手动选择文件")
                return
            
            # 检查文件是否存在
            if os.path.exists(excel_path_str):
                self.file_path_var.set(excel_path_str)
                self._validate_excel_file(excel_path_str)
                self._log_message(f"已获取默认Excel路径: {excel_path_str}", "INFO")
            else:
                self._log_message(f"Excel文件不存在: {excel_path_str}", "WARNING")
                messagebox.showwarning("警告", f"Excel文件不存在或已被移动: {excel_path_str}")
                
        except Exception as e:
            self._log_message(f"获取默认路径失败: {str(e)}", "ERROR")
            messagebox.showerror("错误", f"获取默认Excel路径时发生错误: {str(e)}")
            
    def _select_excel_file(self):
        """手动选择Excel文件"""
        try:
            file_path = filedialog.askopenfilename(
                title="选择Excel文件",
                filetypes=[
                    ("Excel files", "*.xlsx *.xls"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                self.file_path_var.set(file_path)
                self._validate_excel_file(file_path)
                self._log_message(f"已选择Excel文件: {file_path}", "INFO")
                
        except Exception as e:
            self._log_message(f"选择文件失败: {str(e)}", "ERROR")
            
    def _validate_excel_file(self, file_path):
        """验证Excel文件"""
        try:
            if not os.path.exists(file_path):
                self.file_info_var.set("文件不存在")
                return False
                
            if not file_path.lower().endswith(('.xlsx', '.xls')):
                self.file_info_var.set("不是有效的Excel文件")
                return False
                
            # 尝试读取文件信息
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # 使用Excel处理器验证文件
            sheet_info = self.excel_processor.get_file_info(file_path)
            
            info_text = f"文件大小: {file_size_mb:.2f}MB, 工作表: {sheet_info['sheet_count']}, 数据行: {sheet_info['row_count']}"
            self.file_info_var.set(info_text)
            
            return True
            
        except Exception as e:
            self.file_info_var.set(f"文件验证失败: {str(e)}")
            return False
            
    def _on_columns_change(self, event=None):
        """列选择输入变化事件"""
        try:
            columns_text = self.columns_var.get().strip()
            if not columns_text:
                self.columns_preview_var.set("无")
                return
                
            # 处理中英文逗号分隔
            columns = []
            for col in columns_text.replace('，', ',').split(','):
                col = col.strip().upper()
                if col:
                    columns.append(col)
                    
            if columns:
                self.columns_preview_var.set(", ".join(columns))
            else:
                self.columns_preview_var.set("无")
                
        except Exception as e:
            self.columns_preview_var.set(f"格式错误: {str(e)}")
            
    def _validate_parameters(self):
        """验证参数（复用现有逻辑）"""
        try:
            # 验证文件
            file_path = self.file_path_var.get().strip()
            if not file_path:
                raise ValueError("请选择Excel文件")
                
            if not self._validate_excel_file(file_path):
                raise ValueError("Excel文件无效")
                
            # 验证列选择
            columns_text = self.columns_var.get().strip()
            if not columns_text:
                raise ValueError("请输入要处理的列")
                
            # 验证模型和提示词
            if not self.model_var.get():
                raise ValueError("请选择大模型")
                
            if not self.prompt_var.get():
                raise ValueError("请选择提示词")
                
            # 验证参数范围（复用现有逻辑）
            try:
                temperature = float(self.temperature_var.get())
                if not 0.0 <= temperature <= 1.0:
                    raise ValueError("Temperature必须在0.0-1.0之间")
            except ValueError:
                raise ValueError("Temperature格式错误")
                
            try:
                top_p = float(self.top_p_var.get())
                if not 0.0 <= top_p <= 1.0:
                    raise ValueError("Top-p必须在0.0-1.0之间")
            except ValueError:
                raise ValueError("Top-p格式错误")
                
            return True
            
        except ValueError as e:
            messagebox.showerror("参数错误", str(e))
            return False
            
    def _start_processing(self):
        """开始处理"""
        if not self._validate_parameters():
            return
            
        try:
            # 更新UI状态
            self.is_processing = True
            self.is_paused = False
            self._update_button_states()
            
            # 清空统计信息
            self._reset_statistics()
            
            # 启动异步处理任务
            self.current_task = threading.Thread(target=self._process_excel_async, daemon=True)
            self.current_task.start()
            
            self._log_message("开始处理Excel数据...", "INFO")
            
        except Exception as e:
            self._log_message(f"启动处理失败: {str(e)}", "ERROR")
            self.is_processing = False
            self._update_button_states()
            
    def _pause_processing(self):
        """暂停/继续处理"""
        if self.is_processing:
            if not self.is_paused:
                # 请求暂停
                self.pending_pause = True
                self.pause_btn.config(text="暂停中...", state=tk.DISABLED)
                self._log_message("等待当前处理完成后暂停...", "WARNING")
            else:
                # 继续处理
                self.is_paused = False
                self.pending_pause = False
                self.pause_btn.config(text="暂停", state=tk.NORMAL)
                self._log_message("处理已继续", "INFO")
                
    def _stop_processing(self):
        """停止处理"""
        if self.is_processing:
            self.pending_stop = True
            self.stop_btn.config(text="停止中...", state=tk.DISABLED)
            self._log_message("等待当前处理完成后停止...", "WARNING")
            
    def _clear_logs(self):
        """清空日志和重置所有状态（方案A：完整重置方案）"""
        try:
            # 1. 检查是否正在处理
            if self.is_processing:
                result = messagebox.askyesno(
                    "确认操作", 
                    "正在处理中，清空将停止当前处理并重置所有进度，是否继续？",
                    icon='warning'
                )
                if not result:
                    return
                
                # 强制停止当前处理
                self._force_stop_processing()
            
            # 2. 清空日志文本
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)
            
            # 3. 重置UI进度显示
            self._reset_statistics()
            
            # 4. 重置批量处理器状态
            if hasattr(self, 'batch_processor'):
                self.batch_processor.reset_stats()
            
            # 5. 重置内部状态变量
            self.is_processing = False
            self.is_paused = False
            self.pending_stop = False
            self.pending_pause = False
            self.current_processing_row = None
            
            # 6. 更新按钮状态
            self._update_button_states()
            
            # 7. 记录操作日志
            self._log_message("日志已清空，所有状态已重置", "INFO")
            
        except Exception as e:
            error_msg = f"清空日志失败: {str(e)}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def _force_stop_processing(self):
        """强制停止处理"""
        try:
            # 设置停止标志
            self.is_processing = False
            self.is_paused = False
            self.pending_stop = True
            
            # 如果批量处理器存在，强制停止
            if hasattr(self, 'batch_processor'):
                self.batch_processor.force_stop()
            
            # 等待处理线程结束（最多等待2秒）
            if hasattr(self, 'current_task') and self.current_task and self.current_task.is_alive():
                self.current_task.join(timeout=2.0)
                if self.current_task.is_alive():
                    self._log_message("处理线程未能及时停止，已强制重置状态", "WARNING")
            
            self._log_message("处理已强制停止", "WARNING")
            
        except Exception as e:
            self._log_message(f"强制停止处理时出错: {str(e)}", "ERROR")
        

    def _update_button_states(self):
        """更新按钮状态"""
        if self.is_processing:
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED, text="暂停")
            self.stop_btn.config(state=tk.DISABLED, text="停止")
            # 重置pending状态
            self.pending_stop = False
            self.pending_pause = False
            self.current_processing_row = None
            
    def _reset_statistics(self):
        """重置统计信息（优化版）"""
        try:
            # 重置进度条和进度文本
            self.progress_bar['value'] = 0
            self.progress_text_var.set("0/0 (0%)")
            
            # 重置统计变量
            self.processed_var.set("已处理: 0")
            self.success_var.set("成功: 0")
            self.failed_var.set("失败: 0")
            self.speed_var.set("速度: 0/min")
            
            # 重置内部跟踪变量
            if hasattr(self, '_last_total'):
                self._last_total = 0
            
            # 强制更新UI显示
            self.frame.update_idletasks()
            
        except Exception as e:
            print(f"重置统计信息失败: {e}")
        
    def _log_message(self, message, level="INFO"):
        """添加日志消息"""
        try:
            self.log_text.config(state=tk.NORMAL)
            
            # 添加时间戳和消息
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            full_message = f"[{timestamp}] {message}\n"
            
            # 插入消息并设置颜色
            self.log_text.insert(tk.END, full_message, level)
            
            # 自动滚动到底部
            self.log_text.see(tk.END)
            
            self.log_text.config(state=tk.DISABLED)
            
            # 更新UI
            self.frame.update_idletasks()
            
        except Exception as e:
            print(f"日志记录失败: {e}")
            
    def _process_excel_async(self):
        """异步处理Excel数据（主要业务逻辑）"""
        try:
            # 获取参数
            file_path = self.file_path_var.get().strip()
            columns_text = self.columns_var.get().strip()
            model_name = self.model_var.get()
            prompt_name = self.prompt_var.get()
            temperature = float(self.temperature_var.get())
            top_p = float(self.top_p_var.get())
            
            # 解析列名
            columns = []
            for col in columns_text.replace('，', ',').split(','):
                col = col.strip().upper()
                if col:
                    columns.append(col)
                    
            # 获取配置 - 参照 prompt_generator.py 中的逻辑
            model_config = None
            models = self.config_manager.get_all_models()
            for model in models:
                if model.get('name', '') == model_name:
                    model_config = model
                    break
            
            prompt_config = None
            prompts = self.prompt_manager.get_all_prompts()
            for prompt in prompts:
                if prompt.get('name', '') == prompt_name:
                    prompt_config = prompt
                    break
            
            if not model_config:
                raise ValueError(f"未找到模型配置: {model_name}")
            if not prompt_config:
                raise ValueError(f"未找到提示词配置: {prompt_name}")
                
            # 开始批量处理
            self.batch_processor.process_excel_batch(
                file_path=file_path,
                columns=columns,
                model_config=model_config,
                prompt_config=prompt_config,
                temperature=temperature,
                top_p=top_p,
                progress_callback=self._update_progress,
                log_callback=self._log_message,
                pause_check=lambda: self.is_paused,
                stop_check=lambda: not self.is_processing,
                current_row_callback=self._set_current_row,
                pending_stop_check=lambda: self.pending_stop,
                pending_pause_check=lambda: self.pending_pause,
                pause_confirmed_callback=self._confirm_pause,
                stop_confirmed_callback=self._confirm_stop
            )
            
            if self.is_processing:
                self._log_message("Excel数据处理完成！", "SUCCESS")
            else:
                self._log_message("处理已停止", "WARNING")
                
        except Exception as e:
            self._log_message(f"处理失败: {str(e)}", "ERROR")
        finally:
            self.is_processing = False
            self.is_paused = False
            # 在主线程中更新UI
            self.frame.after(0, self._update_button_states)
            
    def _update_progress(self, current, total, success, failed, speed):
        """更新进度信息（优化版）"""
        try:
            # 防止进度超过100%和处理异常情况
            if total > 0:
                # 确保进度不超过100%
                progress = min((current / total) * 100, 100.0)
                self.progress_bar['value'] = progress
                self.progress_text_var.set(f"{current}/{total} ({progress:.1f}%)")
                
                # 检测文件切换（新文件处理）
                if hasattr(self, '_last_total') and self._last_total != total and total > 0:
                    self._log_message(f"检测到新文件处理，总行数: {total}", "INFO")
                self._last_total = total
                
            else:
                # 处理total为0的情况
                self.progress_bar['value'] = 0
                self.progress_text_var.set("0/0 (0%)")
            
            # 更新统计信息
            self.processed_var.set(f"已处理: {current}")
            self.success_var.set(f"成功: {success}")
            self.failed_var.set(f"失败: {failed}")
            self.speed_var.set(f"速度: {speed:.1f}/min")
            
            # 添加异常数据检测和警告
            if current > total and total > 0:
                self._log_message(f"警告：处理数量({current})超过总数({total})，可能存在状态同步问题", "WARNING")
            
            # 更新UI
            self.frame.update_idletasks()
            
        except Exception as e:
            error_msg = f"更新进度失败: {e}"
            print(error_msg)
            self._log_message(error_msg, "ERROR")
            
    def _set_current_row(self, row_number):
        """设置当前处理行号"""
        self.current_processing_row = row_number
        
    def _confirm_pause(self):
        """确认暂停操作"""
        self.is_paused = True
        self.pending_pause = False
        self.frame.after(0, lambda: [
            self.pause_btn.config(text="继续", state=tk.NORMAL),
            self._log_message("处理已暂停", "WARNING")
        ])
        
    def _confirm_stop(self):
        """确认停止操作"""
        self.is_processing = False
        self.is_paused = False
        self.pending_stop = False
        self.frame.after(0, lambda: [
            self._update_button_states(),
            self._log_message("处理已停止", "WARNING")
        ])
    
    def _reset_all_states(self):
        """重置所有状态（不清空日志文本）"""
        try:
            # 检查是否正在处理
            if self.is_processing:
                result = messagebox.askyesno(
                    "确认操作", 
                    "正在处理中，重置将停止当前处理，是否继续？",
                    icon='warning'
                )
                if not result:
                    return
                
                # 强制停止当前处理
                self._force_stop_processing()
            
            # 重置UI进度显示
            self._reset_statistics()
            
            # 重置批量处理器状态
            if hasattr(self, 'batch_processor'):
                self.batch_processor.reset_stats()
            
            # 重置内部状态变量
            self.is_processing = False
            self.is_paused = False
            self.pending_stop = False
            self.pending_pause = False
            self.current_processing_row = None
            
            # 更新按钮状态
            self._update_button_states()
            
            # 记录操作
            self._log_message("所有处理状态已重置", "INFO")
            
        except Exception as e:
            error_msg = f"重置状态失败: {str(e)}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def _export_logs(self):
        """导出日志到文件"""
        try:
            # 获取日志内容
            log_content = self.log_text.get(1.0, tk.END).strip()
            
            if not log_content:
                messagebox.showinfo("提示", "当前没有日志内容可导出")
                return
            
            # 选择保存位置
            from tkinter import filedialog
            import datetime
            
            # 默认文件名包含时间戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"llm_processing_log_{timestamp}.txt"
            
            file_path = filedialog.asksaveasfilename(
                title="导出日志",
                defaultextension=".txt",
                initialname=default_filename,
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("所有文件", "*.*")
                ]
            )
            
            if file_path:
                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"LLM批量处理日志")
                    f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    f.write("=" * 50 + "")
                    f.write(log_content)
                
                self._log_message(f"日志已导出到: {file_path}", "SUCCESS")
                messagebox.showinfo("成功", f"日志已成功导出到:{file_path}")
            
        except Exception as e:
            error_msg = f"导出日志失败: {str(e)}"
            print(error_msg)
            messagebox.showerror("错误", error_msg)
            self._log_message(error_msg, "ERROR")