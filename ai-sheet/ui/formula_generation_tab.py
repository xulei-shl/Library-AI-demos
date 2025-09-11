#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公式生成 Tab - 前端（优化版）
1. 仅负责“增强提示词”构建，后端不再重复拼接
2. 读取 logs/multi_excel_preview.md 嵌入样本
3. 移除冗余“## 涉及的列”
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import pyperclip
from typing import List, Dict, Any, Optional, Callable
from modules.formula_generator import OptimizedFormulaGenerator


class SimpleDataDisplaySelector:
    def __init__(self, parent, get_export_data_callback=None):
        self.parent = parent
        self.get_export_data_callback = get_export_data_callback
        self.excel_data = {}
        self.on_selection_changed = None
        self._last_struct_info = ""   # 缓存结构信息
        self._sample_cache = {}       # 样本缓存

        # ------------------- UI 构建（略，与原文件相同） -------------------
        self.frame = ttk.LabelFrame(parent, text="Excel文件和Sheet选择", padding="10")
        self.info_frame = ttk.Frame(self.frame)
        self.info_frame.pack(fill="x", pady=(0, 10))
        self.source_info_label = ttk.Label(self.info_frame, text="数据来源：multi_excel_selections.json",
                                           foreground="blue")
        self.source_info_label.pack(side="left")
        self.button_frame = ttk.Frame(self.info_frame)
        self.button_frame.pack(side="right")
        self.load_btn = ttk.Button(self.button_frame, text="获取数据", command=self.load_data)
        self.load_btn.pack(side="left", padx=(0, 5))
        self.refresh_btn = ttk.Button(self.button_frame, text="刷新数据", command=self.refresh_data)
        self.refresh_btn.pack(side="left")

        self.data_text = scrolledtext.ScrolledText(self.frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.data_text.pack(fill="both", expand=True, pady=(10, 0))

        # 初始加载
        self.load_data()

    # ------------------- 数据加载 -------------------
    def load_data(self):
        try:
            json_file = os.path.join("logs", "multi_excel_selections.json")
            if not os.path.exists(json_file):
                self._show_message("未找到数据文件", "warning")
                return False
            with open(json_file, encoding='utf-8') as f:
                data = json.load(f)
            self._parse_and_display_data(data)
            self._show_message("数据加载成功", "success")
            if self.on_selection_changed:
                self.on_selection_changed(self.get_selected_columns())
            return True
        except Exception as e:
            self._show_message(f"加载失败：{e}", "error")
            return False

    def refresh_data(self):
        return self.load_data()

    # ------------------- 解析 & 缓存 -------------------
    def _parse_and_display_data(self, json_data):
        self.excel_data = {}
        display_lines = ["📊 Excel文件和Sheet数据信息", "=" * 50, ""]
        selections = json_data.get('selections', [])
        if not selections:
            display_lines.append("❌ 没有找到任何选择的数据")
        else:
            for idx, sel in enumerate(selections, 1):
                if 'error' in sel:
                    continue
                file_path = sel.get('file_path', '')
                file_name = sel.get('file_name', '')
                sheet_name = sel.get('sheet_name', '')
                selected_columns = sel.get('selected_columns', [])
                total_rows = sel.get('total_rows', 0)
                if file_name not in self.excel_data:
                    self.excel_data[file_name] = {}
                self.excel_data[file_name][sheet_name] = {
                    'file_path': file_path,
                    'columns': sel.get('column_names', []),
                    'selected_columns': selected_columns,
                    'total_rows': total_rows
                }
                display_lines.extend([
                    f"📁 选择组 {idx}:",
                    f"   文件路径: {file_path}",
                    f"   Sheet名称: {sheet_name}",
                    f"   数据行数: {total_rows}",
                    f"   选择的列: {', '.join(selected_columns) if selected_columns else '未选择指定列'}",
                    ""
                ])
        # 缓存结构信息
        self._last_struct_info = "\n".join(display_lines)
        # 显示到文本框
        self.data_text.config(state=tk.NORMAL)
        self.data_text.delete("1.0", tk.END)
        self.data_text.insert("1.0", self._last_struct_info)
        self.data_text.config(state=tk.DISABLED)

    # ------------------- 样本读取 -------------------
    def _load_preview_sample(self, file_name: str, sheet_name: str) -> str:
        """直接返回 whole-file 内容"""
        preview_file = os.path.join("logs", "multi_excel_preview.md")
        if not os.path.exists(preview_file):
            return ""
        with open(preview_file, encoding='utf-8') as f:
            return f.read().strip()

    # ------------------- 增强提示词 -------------------
    def build_enhanced_prompt(self, requirement_text: str) -> str:
        if not self._last_struct_info:
            return requirement_text
        # 整文件原文
        whole_sample = self._load_preview_sample("", "")
        sample_section = whole_sample or "*请在【数据预览】页生成预览后，再返回此处*"
        return f"# 数据处理需求\n\n{requirement_text}\n\n---\n\n# Excel文件、工作表和处理列信息\n\n{self._last_struct_info}\n\n---\n\n# Excel数据样例\n\n{sample_section}"

    # ------------------- 兼容接口 -------------------
    def get_selected_columns(self):
        cols = []
        for file_name, sheets in self.excel_data.items():
            for sheet_name, data in sheets.items():
                for col in data['selected_columns']:
                    cols.append(f"[{file_name}-{sheet_name}] {col}")
        return cols

    def get_selected_columns_info(self) -> Dict[str, List[str]]:
        info = {}
        for file_name, sheets in self.excel_data.items():
            for sheet_name, data in sheets.items():
                key = f"{file_name}#{sheet_name}"
                # 去掉“C列-”前缀
                clean = [c.split('-', 1)[1] if '-' in c and c.split('-', 1)[0].endswith('列') else c
                         for c in data['selected_columns']]
                info[key] = clean
        return info

    def get_widget(self): return self.frame

    def _show_message(self, msg, typ="info"):
        color = {"success": "green", "warning": "orange", "error": "red"}.get(typ, "blue")
        self.source_info_label.config(text=msg, foreground=color)


class FormulaGenerationTab:
    def __init__(self, parent, multi_excel_tab=None,
                 get_column_list_callback: Optional[Callable] = None,
                 get_sample_data_callback: Optional[Callable] = None):
        self.parent = parent
        self.multi_excel_tab = multi_excel_tab
        self.get_export_data_callback = multi_excel_tab.get_export_data if multi_excel_tab else None
        self.formula_generator = OptimizedFormulaGenerator()
        self.main_frame = ttk.Frame(parent)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self._setup_ui()
        self._load_config_options()
    
    def _setup_ui(self):
        """设置UI界面"""
        # 创建左右分栏
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill="both", expand=True)
        
        # 左侧面板
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # 右侧面板
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=1)
        
        # 设置左侧面板
        self._setup_left_panel()
        
        # 设置右侧面板
        self._setup_right_panel()
    
    def _setup_left_panel(self):
        """设置左侧面板"""
        # 使用新的简化数据显示选择器
        self.column_selector = SimpleDataDisplaySelector(
            self.left_frame, 
            get_export_data_callback=self.get_export_data_callback
        )
        self.column_selector.on_selection_changed = self._on_column_selection_changed
        self.column_selector.get_widget().pack(fill="both", expand=True, pady=(0, 10))
        
        # 需求描述区域
        self.requirement_frame = ttk.LabelFrame(self.left_frame, text="需求描述", padding="10")
        self.requirement_frame.pack(fill="both", expand=True)
        
        # 需求输入框
        self.requirement_text = scrolledtext.ScrolledText(
            self.requirement_frame,
            height=6,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10)
        )
        self.requirement_text.pack(fill="both", expand=True, pady=(0, 10))
        
        # 添加占位符文本
        placeholder_text = """请详细描述您的数据处理需求，例如：

• 从H列的书目信息中提取时间。
• 如：时间：光绪十年一月五日(1884年2月1日) $$ 版本：手稿 $$ 附件：封1 $$ 主题词：苏州府；杭州府；盛宣怀；盛海颐 $$ 架位：3号架
• 提取后结果为：光绪十年一月五日(1884年2月1日)
• 也就是将`时间`和`$$`的内容提取出来

请清空此文本后输入您的具体需求..."""
        
        self.requirement_text.insert("1.0", placeholder_text)
        self.requirement_text.bind("<FocusIn>", self._on_requirement_focus_in)
        
        # 配置选项区域
        self.config_frame = ttk.LabelFrame(self.requirement_frame, text="生成配置", padding="10")
        self.config_frame.pack(fill="x", pady=(10, 10))
        
        # 第一行：提示词和大模型
        self.config_row1 = ttk.Frame(self.config_frame)
        self.config_row1.pack(fill="x", pady=(0, 5))
        
        # 提示词选择
        ttk.Label(self.config_row1, text="提示词:").pack(side="left", padx=(0, 5))
        self.prompt_var = tk.StringVar()
        self.prompt_combo = ttk.Combobox(
            self.config_row1,
            textvariable=self.prompt_var,
            state="readonly",
            width=20
        )
        self.prompt_combo.pack(side="left", padx=(0, 15))
        
        # 大模型选择
        ttk.Label(self.config_row1, text="大模型:").pack(side="left", padx=(0, 5))
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            self.config_row1,
            textvariable=self.model_var,
            state="readonly",
            width=20
        )
        self.model_combo.pack(side="left")
        
        # 第二行：temperature和top_p
        self.config_row2 = ttk.Frame(self.config_frame)
        self.config_row2.pack(fill="x")
        
        # Temperature
        ttk.Label(self.config_row2, text="Temperature:").pack(side="left", padx=(0, 5))
        self.temperature_var = tk.StringVar(value="0.3")
        self.temperature_entry = ttk.Entry(
            self.config_row2,
            textvariable=self.temperature_var,
            width=8
        )
        self.temperature_entry.pack(side="left", padx=(0, 15))
        
        # Top_p
        ttk.Label(self.config_row2, text="Top_p:").pack(side="left", padx=(0, 5))
        self.top_p_var = tk.StringVar(value="0.9")
        self.top_p_entry = ttk.Entry(
            self.config_row2,
            textvariable=self.top_p_var,
            width=8
        )
        self.top_p_entry.pack(side="left")
        
        # 按钮区域
        self.button_frame = ttk.Frame(self.requirement_frame)
        self.button_frame.pack(fill="x")
        
        # 生成公式按钮
        self.generate_button = ttk.Button(
            self.button_frame,
            text="生成公式",
            command=self._on_generate_formula,
            style="Accent.TButton"
        )
        self.generate_button.pack(side="left", padx=(0, 10))
        
        # 清空按钮
        self.clear_button = ttk.Button(
            self.button_frame,
            text="清空",
            command=self._on_clear_all
        )
        self.clear_button.pack(side="left", padx=(0, 10))
        
        # 刷新数据按钮
        self.refresh_button = ttk.Button(
            self.button_frame,
            text="刷新数据",
            command=self._on_refresh_data
        )
        self.refresh_button.pack(side="left")
    
    def _setup_right_panel(self):
        """设置右侧面板"""
        # 结果显示区域
        self.result_frame = ttk.LabelFrame(self.right_frame, text="生成结果", padding="10")
        self.result_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 创建结果显示区域
        self.result_text = scrolledtext.ScrolledText(
            self.result_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 10)
        )
        self.result_text.pack(fill="both", expand=True)
        
        # 创建按钮框架
        self.result_button_frame = ttk.Frame(self.result_frame)
        self.result_button_frame.pack(fill="x", pady=(10, 0))
        
        # 复制结果按钮
        self.copy_button = ttk.Button(
            self.result_button_frame,
            text="复制结果",
            command=self._copy_result,
            state=tk.DISABLED
        )
        self.copy_button.pack(side="left", padx=(0, 10))
        
        # 清空结果按钮
        self.clear_result_button = ttk.Button(
            self.result_button_frame,
            text="清空结果",
            command=self._clear_result
        )
        self.clear_result_button.pack(side="left")
        
        # 状态和统计信息
        self.status_frame = ttk.LabelFrame(self.right_frame, text="状态信息", padding="10")
        self.status_frame.pack(fill="x")
        
        # 状态标签
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(anchor="w")
        
        # 统计信息
        self.stats_label = ttk.Label(self.status_frame, text="")
        self.stats_label.pack(anchor="w", pady=(5, 0))
        
        # 更新统计信息
        self._update_statistics()
    
    def _load_initial_data(self):
        """加载初始数据"""
        try:
            # 新的简化选择器会自动加载数据，无需手动加载
            # 保持此方法以维持兼容性，但实际工作由SimpleDataDisplaySelector完成
            self.status_label.config(text="数据加载完成")
        except Exception as e:
            self.status_label.config(text=f"加载数据失败：{str(e)}")
    
    def _load_config_options(self):
        """加载配置选项"""
        try:
            print("开始加载配置选项...")
            
            # 加载提示词选项
            prompts = self.formula_generator.prompt_manager.get_all_prompts()
            print(f"获取到 {len(prompts)} 个提示词")
            
            # 移除过滤机制，显示所有提示词
            prompt_options = []
            formula_prompt_exists = False
            default_formula_prompt = None
            
            for prompt in prompts:
                prompt_name = prompt.get('name', prompt.get('id', ''))
                prompt_options.append(prompt_name)
                
                # 检查是否存在"Excel公式生成"提示词
                if 'Excel公式生成' in prompt_name:
                    formula_prompt_exists = True
                    default_formula_prompt = prompt_name
            
            print(f"提示词选项: {prompt_options}")
            self.prompt_combo['values'] = prompt_options
            
            # 设置默认值：优先选择"Excel公式生成"，没有则留空
            if formula_prompt_exists and default_formula_prompt:
                self.prompt_var.set(default_formula_prompt)
                print(f"设置默认提示词: {default_formula_prompt}")
            else:
                # 没有找到"Excel公式生成"相关提示词，留空让用户选择
                self.prompt_var.set("")
                print("未找到'Excel公式生成'提示词，留空让用户选择")
            
            # 加载大模型选项（保持不变）
            models = self.formula_generator.config_manager.get_all_models()
            print(f"获取到 {len(models)} 个模型配置")
            
            model_options = [model.get('name', model.get('model_id', '')) for model in models]
            
            if not model_options:
                model_options = ["默认模型"]
                print("未找到模型配置，使用默认值")
            
            print(f"模型选项: {model_options}")
            self.model_combo['values'] = model_options
            if model_options:
                self.model_var.set(model_options[0])
                
            print("配置选项加载完成")
                
        except Exception as e:
            print(f"加载配置选项失败：{e}")
            import traceback
            traceback.print_exc()
            # 设置默认值 - 不强制设置提示词，让用户自己选择
            self.prompt_combo['values'] = []
            self.prompt_var.set("")
            self.model_combo['values'] = ["默认模型"]
            self.model_var.set("默认模型")
    
    def refresh_config_options(self):
        """刷新配置选项（供外部调用）"""
        try:
            print("开始刷新配置选项...")
            
            # 保存当前选中的值
            current_prompt = self.prompt_var.get()
            current_model = self.model_var.get()
            print(f"当前选中 - 提示词: {current_prompt}, 模型: {current_model}")
            
            # 强制重新初始化配置管理器和提示词管理器，确保读取最新数据
            try:
                print("重新初始化配置管理器...")
                self.formula_generator.config_manager.reload_config()
                print("重新初始化提示词管理器...")
                self.formula_generator.prompt_manager.reload_prompts()
            except Exception as reload_error:
                print(f"重新加载配置时出现错误: {reload_error}")
            
            # 重新加载配置选项
            self._load_config_options()
            print("配置选项重新加载完成")
            
            # 尝试恢复之前的选择，如果不存在则检查默认值
            prompt_values = list(self.prompt_combo['values'])
            
            if current_prompt in prompt_values:
                self.prompt_var.set(current_prompt)
                print(f"恢复提示词选择: {current_prompt}")
            else:
                # 检查是否存在"Excel公式生成"作为默认值
                formula_prompt = None
                for value in prompt_values:
                    if 'Excel公式生成' in value:
                        formula_prompt = value
                        break
                
                if formula_prompt:
                    self.prompt_var.set(formula_prompt)
                    print(f"使用默认提示词: {formula_prompt}")
                else:
                    # 没有找到"Excel公式生成"相关提示词，留空让用户选择
                    self.prompt_var.set("")
                    print("未找到'Excel公式生成'提示词，留空让用户选择")
            
            # 模型选择逻辑保持不变...
            model_values = list(self.model_combo['values'])
            if current_model in model_values:
                self.model_var.set(current_model)
                print(f"恢复模型选择: {current_model}")
            else:
                print(f"原模型 '{current_model}' 不存在，使用默认值")
                
            # 强制更新UI显示
            self.prompt_combo.update()
            self.model_combo.update()
            print("UI更新完成")
                
            print("配置选项刷新完成")
                
        except Exception as e:
            print(f"刷新配置选项失败：{e}")
            import traceback
            traceback.print_exc()
    
    def _on_column_selection_changed(self, selected_columns: List[str]):
        """列选择变更回调"""
        count = len(selected_columns)
        if count == 0:
            self.status_label.config(text="请选择至少一列数据")
        else:
            # 限制显示的列名长度，避免状态栏过长
            if count <= 3:
                display_text = f"已选择 {count} 列：{', '.join(selected_columns)}"
            else:
                display_text = f"已选择 {count} 列：{', '.join(selected_columns[:2])} 等..."
            
            self.status_label.config(text=display_text)
    
    def _on_requirement_focus_in(self, event):
        """需求输入框获得焦点时的处理"""
        current_text = self.requirement_text.get("1.0", tk.END).strip()
        if "请清空此文本后输入您的具体需求" in current_text:
            self.requirement_text.delete("1.0", tk.END)
    
    def _on_generate_formula(self):
        """生成公式按钮点击事件 - 使用增强的提示词"""
        try:
            # 获取选中的列信息
            selected_info = self.column_selector.get_selected_columns_info()
            requirement = self.requirement_text.get("1.0", tk.END).strip()
            
            if not selected_info:
                messagebox.showwarning("警告", "请至少选择一列数据")
                return
            
            # 验证需求描述
            if not requirement or len(requirement) < 10:
                messagebox.showwarning("警告", "请输入详细的需求描述（至少10个字符）")
                return
            
            if "请清空此文本后输入您的具体需求" in requirement:
                messagebox.showwarning("警告", "请输入您的具体需求")
                return
            
            # 使用增强的提示词构建
            enhanced_prompt = self.column_selector.build_enhanced_prompt(requirement)
            
            # 获取配置参数
            selected_prompt = self.prompt_var.get()
            selected_model = self.model_var.get()
            
            try:
                temperature = float(self.temperature_var.get())
                if not (0.0 <= temperature <= 1.0):
                    raise ValueError("Temperature必须在0.0-1.0之间")
            except ValueError as e:
                messagebox.showwarning("警告", f"Temperature参数无效：{e}")
                return
            
            try:
                top_p = float(self.top_p_var.get())
                if not (0.0 <= top_p <= 1.0):
                    raise ValueError("Top_p必须在0.0-1.0之间")
            except ValueError as e:
                messagebox.showwarning("警告", f"Top_p参数无效：{e}")
                return
            
            # 显示生成状态
            self._show_generating_status()
            self.generate_button.config(state=tk.DISABLED, text="生成中...")
            self.status_label.config(text="正在生成公式...")
            
          # 异步生成公式（使用增强的提示词）
            self.formula_generator.generate_formula_async(
                requirement=enhanced_prompt,  # 使用增强的提示词
                columns=list(selected_info.keys()),  # 传递文件-Sheet键
                sample_data="",  # 预览数据已包含在enhanced_prompt中
                selected_prompt=selected_prompt,
                selected_model=selected_model,
                temperature=temperature,
                top_p=top_p,
                success_callback=self._on_formula_generated,
                error_callback=self._on_formula_error,
                progress_callback=self._on_generation_progress
            )
            
        except Exception as e:
            messagebox.showerror("错误", f"生成公式时出错：{str(e)}")
            self._reset_generate_button()
    
    def _show_generating_status(self, message: str = "正在生成公式，请稍候..."):
        """显示生成状态"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", f"⏳ {message}")
        self.result_text.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
    
    def _on_formula_generated(self, result: Dict[str, Any]):
        """公式生成成功回调"""
        # 使用after方法确保在主线程中更新UI
        self.parent.after(0, self._update_ui_after_generation, result)
    
    def _on_formula_error(self, result: Dict[str, Any]):
        """公式生成失败回调"""
        # 使用after方法确保在主线程中更新UI
        self.parent.after(0, self._update_ui_after_generation, result)
    
    def _on_generation_progress(self, message: str):
        """生成进度回调"""
        self.parent.after(0, lambda: self.status_label.config(text=message))
    
    def _update_ui_after_generation(self, result: Dict[str, Any]):
        """在主线程中更新UI"""
        try:
            # 显示结果
            self._display_result(result)
            
            # 更新状态
            if result['success']:
                self.status_label.config(text="公式生成成功")
            else:
                self.status_label.config(text=f"生成失败：{result['error']}")
            
            # 更新统计信息
            self._update_statistics()
            
        except Exception as e:
            print(f"更新UI时出错：{e}")
        finally:
            # 恢复按钮状态
            self._reset_generate_button()
    
    def _display_result(self, result: Dict[str, Any]):
        """显示生成结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        
        if result['success']:
            # 成功结果 - 直接显示大模型返回的内容
            content = f"✅ 公式生成成功\n\n"
            content += result['explanation']  # 直接显示大模型的完整响应
            
            self.result_text.insert("1.0", content)
            self.copy_button.config(state=tk.NORMAL)
            
        else:
            # 失败结果
            content = f"❌ 公式生成失败\n\n"
            content += f"错误信息：{result['error']}\n"
            
            if result['explanation']:
                content += f"\nAI响应：{result['explanation']}"
            
            self.result_text.insert("1.0", content)
            self.copy_button.config(state=tk.DISABLED)
            
            # 设置错误信息样式
            self.result_text.tag_add("error", "3.5", "3.end")
            self.result_text.tag_config("error", foreground="red")
        
        self.result_text.config(state=tk.DISABLED)
    
    def _copy_result(self):
        """复制全部结果文本到剪贴板"""
        try:
            # 启用文本编辑状态
            self.result_text.config(state=tk.NORMAL)
            # 获取全部文本内容
            all_text = self.result_text.get("1.0", tk.END).strip()
            # 恢复只读状态
            self.result_text.config(state=tk.DISABLED)
            
            # 复制到剪贴板
            pyperclip.copy(all_text)
            messagebox.showinfo("成功", "全部内容已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败：{str(e)}")
    
    def _clear_result(self):
        """清空结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.copy_button.config(state=tk.DISABLED)
    
    def _reset_generate_button(self):
        """重置生成按钮状态"""
        self.generate_button.config(state=tk.NORMAL, text="生成公式")
    
    def _on_clear_all(self):
        """清空所有内容"""
        # 清空列选择
        self.column_selector.clear_selection()
        
        # 清空需求描述
        self.requirement_text.delete("1.0", tk.END)
        placeholder_text = """请详细描述您的数据处理需求，例如：

