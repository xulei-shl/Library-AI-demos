#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预置包准备脚本
用于将当前环境中的核心包复制到预置包目录

使用方法:
1. 在一个干净的虚拟环境中安装所需版本的包：
   pip install pandas==2.3.2 openpyxl==3.1.5 numpy==2.3.2 xlrd==2.0.1
2. 运行此脚本将包复制到预置目录：
   python setup_preinstalled_packages.py
"""

import os
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime

def main():
    print("=" * 60)
    print("AI-Sheet 预置包准备脚本")
    print("=" * 60)
    
    # 获取当前Python版本
    major, minor = sys.version_info[:2]
    python_version = f"py{major}{minor}"
    print(f"Python版本: {major}.{minor} ({python_version})")
    
    # 核心包列表
    core_packages = [
        "pandas",
        "openpyxl", 
        "numpy",
        "xlrd",
        "pytz",          # pandas依赖
        "dateutil",      # pandas依赖（实际包名）
        "six",           # 通用依赖
        "et_xmlfile"     # openpyxl依赖
    ]
    
    print(f"核心包列表: {', '.join(core_packages)}")
    
    # 获取当前环境的site-packages路径
    import site
    site_packages_list = site.getsitepackages()
    site_packages = None
    
    # 选择最合适的site-packages路径（选择包含site-packages的路径）
    for sp in site_packages_list:
        if "site-packages" in sp and os.path.exists(sp):
            site_packages = sp
            break
    
    if not site_packages:
        print("❌ 错误: 无法找到site-packages目录")
        return False
        
    print(f"当前site-packages: {site_packages}")
    
    # 目标目录
    project_root = Path(__file__).parent
    target_dir = project_root / "preinstalled_packages" / "windows" / python_version
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"目标目录: {target_dir}")
    print()
    
    # 复制包
    package_info = {
        "python_version": python_version,
        "platform": "windows", 
        "created_date": datetime.now().isoformat(),
        "source_site_packages": site_packages,
        "packages": {}
    }
    
    success_count = 0
    failed_count = 0
    
    for package in core_packages:
        print(f"处理包: {package}")
        try:
            # 查找包目录
            source_package = Path(site_packages) / package
            if not source_package.exists():
                # 尝试查找其他可能的名称
                possible_names = [f"{package}.py", f"{package}.pyd"]
                found = False
                for name in possible_names:
                    alt_source = Path(site_packages) / name
                    if alt_source.exists():
                        source_package = alt_source
                        found = True
                        break
                
                if not found:
                    print(f"  ⚠️  未找到包: {package}")
                    package_info["packages"][package] = "not_found"
                    failed_count += 1
                    continue
            
            # 复制到目标目录
            target_package = target_dir / package
            if target_package.exists():
                if target_package.is_dir():
                    shutil.rmtree(target_package)
                else:
                    target_package.unlink()
            
            print(f"  📁 复制 {source_package} -> {target_package}")
            if source_package.is_dir():
                shutil.copytree(source_package, target_package)
            else:
                # 对于.py文件，保留原始扩展名
                target_file = target_package
                if source_package.suffix == '.py':
                    target_file = target_package.with_suffix('.py')
                shutil.copy2(source_package, target_file)
            
            # 复制.dist-info目录
            dist_info_pattern = f"{package}*.dist-info"
            dist_info_found = False
            for dist_info in Path(site_packages).glob(dist_info_pattern):
                target_dist_info = target_dir / dist_info.name
                if target_dist_info.exists():
                    shutil.rmtree(target_dist_info)
                print(f"  📄 复制 {dist_info.name}")
                shutil.copytree(dist_info, target_dist_info)
                dist_info_found = True
            
            # 复制.libs目录（特别针对numpy、pandas等包）
            libs_pattern = f"{package}.libs"
            for libs_dir in Path(site_packages).glob(libs_pattern):
                target_libs_dir = target_dir / libs_dir.name
                if target_libs_dir.exists():
                    shutil.rmtree(target_libs_dir)
                print(f"  📁 复制 {libs_dir.name}")
                shutil.copytree(libs_dir, target_libs_dir)
            
            # 获取版本信息
            try:
                import importlib.metadata
                version = importlib.metadata.version(package)
                package_info["packages"][package] = {
                    "version": version,
                    "has_dist_info": dist_info_found,
                    "is_directory": source_package.is_dir()
                }
                print(f"  ✅ 成功 (版本: {version})")
            except Exception as ve:
                package_info["packages"][package] = {
                    "version": "unknown", 
                    "has_dist_info": dist_info_found,
                    "is_directory": source_package.is_dir(),
                    "version_error": str(ve)
                }
                print(f"  ✅ 成功 (版本: 未知)")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            package_info["packages"][package] = {
                "error": str(e),
                "status": "failed"
            }
            failed_count += 1
        
        print()
    
    # 保存包信息
    info_file = target_dir / "package_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(package_info, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)
    print("预置包准备完成！")
    print(f"✅ 成功: {success_count} 个包")
    print(f"❌ 失败: {failed_count} 个包")
    print(f"📄 包信息已保存到: {info_file}")
    print("=" * 60)
    
    # 显示使用提示
    if success_count > 0:
        print("\n使用提示:")
        print("1. 预置包已准备完成，下次执行Python代码时将自动使用")
        print("2. 如需更新预置包，请重新运行此脚本")
        print("3. 如需查看预置包信息，请查看 package_info.json 文件")
    
    return success_count > 0

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ 预置包准备失败，请检查当前环境是否安装了所需的包")
        print("建议先运行: pip install pandas openpyxl numpy xlrd")
        sys.exit(1)
    else:
        print("\n🎉 预置包准备成功！")