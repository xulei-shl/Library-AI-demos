#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""  
AI-Sheet 主程序
一个基于大模型的智能电子表格工具
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ui.config_tab import MultiModelConfigTab
from ui.prompt_management_tab import PromptManagementTab
from ui.excel_upload_tab import ExcelUploadTab
from ui.multi_excel_tab import MultiExcelTab
from ui.formula_generation_tab import FormulaGenerationTab
from ui.formula_processing_tab import FormulaProcessingTab
from ui.prompt_generation_tab import PromptGenerationTab
from ui.llm_processing_tab import LLMProcessingTab
from modules.config_manager import MultiModelConfigManager
from ui.python_processing_tab import PythonProcessingTab


class AISheetApp:
    """AI-Sheet 主应用程序类"""
    
    def __init__(self):
        self.root = tk.Tk()
        # 添加配置管理器实例
        self.config_manager = MultiModelConfigManager()
        self.setup_window()
        self.setup_ui()
        
    def setup_window(self):
        """设置主窗口"""
        self.root.title("🤖 AI-Sheet - 智能电子表格工具")
        self.root.geometry("1000x850")
        self.root.minsize(1000, 700)
        
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap("assets/icon.ico")
        except:
            pass
            
        # 居中显示窗口
        self.center_window()
        
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # # 创建标题
        # title_frame = ttk.Frame(main_frame)
        # title_frame.pack(fill='x', pady=(0, 10))
        
        # title_label = ttk.Label(
        #     title_frame, 
        #     text="🤖 AI-Sheet 智能电子表格工具", 
        #     font=('Arial', 12, 'bold')
        # )
        # title_label.pack()
        
        # subtitle_label = ttk.Label(
        #     title_frame, 
        #     text="基于大模型的智能数据处理平台", 
        #     font=('Arial', 10)
        # )
        # subtitle_label.pack()
        
        # 创建选项卡控件
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # 创建各个选项卡
        self.create_tabs()
        
        # 绑定选项卡切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
    # 在AISheetApp类中添加以下方法
    def ensure_tabs_display(self):
        """确保所有Tab的PanedWindow正确显示"""
        if hasattr(self, 'config_tab'):
            self.config_tab.set_paned_position()
        if hasattr(self, 'prompt_tab'):
            self.prompt_tab.set_paned_position()
        if hasattr(self, 'llm_processing_tab'):
            self.llm_processing_tab.set_paned_position()
    
    # 修改create_tabs方法，确保正确的创建顺序
    def create_tabs(self):
        """创建所有选项卡"""
        # 创建共享数据字典，用于在不同Tab之间共享数据
        shared_data = {}


        # # 1. Excel上传Tab（单文件）
        excel_frame = ttk.Frame(self.notebook)        
        # self.notebook.add(excel_frame, text="📊 单Excel上传")
        # self.excel_tab = ExcelUploadTab(excel_frame, shared_data)

        # 2. 多Excel上传Tab
        multi_excel_frame = ttk.Frame(self.notebook)
        self.notebook.add(multi_excel_frame, text="📊 多Excel上传")
        self.multi_excel_tab = MultiExcelTab(multi_excel_frame, shared_data)

        # 3. 公式生成Tab（必须在配置管理Tab之前创建，确保回调函数能正确引用）
        formula_frame = ttk.Frame(self.notebook)
        self.notebook.add(formula_frame, text="🧮 公式生成")
        self.formula_tab = FormulaGenerationTab(
            formula_frame,
            get_column_list_callback=self._get_excel_columns,
            get_sample_data_callback=self._get_excel_sample_data
        )
        
        # 4. 公式处理Tab
        self.formula_processing_tab = FormulaProcessingTab(self.notebook, shared_data)
        self.notebook.add(self.formula_processing_tab.get_frame(), text="🧮 公式处理")
        
        # 5. 提示词生成Tab
        prompt_gen_frame = ttk.Frame(self.notebook)
        self.notebook.add(prompt_gen_frame, text="📝 提示词生成")
        self.prompt_gen_tab = PromptGenerationTab(prompt_gen_frame)
        
                
        # 6. LLM处理Tab（批量AI处理功能）
        llm_processing_frame = ttk.Frame(self.notebook)
        self.notebook.add(llm_processing_frame, text="🤖 大模型处理")
        self.llm_processing_tab = LLMProcessingTab(llm_processing_frame, shared_data)

        # 7. Python处理Tab
        python_processing_frame = ttk.Frame(self.notebook)
        self.notebook.add(python_processing_frame, text="🐍 Python 处理")
        self.python_processing_tab = PythonProcessingTab(python_processing_frame)

        # 8. 配置Tab（在公式生成Tab之后创建，确保回调函数中的formula_tab已存在）
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="⚙️ 配置管理")
        self.config_tab = MultiModelConfigTab(config_frame, config_change_callback=self._on_config_changed)
        
        # 9. 提示词管理Tab（在公式生成Tab之后创建，确保回调函数中的formula_tab已存在）
        prompt_frame = ttk.Frame(self.notebook)
        self.notebook.add(prompt_frame, text="📝 提示词管理")
        self.prompt_tab = PromptManagementTab(prompt_frame, prompt_change_callback=self._on_prompt_changed)

        
        # 确保Tab内容正确显示
        excel_frame.update()
        multi_excel_frame.update()
        formula_frame.update()
        prompt_gen_frame.update()
        llm_processing_frame.update()        
        config_frame.update()
        prompt_frame.update()
        
        # 延迟调用确保PanedWindow正确显示
        self.root.after(500, self.ensure_tabs_display)
    
    # 修改on_tab_changed方法，在切换Tab时也调用ensure_tabs_display
    def on_tab_changed(self, event):
        """选项卡切换事件处理"""
        selected_tab = event.widget.tab('current')['text']
        print(f"切换到选项卡: {selected_tab}")
        
        # 确保当前Tab的PanedWindow正确显示
        self.ensure_tabs_display()
    def run(self):
        """运行应用程序"""
        try:
            # 检查配置状态
            if not self.config_manager.is_configured():
                messagebox.showinfo(
                    "欢迎使用", 
                    "欢迎使用AI-Sheet！\n请先在配置选项卡中设置您的大模型API配置。"
                )
                # 切换到配置选项卡
                self.notebook.select(1)  # 配置选项卡索引
                
            self.root.mainloop()
            
        except KeyboardInterrupt:
            print("\n程序被用户中断")
        except Exception as e:
            messagebox.showerror("错误", f"程序运行出错：{str(e)}")
        finally:
            self.cleanup()
            
    def _get_excel_columns(self):
        """获取Excel列信息的回调函数"""
        try:
            # 优先使用多Excel Tab的数据
            if hasattr(self, 'multi_excel_tab') and hasattr(self.multi_excel_tab, 'get_column_list'):
                multi_columns = self.multi_excel_tab.get_column_list()
                if multi_columns:
                    return multi_columns
            
            # 回退到单Excel Tab
            if hasattr(self, 'excel_tab') and hasattr(self.excel_tab, 'get_column_list'):
                return self.excel_tab.get_column_list()
            
            return []
        except Exception as e:
            print(f"获取Excel列信息失败：{e}")
            return []
    
    def _get_excel_sample_data(self):
        """获取Excel样本数据的回调函数"""
        try:
            # 优先使用多Excel Tab的数据
            if hasattr(self, 'multi_excel_tab') and hasattr(self.multi_excel_tab, 'get_sample_data'):
                multi_sample = self.multi_excel_tab.get_sample_data()
                if multi_sample and multi_sample.strip() != "*请选择Excel文件和Sheet以查看数据预览*":
                    return multi_sample
            
            # 回退到单Excel Tab
            if hasattr(self, 'excel_tab') and hasattr(self.excel_tab, 'get_sample_data'):
                return self.excel_tab.get_sample_data()
            
            return ""
        except Exception as e:
            print(f"获取Excel样本数据失败：{e}")
            return ""
    
    def _on_config_changed(self):
        """配置变更回调函数"""
        try:
            print("🔄 配置变更回调被触发")
            
            # 刷新公式生成Tab配置选项
            if hasattr(self, 'formula_tab') and self.formula_tab is not None:
                print("✅ 找到formula_tab，正在刷新配置选项...")
                self.formula_tab.refresh_config_options()
                print("✅ 公式生成Tab配置选项刷新完成")
            else:
                print("❌ formula_tab不存在或为None，无法刷新配置选项")
            
            # 刷新提示词生成Tab配置选项
            if hasattr(self, 'prompt_gen_tab') and self.prompt_gen_tab is not None:
                print("✅ 找到prompt_gen_tab，正在刷新配置选项...")
                self.prompt_gen_tab.refresh_config_options()
                print("✅ 提示词生成Tab配置选项刷新完成")
            else:
                print("❌ prompt_gen_tab不存在或为None，无法刷新配置选项")
                
            # 刷新LLM处理Tab配置选项
            if hasattr(self, 'llm_processing_tab') and self.llm_processing_tab is not None:
                print("✅ 找到llm_processing_tab，正在刷新配置选项...")
                if hasattr(self.llm_processing_tab, 'refresh_config_options'):
                    self.llm_processing_tab.refresh_config_options()
                    print("✅ LLM处理Tab配置选项刷新完成")
                else:
                    print("❌ llm_processing_tab没有refresh_config_options方法")
            else:
                print("❌ llm_processing_tab不存在或为None，无法刷新配置选项")
                
            # 刷新Python处理Tab配置选项
            if hasattr(self, 'python_processing_tab') and self.python_processing_tab is not None:
                print("✅ 找到python_processing_tab，正在刷新配置选项...")
                if hasattr(self.python_processing_tab, 'refresh_config_options'):
                    self.python_processing_tab.refresh_config_options()
                    print("✅ Python处理Tab配置选项刷新完成")
                else:
                    print("❌ python_processing_tab没有refresh_config_options方法")
            else:
                print("❌ python_processing_tab不存在或为None，无法刷新配置选项")
                
        except Exception as e:
            print(f"❌ 刷新配置选项失败：{e}")
            import traceback
            traceback.print_exc()
    
    def _on_prompt_changed(self):
        """提示词变更回调函数"""
        try:
            print("🔄 提示词变更回调被触发")
            
            # 刷新公式生成Tab提示词选项
            if hasattr(self, 'formula_tab') and self.formula_tab is not None:
                print("✅ 找到formula_tab，正在刷新提示词选项...")
                self.formula_tab.refresh_config_options()
                print("✅ 公式生成Tab提示词选项刷新完成")
            else:
                print("❌ formula_tab不存在或为None，无法刷新提示词选项")
            
            # 刷新提示词生成Tab提示词选项
            if hasattr(self, 'prompt_gen_tab') and self.prompt_gen_tab is not None:
                print("✅ 找到prompt_gen_tab，正在刷新提示词选项...")
                self.prompt_gen_tab.refresh_config_options()
                print("✅ 提示词生成Tab提示词选项刷新完成")
            else:
                print("❌ prompt_gen_tab不存在或为None，无法刷新提示词选项")
                
            # 刷新LLM处理Tab提示词选项
            if hasattr(self, 'llm_processing_tab') and self.llm_processing_tab is not None:
                print("✅ 找到llm_processing_tab，正在刷新提示词选项...")
                if hasattr(self.llm_processing_tab, 'refresh_config_options'):
                    self.llm_processing_tab.refresh_config_options()
                    print("✅ LLM处理Tab提示词选项刷新完成")
                else:
                    print("❌ llm_processing_tab没有refresh_config_options方法")
            else:
                print("❌ llm_processing_tab不存在或为None，无法刷新提示词选项")
                
            # 刷新Python处理Tab提示词选项
            if hasattr(self, 'python_processing_tab') and self.python_processing_tab is not None:
                print("✅ 找到python_processing_tab，正在刷新提示词选项...")
                if hasattr(self.python_processing_tab, 'refresh_config_options'):
                    self.python_processing_tab.refresh_config_options()
                    print("✅ Python处理Tab提示词选项刷新完成")
                else:
                    print("❌ python_processing_tab没有refresh_config_options方法")
            else:
                print("❌ python_processing_tab不存在或为None，无法刷新提示词选项")
                
        except Exception as e:
            print(f"❌ 刷新提示词选项失败：{e}")
            import traceback
            traceback.print_exc()
    
    def cleanup(self):
        """清理资源"""
        print("正在清理资源...")
        # 清理公式生成Tab资源
        if hasattr(self, 'formula_tab'):
            try:
                self.formula_tab.cleanup()
            except Exception as e:
                print(f"清理公式生成Tab资源失败：{e}")
        
        # 清理提示词生成Tab资源
        if hasattr(self, 'prompt_gen_tab'):
            try:
                self.prompt_gen_tab.cleanup()
                print("✅ 提示词生成Tab资源已清理")
            except Exception as e:
                print(f"清理提示词生成Tab资源失败：{e}")
        
        # 清理Excel临时文件
        if hasattr(self, 'excel_tab'):
            try:
                self.excel_tab._remove_temp_file()
                print("✅ Excel临时文件已清理")
            except Exception as e:
                print(f"清理Excel临时文件失败：{e}")
        
        # 清理多Excel临时文件
        if hasattr(self, 'multi_excel_tab'):
            try:
                from modules.multi_excel_utils import clear_multi_excel_temp_files
                clear_multi_excel_temp_files()
                print("✅ 多Excel临时文件已清理")
            except Exception as e:
                print(f"清理多Excel临时文件失败：{e}")
        
        # 清理LLM处理Tab资源
        if hasattr(self, 'llm_processing_tab'):
            try:
                # 如果LLM处理Tab有cleanup方法，则调用它
                if hasattr(self.llm_processing_tab, 'cleanup'):
                    self.llm_processing_tab.cleanup()
                    print("✅ LLM处理Tab资源已清理")
            except Exception as e:
                print(f"清理LLM处理Tab资源失败：{e}")
        
        # 清理Python处理Tab资源
        if hasattr(self, 'python_processing_tab'):
            try:
                if hasattr(self.python_processing_tab, 'cleanup'):
                    self.python_processing_tab.cleanup()
                    print("✅ Python处理Tab资源已清理")
            except Exception as e:
                print(f"清理Python处理Tab资源失败：{e}")
        
        # 清理logs目录下的临时文件
        try:
            import os
            # 清理样本数据临时文件
            temp_file_path = os.path.join("logs", "excel_sample_data.md")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print("✅ 样本数据临时文件已清理")
            
            # 清理Excel路径临时文件
            path_file_path = os.path.join("logs", "excel_path.txt")
            if os.path.exists(path_file_path):
                os.remove(path_file_path)
                print("✅ Excel路径临时文件已清理")
                
        except Exception as e:
            print(f"清理全局临时文件失败：{e}")
        
    def on_closing(self):
        """窗口关闭事件处理"""
        if messagebox.askokcancel("退出", "确定要退出AI-Sheet吗？"):
            self.cleanup()
            self.root.destroy()


def main():
    """主函数"""
    print("🚀 启动AI-Sheet...")
    
    try:
        app = AISheetApp()
        app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.run()
    except Exception as e:
        import traceback
        print(f"❌ 启动失败: {e}")
        print("完整错误堆栈:")
        traceback.print_exc()
        messagebox.showerror("启动错误", f"程序启动失败：{str(e)}")
        return 1
        
    print("👋 AI-Sheet已退出")
    return 0


if __name__ == "__main__":
    sys.exit(main())