#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Package the Local Book Researcher skill into a .skill file
"""

import os
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path

def package_skill():
    """Package the skill into a .skill file"""

    # Get the skill directory
    skill_dir = Path(__file__).parent
    skill_name = skill_dir.name
    parent_dir = skill_dir.parent

    # Create output filename
    output_file = parent_dir / f"{skill_name}.skill"

    # Remove existing .skill file if it exists
    if output_file.exists():
        output_file.unlink()

    # Create a temporary directory for packaging
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_skill_dir = Path(temp_dir) / skill_name
        shutil.copytree(skill_dir, temp_skill_dir)

        # Create zip file
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in temp_skill_dir.rglob('*'):
                if file_path.is_file():
                    # Calculate relative path from skill directory
                    arcname = file_path.relative_to(temp_skill_dir)
                    zf.write(file_path, arcname)

    print(f"技能已打包到: {output_file}")
    print(f"文件大小: {output_file.stat().st_size} 字节")

if __name__ == "__main__":
    package_skill()