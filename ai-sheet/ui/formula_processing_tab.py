"""
公式处理Tab主UI界面
实现Excel公式处理功能的用户界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import time

try:
    from modules.formula_processor import FormulaProcessor, ProcessingConfig, ProcessingStatus, ErrorStrategy, ProgressInfo
    from modules.excel_formula_reader import ExcelFormulaReader
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from modules.formula_processor import FormulaProcessor, ProcessingConfig, ProcessingStatus, ErrorStrategy, ProgressInfo
    from modules.excel_formula_reader import ExcelFormulaReader

# 配置日志
logger = logging.getLogger(__name__)


class FormulaProcessingTab:
    """公式处理Tab主界面类"""
    
    def __init__(self, parent_notebook, shared_data=None):
        self.parent = parent_notebook
        self.shared_data = shared_data or {}
        self.config = self._load_config()
        
        # 核心组件
        self.processor = None
        self.excel_reader = ExcelFormulaReader()
        
        # UI变量
        self.file_path_var = tk.StringVar()
        self.formula_var = tk.StringVar()
        self.target_column_var = tk.StringVar()
        self.preview_rows_var = tk.IntVar(value=self.config['default_settings']['preview_rows'])
        self.error_strategy_var = tk.StringVar(value=self.config['default_settings']['error_strategy'])
        self.backup_enabled_var = tk.BooleanVar(value=self.config['default_settings']['backup_enabled'])
        self.overwrite_strategy_var = tk.StringVar(value="overwrite")
        self.batch_size_var = tk.IntVar(value=self.config['default_settings']['batch_size'])
        
        # 状态变量
        self.current_sheet_var = tk.StringVar()
        self.file_info_var = tk.StringVar(value="未选择文件")
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="就绪")
        
        # 处理状态
        self.is_processing = False
        self.processing_thread = None
        
        # 创建主框架
        self.main_frame = ttk.Frame(parent_notebook)
        self._create_ui()
        
        logger.info("公式处理Tab界面初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            config_path = Path("config/formula_config.json")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config['formula_processing']
            else:
                logger.warning("配置文件不存在，使用默认配置")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'default_settings': {
                'preview_rows': 10,
                'batch_size': 1000,
                'error_strategy': 'skip',
                'backup_enabled': True
            },
            'ui_settings': {
                'left_panel_width': 75,
                'right_panel_width': 25
            },

            'error_handling': {
                'strategies': [
                    {'value': 'skip', 'label': '跳过错误行'},
                    {'value': 'default', 'label': '使用默认值'},
                    {'value': 'stop', 'label': '停止处理'}
                ]
            }
        }
    
    def _create_ui(self):
        """创建用户界面"""
        # 创建主要的PanedWindow（左右分栏）
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧控制面板
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=3)
        
        # 右侧日志面板
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=1)
        
        # 创建左侧控制面板内容
        self._create_left_panel()
        
        # 创建右侧日志面板内容
        self._create_right_panel()
        
        # 初始化处理器
        self._initialize_processor()
    
    def _create_left_panel(self):
        """创建左侧控制面板"""
        # 创建滚动框架
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
        
        # 在scrollable_frame中创建各个组件
        self._create_file_upload_section(scrollable_frame)
        self._create_formula_input_section(scrollable_frame)
        self._create_target_column_section(scrollable_frame)
        self._create_processing_options_section(scrollable_frame)
        self._create_operation_buttons_section(scrollable_frame)
    
    def _create_file_upload_section(self, parent):
        """创建文件选择组件"""
        section_frame = ttk.LabelFrame(parent, text="📁 文件选择", padding=10)
        section_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 文件路径显示
        path_frame = ttk.Frame(section_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(path_frame, text="文件路径:").pack(anchor=tk.W)
        path_entry = ttk.Entry(path_frame, textvariable=self.file_path_var, state='readonly')
        path_entry.pack(fill=tk.X, pady=(2, 0))
        
        # 按钮框架
        button_frame = ttk.Frame(section_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="获取默认路径", 
                  command=self._get_default_path).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="选择文件", 
                  command=self._select_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="刷新信息", 
                  command=self._refresh_file_info).pack(side=tk.LEFT)
        
        # 文件信息显示
        info_frame = ttk.Frame(section_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(info_frame, text="文件信息:").pack(anchor=tk.W)
        self.file_info_label = ttk.Label(info_frame, textvariable=self.file_info_var, 
                                        foreground="blue", wraplength=400)
        self.file_info_label.pack(anchor=tk.W, pady=(2, 0))
        
        # 工作表选择
        sheet_frame = ttk.Frame(section_frame)
        sheet_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(sheet_frame, text="工作表:").pack(side=tk.LEFT)
        self.sheet_combobox = ttk.Combobox(sheet_frame, textvariable=self.current_sheet_var, 
                                          state='readonly', width=20)
        self.sheet_combobox.pack(side=tk.LEFT, padx=(5, 0))
    
    def _create_formula_input_section(self, parent):
        """创建公式输入组件"""
        section_frame = ttk.LabelFrame(parent, text="🧮 公式输入", padding=10)
        section_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 公式输入框
        formula_frame = ttk.Frame(section_frame)
        formula_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(formula_frame, text="公式内容:").pack(anchor=tk.W)
        self.formula_text = tk.Text(formula_frame, height=3, wrap=tk.WORD)
        self.formula_text.pack(fill=tk.X, pady=(2, 5))
        
        # 绑定文本变化事件
        self.formula_text.bind('<KeyRelease>', self._on_formula_changed)
        
        # 公式操作按钮
        formula_button_frame = ttk.Frame(section_frame)
        formula_button_frame.pack(fill=tk.X)
        
        ttk.Button(formula_button_frame, text="验证语法", 
                  command=self._validate_formula).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(formula_button_frame, text="清空公式", 
                  command=self._clear_formula).pack(side=tk.LEFT, padx=(0, 5))
        
        # 语法提示
        self.syntax_label = ttk.Label(section_frame, text="提示: 公式应以=开头，如 =SUM(A1:A10)", 
                                     foreground="gray", wraplength=400)
        self.syntax_label.pack(anchor=tk.W, pady=(5, 0))
    
    def _create_target_column_section(self, parent):
        """创建目标列配置组件"""
        section_frame = ttk.LabelFrame(parent, text="🎯 目标列配置", padding=10)
        section_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 目标列名
        column_frame = ttk.Frame(section_frame)
        column_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(column_frame, text="目标列名:").pack(side=tk.LEFT)
        column_entry = ttk.Entry(column_frame, textvariable=self.target_column_var, width=20)
        column_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Button(column_frame, text="检查列", 
                command=self._check_column_exists).pack(side=tk.LEFT, padx=(5, 0))
        
        # 覆盖策略
        strategy_frame = ttk.Frame(section_frame)
        strategy_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(strategy_frame, text="覆盖策略:").pack(side=tk.LEFT)
        strategy_combobox = ttk.Combobox(strategy_frame, textvariable=self.overwrite_strategy_var, 
                                        state='readonly', width=15)
        strategy_combobox['values'] = ('覆盖现有列', '新增列', '创建新工作表')
        strategy_combobox.pack(side=tk.LEFT, padx=(5, 0))
        
        # 设置默认显示值为中文
        self.overwrite_strategy_var.set('覆盖现有列')
        
        # 列状态显示
        self.column_status_label = ttk.Label(section_frame, text="", foreground="blue")
        self.column_status_label.pack(anchor=tk.W, pady=(5, 0))

    def _create_processing_options_section(self, parent):
        """创建处理选项组件"""
        section_frame = ttk.LabelFrame(parent, text="⚙️ 处理选项", padding=10)
        section_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 预处理行数
        preview_frame = ttk.Frame(section_frame)
        preview_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(preview_frame, text="预处理行数:").pack(side=tk.LEFT)
        preview_spinbox = ttk.Spinbox(preview_frame, from_=1, to=100, 
                                    textvariable=self.preview_rows_var, width=10)
        preview_spinbox.pack(side=tk.LEFT, padx=(5, 0))

        # 批处理大小（- 按钮 + 输入框 + + 按钮）
        batch_frame = ttk.Frame(section_frame)
        batch_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(batch_frame, text="批处理大小:").pack(side=tk.LEFT)

        # 减号按钮
        minus_btn = ttk.Button(batch_frame, text="-", width=3,
                               command=lambda: self._change_batch_size(-50))
        minus_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 只读输入框（显示用，禁止手工输入）
        batch_entry = ttk.Entry(batch_frame, textvariable=self.batch_size_var,
                                width=6, justify="center", state="readonly")
        batch_entry.pack(side=tk.LEFT, padx=3)

        # 加号按钮
        plus_btn = ttk.Button(batch_frame, text="+", width=3,
                              command=lambda: self._change_batch_size(50))
        plus_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 设置初始值
        self.batch_size_var.set(100)

        
        # 错误处理策略
        error_frame = ttk.Frame(section_frame)
        error_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(error_frame, text="错误处理:").pack(side=tk.LEFT)
        error_combobox = ttk.Combobox(error_frame, textvariable=self.error_strategy_var, 
                                    state='readonly', width=15)
        error_values = [strategy['label'] for strategy in self.config['error_handling']['strategies']]
        error_combobox['values'] = error_values
        error_combobox.pack(side=tk.LEFT, padx=(5, 0))
        
        # 设置默认显示值为中文
        self._set_default_error_strategy()
        
        # 备份选项
        backup_frame = ttk.Frame(section_frame)
        backup_frame.pack(fill=tk.X, pady=(5, 0))
        
        backup_check = ttk.Checkbutton(backup_frame, text="自动备份原文件", 
                                      variable=self.backup_enabled_var)
        backup_check.pack(side=tk.LEFT)
    
    def _set_default_error_strategy(self):
        """设置默认错误处理策略显示"""
        try:
            default_strategy = self.config['default_settings']['error_strategy']  # 这是英文值，如 'skip'
            
            # 查找对应的中文标签
            for strategy in self.config['error_handling']['strategies']:
                if strategy['value'] == default_strategy:
                    self.error_strategy_var.set(strategy['label'])  # 设置为中文标签
                    self._log_message("DEBUG", f"设置默认错误策略: {strategy['label']}")
                    return
            
            # 如果配置中没找到，使用备用映射
            english_to_chinese = {
                'skip': '跳过错误行',
                'default': '使用默认值',
                'stop': '停止处理'
            }
            
            chinese_label = english_to_chinese.get(default_strategy, '跳过错误行')
            self.error_strategy_var.set(chinese_label)
            self._log_message("DEBUG", f"使用备用映射设置错误策略: {chinese_label}")
            
        except Exception as e:
            self._log_message("ERROR", f"设置默认错误策略失败: {str(e)}")
            self.error_strategy_var.set('跳过错误行')  # 最终默认值
                
    def _change_batch_size(self, delta):
        """按 delta 步进调整批处理大小，最小值 50"""
        current = self.batch_size_var.get()
        new_val = max(50, current + delta)   # 如需上限再加个 min(...)
        self.batch_size_var.set(new_val)
        

    def _create_operation_buttons_section(self, parent):
        """创建操作按钮组件"""
        section_frame = ttk.LabelFrame(parent, text="🚀 操作控制", padding=10)
        section_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 主要操作按钮
        main_button_frame = ttk.Frame(section_frame)
        main_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.preview_button = ttk.Button(main_button_frame, text="🔍 预处理", 
                                        command=self._start_preview_processing)
        self.preview_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.process_button = ttk.Button(main_button_frame, text="⚡ 全量处理", 
                                        command=self._start_full_processing)
        self.process_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 控制按钮
        control_button_frame = ttk.Frame(section_frame)
        control_button_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.pause_button = ttk.Button(control_button_frame, text="⏸️ 暂停", 
                                      command=self._pause_processing, state='disabled')
        self.pause_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(control_button_frame, text="⏹️ 停止", 
                                     command=self._stop_processing, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_log_button = ttk.Button(control_button_frame, text="🗑️ 清空日志", 
                                          command=self._clear_log)
        self.clear_log_button.pack(side=tk.LEFT, padx=(0, 5))
    
    def _create_right_panel(self):
        """创建右侧日志面板"""
        # 进度显示区域
        self._create_progress_section(self.right_frame)
        
        # 实时日志区域
        self._create_log_section(self.right_frame)
    
    def _create_progress_section(self, parent):
        """创建进度显示区域"""
        progress_frame = ttk.LabelFrame(parent, text="📊 处理进度", padding=10)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 状态显示
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                     foreground="blue")
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 进度条
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=200)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        # 进度信息
        self.progress_info_label = ttk.Label(progress_frame, text="", 
                                            wraplength=200, justify=tk.LEFT)
        self.progress_info_label.pack(anchor=tk.W, pady=(5, 0))
    
    def _create_log_section(self, parent):
        """创建实时日志区域"""
        log_frame = ttk.LabelFrame(parent, text="📝 处理日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, 
                                                 state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志颜色
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("DEBUG", foreground="gray")
    
    def _initialize_processor(self):
        """初始化处理器"""
        try:
            # 将界面上的中文错误策略映射为英文值
            error_strategy_value = self._map_error_strategy_to_backend(self.error_strategy_var.get())
            
            config = ProcessingConfig(
                preview_rows=self.preview_rows_var.get(),
                batch_size=self.batch_size_var.get(),
                error_strategy=ErrorStrategy(error_strategy_value),  # 使用映射后的英文值
                backup_enabled=self.backup_enabled_var.get()
            )
            
            self.processor = FormulaProcessor(config)
            self.processor.set_progress_callback(self._on_progress_update)
            self.processor.set_log_callback(self._on_log_message)
            
            self._log_message("INFO", "公式处理器初始化成功")
            
        except Exception as e:
            self._log_message("ERROR", f"处理器初始化失败: {str(e)}")
    
    # 事件处理方法
    def _get_default_path(self):
        """获取默认文件路径（从multi_excel_selections.json文件）"""
        try:
            self._log_message("INFO", "尝试获取默认文件路径...")
            
            # 从multi_excel_selections.json文件中获取第一个Excel文件路径
            try:
                selections_file = Path("logs/multi_excel_selections.json")
                if selections_file.exists():
                    with open(selections_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 获取selections数组中第一个文件的路径
                    if 'selections' in data and len(data['selections']) > 0:
                        file_path = data['selections'][0]['file_path']
                        if file_path and os.path.exists(file_path):
                            self.file_path_var.set(file_path)
                            self._refresh_file_info()
                            self._log_message("INFO", f"已从multi_excel_selections.json获取路径: {file_path}")
                            return
                        else:
                            self._log_message("WARNING", f"文件路径不存在: {file_path}")
                    else:
                        self._log_message("WARNING", "multi_excel_selections.json中没有找到文件选择记录")
                else:
                    self._log_message("WARNING", "multi_excel_selections.json文件不存在")
            except Exception as e:
                self._log_message("DEBUG", f"读取multi_excel_selections.json失败: {str(e)}")
            
            # 尝试从共享数据中获取文件路径（备用方案）
            if self.shared_data and 'current_file_path' in self.shared_data:
                file_path = self.shared_data['current_file_path']
                if file_path and os.path.exists(file_path):
                    self.file_path_var.set(file_path)
                    self._refresh_file_info()
                    self._log_message("INFO", f"已从共享数据获取路径: {file_path}")
                    return
            
            # 尝试从临时文件中读取路径（备用方案）
            try:
                path_file = Path("logs/excel_path.txt")
                if path_file.exists():
                    with open(path_file, 'r', encoding='utf-8') as f:
                        file_path = f.read().strip()
                    if file_path and os.path.exists(file_path):
                        self.file_path_var.set(file_path)
                        self._refresh_file_info()
                        self._log_message("INFO", f"已从临时文件获取路径: {file_path}")
                        return
            except Exception as e:
                self._log_message("DEBUG", f"读取临时路径文件失败: {str(e)}")
            
            # 如果都没有找到，提示用户
            messagebox.showinfo("提示", "未找到默认文件路径，请手动选择文件")
            self._log_message("WARNING", "未找到默认文件路径")
            
        except Exception as e:
            self._log_message("ERROR", f"获取默认路径失败: {str(e)}")
    
    def _select_file(self):
        """选择Excel文件"""
        try:
            file_path = filedialog.askopenfilename(
                title="选择Excel文件",
                filetypes=[
                    ("Excel文件", "*.xlsx *.xls"),
                    ("所有文件", "*.*")
                ]
            )
            
            if file_path:
                self.file_path_var.set(file_path)
                self._refresh_file_info()
                self._log_message("INFO", f"已选择文件: {file_path}")
                
        except Exception as e:
            self._log_message("ERROR", f"选择文件失败: {str(e)}")
    
    def _refresh_file_info(self):
        """刷新文件信息"""
        try:
            file_path = self.file_path_var.get()
            if not file_path:
                self.file_info_var.set("未选择文件")
                return
            
            # 验证文件
            is_valid, message = self.excel_reader.validate_file(file_path)
            if not is_valid:
                self.file_info_var.set(f"文件无效: {message}")
                return
            
            # 获取文件信息
            info = self.excel_reader.get_file_info(file_path)
            
            # 更新工作表列表
            sheets = self.excel_reader.get_sheet_names(file_path)
            self.sheet_combobox['values'] = sheets
            if sheets:
                self.sheet_combobox.current(0)
                self.current_sheet_var.set(sheets[0])
            
            # 更新文件信息显示
            size_mb = info['file_size'] / (1024 * 1024)
            info_text = f"大小: {size_mb:.2f}MB | 工作表: {len(sheets)}个 | 行数: {info['total_rows']} | 列数: {info['total_columns']}"
            self.file_info_var.set(info_text)
            
            self._log_message("INFO", "文件信息刷新成功")
            
        except Exception as e:
            error_msg = f"刷新文件信息失败: {str(e)}"
            self.file_info_var.set(error_msg)
            self._log_message("ERROR", error_msg)
    

    
    def _on_formula_changed(self, event):
        """公式内容变化事件"""
        try:
            formula = self.formula_text.get(1.0, tk.END).strip()
            self.formula_var.set(formula)
        except Exception as e:
            logger.debug(f"公式变化事件处理失败: {str(e)}")
    
    def _validate_formula(self):
        """验证公式语法"""
        try:
            formula = self.formula_text.get(1.0, tk.END).strip()
            if not formula:
                messagebox.showwarning("警告", "请输入公式内容")
                return
            
            if not self.processor:
                self._initialize_processor()
            
            is_valid, message = self.processor.validate_formula(formula)
            
            if is_valid:
                messagebox.showinfo("验证结果", "公式语法正确")
                self._log_message("INFO", f"公式验证通过: {formula}")
            else:
                messagebox.showerror("验证结果", f"公式语法错误:\n{message}")
                self._log_message("ERROR", f"公式验证失败: {message}")
                
        except Exception as e:
            error_msg = f"公式验证异常: {str(e)}"
            messagebox.showerror("错误", error_msg)
            self._log_message("ERROR", error_msg)
    
    def _clear_formula(self):
        """清空公式"""
        self.formula_text.delete(1.0, tk.END)
        self._log_message("INFO", "已清空公式内容")
    
    def _check_column_exists(self):
        """检查目标列是否存在"""
        try:
            file_path = self.file_path_var.get()
            target_column = self.target_column_var.get()
            
            if not file_path or not target_column:
                self.column_status_label.config(text="请先选择文件和输入列名", foreground="red")
                return
            
            # 获取列名列表
            columns = self.excel_reader.get_column_names(file_path, self.current_sheet_var.get())
            
            if target_column in columns:
                self.column_status_label.config(text="✓ 列已存在，将根据覆盖策略处理", foreground="orange")
            else:
                self.column_status_label.config(text="✓ 新列，将创建新列", foreground="green")
                
        except Exception as e:
            self.column_status_label.config(text=f"检查失败: {str(e)}", foreground="red")
    
    def _start_preview_processing(self):
        """开始预处理"""
        if self._validate_inputs():
            self.processing_thread = threading.Thread(target=self._run_preview_processing)
            self.processing_thread.daemon = True
            self.processing_thread.start()
    
    def _start_full_processing(self):
        """开始全量处理"""
        if self._validate_inputs():
            result = messagebox.askyesno("确认", "确定要开始全量处理吗？\n这可能需要较长时间。")
            if result:
                self.processing_thread = threading.Thread(target=self._run_full_processing)
                self.processing_thread.daemon = True
                self.processing_thread.start()
    
    def _validate_inputs(self) -> bool:
        """验证输入参数"""
        if not self.file_path_var.get():
            messagebox.showerror("错误", "请选择Excel文件")
            return False
        
        formula = self.formula_text.get(1.0, tk.END).strip()
        if not formula:
            messagebox.showerror("错误", "请输入公式内容")
            return False
        
        if not self.target_column_var.get():
            messagebox.showerror("错误", "请输入目标列名")
            return False
        
        return True
    
    def _map_strategy_to_backend(self, ui_strategy: str) -> str:
        """将UI中的中文策略选项映射到后端英文策略值"""
        strategy_mapping = {
            '覆盖现有列': 'overwrite',
            '新增列': 'append',
            '创建新工作表': 'new_sheet'
        }
        return strategy_mapping.get(ui_strategy, 'overwrite')

    def _map_error_strategy_to_backend(self, ui_strategy: str) -> str:
        """将UI中的中文错误策略选项映射到后端英文策略值"""
        try:
            # 从配置中查找对应的值
            for strategy in self.config['error_handling']['strategies']:
                if strategy['label'] == ui_strategy:
                    return strategy['value']
            
            # 如果没找到匹配的，根据常见的中文值进行映射
            strategy_mapping = {
                '跳过错误行': 'skip',
                '使用默认值': 'default', 
                '停止处理': 'stop'
            }
            
            mapped_value = strategy_mapping.get(ui_strategy)
            if mapped_value:
                return mapped_value
                
            # 如果还是没找到，返回默认值
            self._log_message("WARNING", f"未知的错误策略: {ui_strategy}，使用默认值 'skip'")
            return 'skip'
            
        except Exception as e:
            self._log_message("ERROR", f"映射错误策略失败: {str(e)}")
            return 'skip'        
    
    def _run_preview_processing(self):
        """运行预处理（在后台线程中）"""
        try:
            self._set_processing_state(True)
            
            # 更新处理器配置（确保使用最新的界面设置）
            error_strategy_value = self._map_error_strategy_to_backend(self.error_strategy_var.get())
            config = ProcessingConfig(
                preview_rows=self.preview_rows_var.get(),
                batch_size=self.batch_size_var.get(),
                error_strategy=ErrorStrategy(error_strategy_value),
                backup_enabled=self.backup_enabled_var.get()
            )
            self.processor.config = config
            
            formula = self.formula_text.get(1.0, tk.END).strip()
            result = self.processor.preview_processing(
                self.file_path_var.get(),
                formula,
                self.target_column_var.get(),
                self.current_sheet_var.get()
            )
            
            # 在主线程中显示结果
            self.main_frame.after(0, lambda: self._show_preview_result(result))
            
        except Exception as e:
            error_msg = str(e)
            self.main_frame.after(0, lambda msg=error_msg: self._log_message("ERROR", f"预处理异常: {msg}"))
        finally:
            self.main_frame.after(0, lambda: self._set_processing_state(False))    
    
    def _run_full_processing(self):
        """运行全量处理（在后台线程中）"""
        try:
            self._set_processing_state(True)
            
            formula = self.formula_text.get(1.0, tk.END).strip()
            strategy = self._map_strategy_to_backend(self.overwrite_strategy_var.get())
            result = self.processor.process_full_file(
                self.file_path_var.get(),
                formula,
                self.target_column_var.get(),
                self.current_sheet_var.get(),
                strategy
            )
            
            # 在主线程中显示结果
            self.main_frame.after(0, lambda: self._show_processing_result(result))
            
        except Exception as e:
            # 捕获异常信息
            error_msg = str(e)
            self.main_frame.after(0, lambda msg=error_msg: self._log_message("ERROR", f"全量处理异常: {msg}"))
        finally:
            self.main_frame.after(0, lambda: self._set_processing_state(False))
    
    def _show_preview_result(self, result):
        """显示预处理结果"""
        if result.success:
            message = f"预处理完成！\n\n"
            message += f"处理行数: {result.processed_rows}\n"
            message += f"成功行数: {result.success_rows}\n"
            message += f"错误行数: {result.error_rows}\n"
            message += f"执行时间: {result.execution_time:.2f}秒"
            
            messagebox.showinfo("预处理结果", message)
            
            # 可以选择显示详细结果
            if result.result_data is not None:
                show_detail = messagebox.askyesno("查看详情", "是否查看详细结果数据？")
                if show_detail:
                    self._show_result_window(result.result_data, "预处理结果")
        else:
            error_msg = "预处理失败！\n\n"
            if result.errors:
                error_msg += f"错误信息: {result.errors[0].get('error', '未知错误')}"
            messagebox.showerror("预处理失败", error_msg)
    
    def _show_processing_result(self, result):
        """显示全量处理结果"""
        if result.success:
            message = f"全量处理完成！\n\n"
            message += f"总行数: {result.total_rows}\n"
            message += f"处理行数: {result.processed_rows}\n"
            message += f"成功行数: {result.success_rows}\n"
            message += f"错误行数: {result.error_rows}\n"
            message += f"执行时间: {result.execution_time:.2f}秒"
            
            messagebox.showinfo("处理完成", message)
        else:
            error_msg = "全量处理失败！\n\n"
            if result.errors:
                error_msg += f"错误信息: {result.errors[0].get('error', '未知错误')}"
            messagebox.showerror("处理失败", error_msg)
    
    def _show_result_window(self, data, title):
        """显示结果数据窗口"""
        try:
            result_window = tk.Toplevel(self.main_frame)
            result_window.title(title)
            result_window.geometry("800x600")
            
            # 创建表格显示数据
            frame = ttk.Frame(result_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建Treeview
            columns = list(data.columns)
            tree = ttk.Treeview(frame, columns=columns, show='headings', height=20)
            
            # 设置列标题
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            # 添加数据
            for index, row in data.iterrows():
                tree.insert('', tk.END, values=list(row))
            
            # 添加滚动条
            scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
            scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
            
        except Exception as e:
            self._log_message("ERROR", f"显示结果窗口失败: {str(e)}")
    
    def _pause_processing(self):
        """暂停处理"""
        if self.processor:
            self.processor.pause_processing()
            self._log_message("INFO", "已请求暂停处理")
    
    def _stop_processing(self):
        """停止处理"""
        if self.processor:
            self.processor.stop_processing()
            self._log_message("INFO", "已请求停止处理")
    
    def _set_processing_state(self, is_processing: bool):
        """设置处理状态"""
        self.is_processing = is_processing
        
        if is_processing:
            self.preview_button.config(state='disabled')
            self.process_button.config(state='disabled')
            self.pause_button.config(state='normal')
            self.stop_button.config(state='normal')
            self.status_var.set("处理中...")
        else:
            self.preview_button.config(state='normal')
            self.process_button.config(state='normal')
            self.pause_button.config(state='disabled')
            self.stop_button.config(state='disabled')
            self.status_var.set("就绪")
            self.progress_var.set(0)
    
    def _on_progress_update(self, progress_info: ProgressInfo):
        """进度更新回调"""
        try:
            # 使用 after 方法确保在主线程中更新UI
            def update_ui():
                # 更新进度条
                self.progress_var.set(progress_info.progress_percent)
                
                # 更新进度信息
                info_text = f"进度: {progress_info.current_row}/{progress_info.total_rows}\n"
                info_text += f"成功: {progress_info.success_count} | 错误: {progress_info.error_count}\n"
                info_text += f"速度: {progress_info.processing_speed:.1f} 行/秒\n"
                
                if progress_info.estimated_remaining > 0:
                    remaining_min = progress_info.estimated_remaining / 60
                    info_text += f"预计剩余: {remaining_min:.1f} 分钟"
                
                self.progress_info_label.config(text=info_text)
                
                # 更新状态
                self.status_var.set(f"处理中... {progress_info.current_row}/{progress_info.total_rows}")
            
            # 确保在主线程中执行UI更新
            if hasattr(self, 'main_frame'):
                self.main_frame.after(0, update_ui)
            else:
                update_ui()
                
        except Exception as e:
            logger.debug(f"进度更新失败: {str(e)}")
    
    def _on_log_message(self, level: str, message: str):
        """日志消息回调"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {level}: {message}\n"
            
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, log_entry, level.upper())
            self.log_text.config(state='disabled')
            self.log_text.see(tk.END)
            
        except Exception as e:
            logger.debug(f"日志显示失败: {str(e)}")
    
    def _log_message(self, level: str, message: str):
        """内部日志方法"""
        self._on_log_message(level, message)
    
    def _clear_log(self):
        """清空日志"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self._log_message("INFO", "日志已清空")
    
    def get_frame(self):
        """获取主框架（供主程序调用）"""
        return self.main_frame