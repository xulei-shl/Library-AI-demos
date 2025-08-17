import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from config_manager import ConfigManager

class PromptGUI:
    def __init__(self, parent):
        self.parent = parent
        self.config_manager = ConfigManager()
        self.setup_ui()
        self.load_prompts()
        
    def setup_ui(self):
        """设置UI界面"""
        # 主框架
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        
        # 左右布局的主容器
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重，让左右两列平均分配宽度
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # 左侧框架
        left_frame = ttk.LabelFrame(content_frame, text="📋 检索主题词生成", padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # 左侧文本编辑框
        left_text_frame = ttk.Frame(left_frame)
        left_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.left_text = tk.Text(left_text_frame, wrap=tk.WORD, font=("Consolas", 12),
                                bg="#2C3E50", fg="white", insertbackground="white")
        left_scrollbar = ttk.Scrollbar(left_text_frame, orient=tk.VERTICAL, command=self.left_text.yview)
        self.left_text.configure(yscrollcommand=left_scrollbar.set)
        
        self.left_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右侧框架
        right_frame = ttk.LabelFrame(content_frame, text="📋 文献相关性判断", padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # 右侧文本编辑框
        right_text_frame = ttk.Frame(right_frame)
        right_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.right_text = tk.Text(right_text_frame, wrap=tk.WORD, font=("Consolas", 12),
                                 bg="#2C3E50", fg="white", insertbackground="white")
        right_scrollbar = ttk.Scrollbar(right_text_frame, orient=tk.VERTICAL, command=self.right_text.yview)
        self.right_text.configure(yscrollcommand=right_scrollbar.set)
        
        self.right_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 保存按钮
        save_button = ttk.Button(button_frame, text="💾 保存提示词", command=self.save_prompts)
        save_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 重置按钮
        reset_button = ttk.Button(button_frame, text="🧹 重置清空", command=self.reset_prompts)
        reset_button.pack(side=tk.LEFT, padx=(0, 10))
        
        
        # 状态标签
        self.status_label = ttk.Label(button_frame, text="就绪", foreground="green")
        self.status_label.pack(side=tk.RIGHT)
        
    def load_prompts(self):
        """从配置文件加载提示词"""
        try:
            # 从配置管理器获取提示词配置
            prompts_config = self.config_manager.config.get("prompts", {})
            
            # 加载左侧提示词
            left_prompt = prompts_config.get("prompt1", {})
            self.left_text.delete(1.0, tk.END)
            if isinstance(left_prompt, dict):
                left_content = left_prompt.get("content", "")
            else:
                left_content = ""
            self.left_text.insert(1.0, left_content)
            
            # 加载右侧提示词
            right_prompt = prompts_config.get("prompt2", {})
            self.right_text.delete(1.0, tk.END)
            if isinstance(right_prompt, dict):
                right_content = right_prompt.get("content", "")
            else:
                right_content = ""
            self.right_text.insert(1.0, right_content)
            
            self.update_status("提示词加载完成", "green")
            
        except Exception as e:
            self.update_status(f"加载失败: {str(e)}", "red")
            messagebox.showerror("错误", f"加载提示词失败: {str(e)}")
    
    def save_prompts(self):
        """保存提示词到配置文件"""
        try:
            # 获取当前提示词内容
            prompts_config = {
                "prompt1": {
                    "label": "检索主题词生成",
                    "content": self.left_text.get(1.0, tk.END).strip()
                },
                "prompt2": {
                    "label": "文献相关性判断",
                    "content": self.right_text.get(1.0, tk.END).strip()
                }
            }
            
            # 保存到配置管理器
            success = self.config_manager.set_setting("prompts", prompts_config)
            if not success:
                raise Exception("配置保存失败")
            
            self.update_status("提示词保存成功", "green")
            messagebox.showinfo("成功", "提示词已保存到配置文件")
            
        except Exception as e:
            self.update_status(f"保存失败: {str(e)}", "red")
            messagebox.showerror("错误", f"保存提示词失败: {str(e)}")
    
    def reset_prompts(self):
        """重置提示词"""
        if messagebox.askyesno("确认", "确定要重置所有提示词吗？"):
            self.left_text.delete(1.0, tk.END)
            self.right_text.delete(1.0, tk.END)
            self.update_status("提示词已重置", "blue")
    
    
    def update_status(self, message, color="black"):
        """更新状态标签"""
        self.status_label.config(text=message, foreground=color)
        # 3秒后恢复为就绪状态
        self.parent.after(3000, lambda: self.status_label.config(text="就绪", foreground="green"))