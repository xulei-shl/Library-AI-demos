#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
包管理器
负责预置包的管理和快速安装
仅支持Windows平台的优化，其他平台使用原有pip安装逻辑
"""

import os
import sys
import json
import shutil
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class PackageManager:
    """包管理器类
    
    负责：
    1. 检测当前系统和Python版本
    2. 管理预置包的复制和安装
    3. 提供降级到pip安装的机制
    """
    
    def __init__(self, project_root: str):
        """初始化包管理器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root)
        self.preinstalled_dir = self.project_root / "preinstalled_packages"
        self.is_windows = platform.system().lower() == "windows"
        self.python_version = self._get_python_version()
        
        # 核心Excel处理包列表
        self.core_packages = [
            "pandas",
            "openpyxl", 
            "numpy",
            "xlrd",
            "pytz",  # pandas依赖
            "dateutil",  # pandas依赖（实际包名）
            "six",  # 其他包依赖
            "et_xmlfile"  # openpyxl依赖
        ]
        
    def _get_python_version(self) -> str:
        """获取Python主版本号 (如: py39, py310, py311)"""
        major, minor = sys.version_info[:2]
        return f"py{major}{minor}"
    
    def _log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[PackageManager {timestamp}] {message}")
    
    def is_optimization_available(self) -> bool:
        """检查是否支持预置包优化
        
        Returns:
            bool: 是否支持优化（仅Windows且有对应Python版本的预置包）
        """
        if not self.is_windows:
            self._log("非Windows系统，使用标准pip安装")
            return False
            
        version_dir = self.preinstalled_dir / "windows" / self.python_version
        if not version_dir.exists():
            self._log(f"未找到{self.python_version}版本的预置包目录: {version_dir}")
            return False
            
        # 检查核心包是否都存在
        missing_packages = []
        for package in self.core_packages:
            package_dir = version_dir / package
            package_file = version_dir / f"{package}.py"
            if not package_dir.exists() and not package_file.exists():
                missing_packages.append(package)
        
        if missing_packages:
            self._log(f"缺少预置包: {missing_packages}")
            return False
            
        self._log(f"预置包优化可用 - Windows {self.python_version}")
        return True
    
    def get_package_info(self) -> Optional[Dict]:
        """获取预置包版本信息
        
        Returns:
            Dict: 包版本信息，如果不存在返回None
        """
        if not self.is_optimization_available():
            return None
            
        info_file = self.preinstalled_dir / "windows" / self.python_version / "package_info.json"
        if not info_file.exists():
            return None
            
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self._log(f"读取包信息失败: {e}")
            return None
    
    def copy_preinstalled_packages(self, target_site_packages: str) -> Tuple[bool, List[str], List[str]]:
        """复制预置包到目标site-packages目录
        
        Args:
            target_site_packages: 目标site-packages目录路径
            
        Returns:
            (success, installed_packages, failed_packages): 
            成功状态、已安装包列表、失败包列表
        """
        if not self.is_optimization_available():
            return False, [], []
            
        target_dir = Path(target_site_packages)
        source_dir = self.preinstalled_dir / "windows" / self.python_version
        
        installed_packages = []
        failed_packages = []
        
        self._log(f"开始复制预置包到: {target_dir}")
        
        for package in self.core_packages:
            try:
                source_package = source_dir / package
                target_package = target_dir / package
                
                # 检查是目录还是.py文件
                source_py_file = source_dir / f"{package}.py"
                if not source_package.exists() and source_py_file.exists():
                    source_package = source_py_file
                    target_package = target_dir / f"{package}.py"
                
                if not source_package.exists():
                    self._log(f"源包不存在: {source_package}")
                    failed_packages.append(package)
                    continue
                
                # 如果目标包已存在，先删除
                if target_package.exists():
                    if target_package.is_dir():
                        shutil.rmtree(target_package)
                    else:
                        target_package.unlink()
                
                # 复制包
                if source_package.is_dir():
                    shutil.copytree(source_package, target_package)
                else:
                    # 对于.py文件，保留原始扩展名
                    target_file = target_package
                    if source_package.suffix == '.py':
                        target_file = target_package.with_suffix('.py')
                    shutil.copy2(source_package, target_file)
                
                # 复制相关的.dist-info目录
                dist_info_pattern = f"{package}*.dist-info"
                for dist_info in source_dir.glob(dist_info_pattern):
                    target_dist_info = target_dir / dist_info.name
                    if target_dist_info.exists():
                        shutil.rmtree(target_dist_info)
                    shutil.copytree(dist_info, target_dist_info)
                
                # 复制相关的.libs目录（特别针对numpy、pandas等包）
                libs_pattern = f"{package}.libs"
                for libs_dir in source_dir.glob(libs_pattern):
                    target_libs_dir = target_dir / libs_dir.name
                    if target_libs_dir.exists():
                        shutil.rmtree(target_libs_dir)
                    shutil.copytree(libs_dir, target_libs_dir)
                
                installed_packages.append(package)
                self._log(f"✓ 复制包成功: {package}")
                
            except Exception as e:
                self._log(f"✗ 复制包失败 {package}: {e}")
                failed_packages.append(package)
        
        success = len(failed_packages) == 0
        self._log(f"预置包复制完成 - 成功: {len(installed_packages)}, 失败: {len(failed_packages)}")
        
        return success, installed_packages, failed_packages
    
    def filter_requirements(self, requirements_content: str) -> Tuple[str, List[str]]:
        """过滤requirements内容，移除已预置的包
        
        Args:
            requirements_content: 原始requirements内容
            
        Returns:
            (filtered_content, preinstalled_packages): 
            过滤后的requirements内容、已预置的包列表
        """
        if not self.is_optimization_available():
            return requirements_content, []
            
        lines = requirements_content.strip().split('\n')
        filtered_lines = []
        preinstalled_packages = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                filtered_lines.append(line)
                continue
                
            # 提取包名（处理版本号）
            package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].strip()
            
            if package_name.lower() in [pkg.lower() for pkg in self.core_packages]:
                preinstalled_packages.append(package_name)
                self._log(f"跳过预置包: {package_name}")
            else:
                filtered_lines.append(line)
        
        filtered_content = '\n'.join(filtered_lines)
        return filtered_content, preinstalled_packages
    
    def get_site_packages_path(self, venv_path: str) -> str:
        """获取虚拟环境的site-packages路径
        
        Args:
            venv_path: 虚拟环境路径
            
        Returns:
            str: site-packages完整路径
        """
        venv_path = Path(venv_path)
        
        if self.is_windows:
            return str(venv_path / "Lib" / "site-packages")
        else:
            # 非Windows系统（虽然当前不会用到）
            return str(venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages")
    
    def create_preinstalled_structure(self):
        """创建预置包目录结构（用于初始化项目）"""
        if not self.is_windows:
            self._log("非Windows系统，跳过预置包结构创建")
            return
            
        version_dir = self.preinstalled_dir / "windows" / self.python_version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建包信息文件模板
        package_info = {
            "python_version": self.python_version,
            "platform": "windows",
            "created_date": datetime.now().isoformat(),
            "packages": {
                package: "未安装" for package in self.core_packages
            },
            "notes": "使用 setup_preinstalled_packages.py 脚本来填充此目录"
        }
        
        info_file = version_dir / "package_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(package_info, f, ensure_ascii=False, indent=2)
        
        self._log(f"预置包目录结构已创建: {version_dir}")


# 辅助函数：用于准备预置包的脚本
def create_setup_script():
    """创建用于准备预置包的辅助脚本"""
    
    setup_script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预置包准备脚本
用于将当前环境中的核心包复制到预置包目录

使用方法:
1. 在一个干净的虚拟环境中安装所需版本的包
2. 运行此脚本将包复制到预置目录
"""

import os
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime

def main():
    # 获取当前Python版本
    major, minor = sys.version_info[:2]
    python_version = f"py{major}{minor}"
    
    # 核心包列表
    core_packages = [
        "pandas",
        "openpyxl", 
        "numpy",
        "xlrd",
        "pytz",
        "python_dateutil",
        "six"
    ]
    
    # 获取当前环境的site-packages路径
    import site
    site_packages = site.getsitepackages()[0]
    print(f"当前site-packages: {site_packages}")
    
    # 目标目录
    project_root = Path(__file__).parent
    target_dir = project_root / "preinstalled_packages" / "windows" / python_version
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"目标目录: {target_dir}")
    
    # 复制包
    package_info = {
        "python_version": python_version,
        "platform": "windows", 
        "created_date": datetime.now().isoformat(),
        "packages": {}
    }
    
    for package in core_packages:
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
                    print(f"⚠️  未找到包: {package}")
                    continue
            
            # 复制到目标目录
            target_package = target_dir / package
            if target_package.exists():
                if target_package.is_dir():
                    shutil.rmtree(target_package)
                else:
                    target_package.unlink()
            
            if source_package.is_dir():
                shutil.copytree(source_package, target_package)
            else:
                shutil.copy2(source_package, target_package)
            
            # 复制.dist-info目录
            dist_info_pattern = f"{package}*.dist-info"
            for dist_info in Path(site_packages).glob(dist_info_pattern):
                target_dist_info = target_dir / dist_info.name
                if target_dist_info.exists():
                    shutil.rmtree(target_dist_info)
                shutil.copytree(dist_info, target_dist_info)
            
            # 获取版本信息
            try:
                import importlib.metadata
                version = importlib.metadata.version(package)
                package_info["packages"][package] = version
            except:
                package_info["packages"][package] = "unknown"
            
            print(f"✓ 复制成功: {package}")
            
        except Exception as e:
            print(f"✗ 复制失败 {package}: {e}")
            package_info["packages"][package] = f"failed: {e}"
    
    # 保存包信息
    info_file = target_dir / "package_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(package_info, f, ensure_ascii=False, indent=2)
    
    print(f"\\n预置包准备完成！")
    print(f"包信息已保存到: {info_file}")

if __name__ == "__main__":
    main()
'''
    
    return setup_script_content


if __name__ == "__main__":
    # 测试代码
    project_root = Path(__file__).parent.parent
    manager = PackageManager(str(project_root))
    
    print(f"Windows系统: {manager.is_windows}")
    print(f"Python版本: {manager.python_version}")
    print(f"优化可用: {manager.is_optimization_available()}")
    
    if manager.is_optimization_available():
        info = manager.get_package_info()
        print(f"包信息: {info}")
    else:
        print("创建预置包目录结构...")
        manager.create_preinstalled_structure()
        
        # 创建准备脚本
        setup_script = create_setup_script()
        setup_file = project_root / "setup_preinstalled_packages.py"
        with open(setup_file, 'w', encoding='utf-8') as f:
            f.write(setup_script)
        print(f"准备脚本已创建: {setup_file}")