• 从H列的书目信息中提取时间。
• 如：时间：光绪十年一月五日(1884年2月1日) $$ 版本：手稿 $$ 附件：封1 $$ 主题词：苏州府；杭州府；盛宣怀；盛海颐 $$ 架位：3号架
• 提取后结果为：光绪十年一月五日(1884年2月1日)
• 也就是将`时间`和`$$`的内容提取出来

请清空此文本后输入您的具体需求..."""
        self.requirement_text.insert("1.0", placeholder_text)
        
        # 清空结果
        self._clear_result()
        
        # 更新状态
        self.status_label.config(text="已清空所有内容")
    
    def _on_refresh_data(self):
        """刷新数据"""
        # 刷新简化数据显示选择器的数据
        success = self.column_selector.refresh_data()
        
        if success:
            self.status_label.config(text="数据刷新成功")
        else:
            self.status_label.config(text="数据刷新失败，请检查数据源")
        
        # 更新统计信息
        self._update_statistics()
    
    def _update_statistics(self):
        """更新统计信息"""
        try:
            cache_stats = self.formula_generator.get_cache_statistics()
            history_stats = self.formula_generator.get_history_statistics()
            
            stats_text = f"缓存: {cache_stats['cache_size']}/{cache_stats['max_cache_size']} | "
            stats_text += f"历史: {history_stats['total_formulas']}"
            
            self.stats_label.config(text=stats_text)
        except Exception as e:
            self.stats_label.config(text="统计信息获取失败")
    
    def get_main_frame(self) -> ttk.Frame:
        """获取主框架"""
        return self.main_frame
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清空缓存
            self.formula_generator.clear_cache()
        except Exception as e:
            print(f"清理资源时出错：{e}")


# 测试代码
if __name__ == "__main__":
    def test_get_columns():
        return ["A列-姓名", "B列-年龄", "C列-部门", "D列-薪资", "E列-入职日期", "F列-绩效"]
    
    def test_get_sample_data():
        return """姓名,年龄,部门,薪资,入职日期,绩效
张三,28,技术部,8000,2022-01-15,优秀
李四,32,销售部,6500,2021-03-20,良好
王五,25,技术部,7200,2023-02-10,优秀
赵六,35,人事部,5800,2020-05-12,良好
钱七,29,技术部,9500,2022-08-30,优秀"""
    
    root = tk.Tk()
    root.title("公式生成Tab测试")
    root.geometry("1200x800")
    
    # 创建公式生成Tab
    formula_tab = FormulaGenerationTab(
        root, 
        get_column_list_callback=test_get_columns,
        get_sample_data_callback=test_get_sample_data
    )
    
    root.mainloop()