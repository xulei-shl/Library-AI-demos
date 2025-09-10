#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rename_and_move.py
第一张原名后加-1，其余以第一张名为前缀依次加-2、-3...，并移动到output
"""

import os
import shutil
from pathlib import Path

SRC_DIR = Path(r"E:\scripts\doing\huohua")
OUT_DIR = SRC_DIR / "output"

def main() -> None:
    # 1. 收集所有 jpg（不区分大小写）
    jpegs = sorted(SRC_DIR.glob("*.[jJ][pP][gG]")) + sorted(SRC_DIR.glob("*.[jJ][pP][eE][gG]"))
    if not jpegs:
        print("未找到任何 jpg 图片。")
        return

    # 2. 取第一张文件名的纯名（不含扩展名）作为统一前缀
    base_name = jpegs[0].stem  # BROTHER8530DN_006778
    OUT_DIR.mkdir(exist_ok=True)

    # 3. 重命名并移动
    for idx, old_path in enumerate(jpegs, start=1):
        if idx == 1:
            new_name = f"{base_name}-1.jpg"
        else:
            new_name = f"{base_name}-{idx}.jpg"

        new_path = OUT_DIR / new_name

        # 防止重名覆盖
        counter = 1
        while new_path.exists():
            new_name = f"{base_name}-{idx}_{counter}.jpg"
            new_path = OUT_DIR / new_name
            counter += 1

        shutil.move(str(old_path), str(new_path))
        print(f"{old_path.name}  ->  {new_path.name}")

    print("全部完成！")

if __name__ == "__main__":
    main()