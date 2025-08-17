#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CNKI文献研究工具套件 - 主启动文件
模块化GUI版本
"""

import tkinter as tk
from gui.main_window import MainWindow

def main():
    """主函数"""
    try:
        # 创建主窗口
        app = MainWindow()
        
        # 设置窗口图标（如果有的话）
        try:
            app.root.iconbitmap('icon.ico')
        except:
            pass
        
        # 居中显示窗口
        app.root.update_idletasks()
        width = app.root.winfo_width()
        height = app.root.winfo_height()
        x = (app.root.winfo_screenwidth() // 2) - (width // 2)
        y = (app.root.winfo_screenheight() // 2) - (height // 2)
        app.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # 运行主循环
        app.run()
        
    except Exception as e:
        print(f"启动应用程序时出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()