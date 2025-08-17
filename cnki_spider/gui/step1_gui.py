import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from step1_search_generator import generate_search_terms_for_gui

class Step1GUI:
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面 - 左右1:3布局"""
        # 主容器 - 使用grid布局更好控制比例
        main_container = ttk.Frame(self.parent_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置网格权重 - 左右平均宽度
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)
        
        # 左侧面板
        left_panel = ttk.Frame(main_container, padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # 右侧面板
        right_panel = ttk.Frame(main_container, padding="10")
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # === 左侧面板内容 ===
        self._setup_left_panel(left_panel)
        
        # === 右侧面板内容 ===
        self._setup_right_panel(right_panel)
    
    def _setup_left_panel(self, left_panel):
        """设置左侧面板内容"""
        # 标题
        ttk.Label(left_panel, text="🤖 检索词生成", 
                 font=('Microsoft YaHei UI', 14, 'bold'),
                 foreground='#2c3e50').pack(pady=(0, 15))
        
        # 输入区域
        input_frame = ttk.LabelFrame(left_panel, text="初始主题词输入", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        text_frame = ttk.Frame(input_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.requirement_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10), 
                                      bg='#2C3E50', fg='white', insertbackground='white', height=8)
        requirement_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.requirement_text.yview)
        self.requirement_text.configure(yscrollcommand=requirement_scroll.set)
        
        # 使用grid布局
        self.requirement_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        requirement_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # 生成按钮
        generate_btn = ttk.Button(left_panel, text="🚀 生成检索词", 
                                command=self.generate_search_terms,
                                style="Accent.TButton")
        generate_btn.pack(fill=tk.X, pady=10)
    
    def _setup_right_panel(self, right_panel):
        """设置右侧面板内容"""
        # 结果显示标题
        result_title_frame = ttk.Frame(right_panel)
        result_title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(result_title_frame, text="📋 生成结果", 
                 font=('Microsoft YaHei UI', 14, 'bold'),
                 foreground='#2c3e50').pack(side=tk.LEFT)
        
        # 结果显示和修改区域
        result_frame = ttk.LabelFrame(right_panel, text="检索词结果 (可编辑)", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建文本框和滚动条
        text_container = ttk.Frame(result_frame)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(text_container, wrap=tk.WORD, font=('Consolas', 10),
                                 bg='#2c3e50', fg='white', insertbackground='white')
        result_v_scroll = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.result_text.yview)
        result_h_scroll = ttk.Scrollbar(text_container, orient=tk.HORIZONTAL, command=self.result_text.xview)
        
        self.result_text.configure(yscrollcommand=result_v_scroll.set, xscrollcommand=result_h_scroll.set)
        
        # 布局文本框和滚动条
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_v_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        result_h_scroll.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        text_container.columnconfigure(0, weight=1)
        text_container.rowconfigure(0, weight=1)
        
        # 初始提示文本
        self.result_text.insert(tk.END, "点击'生成检索词'按钮开始生成...\n\n生成后您可以在此处直接编辑和修改结果。")
        
        # 底部按钮区域
        self._setup_bottom_buttons(right_panel)
    
    def _setup_bottom_buttons(self, parent):
        """设置底部按钮区域"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 导出按钮
        export_btn = ttk.Button(bottom_frame, text="📤 导出保存", 
                              command=self.export_results)
        export_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 清空按钮
        clear_btn = ttk.Button(bottom_frame, text="🗑️ 清空", 
                             command=self.clear_results)
        clear_btn.pack(side=tk.RIGHT)
    
    def generate_search_terms(self):
        """生成检索词"""
        requirement = self.requirement_text.get("1.0", tk.END).strip()
        
        if not requirement:
            messagebox.showwarning("输入错误", "请输入初始主题词")
            return
        
        # 清空结果区域
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "正在调用大模型生成检索词，请稍候...\n")
        
        # 在新线程中执行生成任务
        thread = threading.Thread(target=self._generate_in_background, args=(requirement,))
        thread.daemon = True
        thread.start()
    
    def _generate_in_background(self, requirement):
        """后台生成检索词"""
        try:
            # 调用实际的大模型生成逻辑
            result = generate_search_terms_for_gui(requirement)
            
            # 在主线程中更新UI
            self.parent_frame.after(0, self._update_result, result)
            
        except Exception as e:
            error_msg = f"生成失败: {str(e)}"
            self.parent_frame.after(0, self._update_result, error_msg)
    
    def _update_result(self, result):
        """更新结果显示"""
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, result)
    
    def clear_results(self):
        """清空结果"""
        if messagebox.askyesno("确认清空", "确定要清空所有结果吗？"):
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, "点击'生成检索词'按钮开始生成...\n\n生成后您可以在此处直接编辑和修改结果。")
    
    def export_results(self):
        """导出结果"""
        content = self.result_text.get("1.0", tk.END).strip()
        if not content or content == "点击'生成检索词'按钮开始生成...\n\n生成后您可以在此处直接编辑和修改结果。":
            messagebox.showwarning("导出失败", "没有可导出的内容")
            return
        
        try:
            # 选择保存位置
            filename = filedialog.asksaveasfilename(
                title="导出检索词结果",
                defaultextension=".txt",
                filetypes=[
                    ("文本文件", "*.txt"),
                    ("所有文件", "*.*")
                ]
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("导出成功", f"结果已导出到: {filename}")
                
        except Exception as e:
            messagebox.showerror("导出失败", f"导出文件时出错: {str(e)}")