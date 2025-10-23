# -*- coding: utf-8 -*-
import os
import re
from dataclasses import dataclass
from typing import List, Dict, Optional

from src.utils.logger import get_logger

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif', '.svg', '.ico', '.avif'}

logger = get_logger(__name__)

@dataclass
class ImageGroup:
    """
    表示一组同一对象或系列的图像集合。
    group_type: 'b' (根目录直接分组) | 'a_series' (系列样本) | 'a_object' (对象图像组)
    """
    group_id: str
    image_paths: List[str]
    group_type: str
    root_dir: str
    series_dir: Optional[str] = None
    object_dir: Optional[str] = None

    def get_consensus_file_path(self) -> Optional[str]:
        """
        获取该组对应的系列共识文件路径。

        Returns:
            共识文件路径，如果该组不属于任何系列则返回 None
        """
        # A 类型系列：共识文件在 object_dir 下
        if self.group_type in ("a_series", "a_object") and self.object_dir:
            return os.path.join(self.object_dir, ".series_consensus.json")

        # B 类型系列：根据图像所在父目录确定系列文件夹
        # 若父目录等于输入根目录（即根目录扁平 C 类型），不生成共识路径
        if self.group_type == "b" and self.image_paths:
            series_folder = os.path.dirname(self.image_paths[0])
            # 根目录扁平（C 类型）：跳过共识文件
            if os.path.normpath(series_folder) == os.path.normpath(self.root_dir):
                return None
            # 子目录（B 类型）：在该系列文件夹生成共识文件
            return os.path.join(series_folder, ".series_consensus.json")

        return None

def is_image_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in IMAGE_EXTS

def list_image_files(dir_path: str) -> List[str]:
    files: List[str] = []
    for root, _, filenames in os.walk(dir_path):
        for fn in filenames:
            fp = os.path.join(root, fn)
            if is_image_file(fp):
                files.append(fp)
    return sorted(files)

def extract_prefix(filepath: str) -> str:
    """
    依据文件名规则 id-1、id-2 提取前缀 id。
    若不匹配末尾 -数字 的模式，则退化为完整不含扩展名的文件名。
    """
    name = os.path.splitext(os.path.basename(filepath))[0]
    m = re.match(r'^(.*?)-(\d+)$', name)
    if m:
        return m.group(1)
    return name

def group_by_prefix(files: List[str]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for f in files:
        gid = extract_prefix(f)
        groups.setdefault(gid, []).append(f)
    return groups

def discover_image_groups(input_root: str) -> List[ImageGroup]:
    """
    发现并返回需要处理的图像分组，遵循文档的类型a/类型b与series优先处理规则。
    - 类型b：根目录下直接存在图片，按 id 前缀聚合。
    - 类型a：存在子文件夹（如 pic/S1/），其中可能包含 series 子文件夹作为系列样本；对象图像仍按 id 前缀聚合。
    顺序：同一对象目录下，series 先于对象图像组。
    """
    groups: List[ImageGroup] = []

    try:
        entries = [os.path.join(input_root, e) for e in os.listdir(input_root)]
    except FileNotFoundError:
        logger.warning(f"input_root_not_found path={input_root}")
        return []

    # 类型b：根目录直接存放图片
    root_images = [os.path.join(input_root, e) for e in os.listdir(input_root)
                   if is_image_file(os.path.join(input_root, e))]
    if root_images:
        for gid, paths in group_by_prefix(root_images).items():
            groups.append(ImageGroup(
                group_id=gid,
                image_paths=sorted(paths),
                group_type='b',
                root_dir=input_root
            ))

    # 类型a：遍历子目录
    for entry in sorted(entries):
        if not os.path.isdir(entry):
            continue

        series_dir = os.path.join(entry, "series")
        # 先处理 series 子目录（样本集）
        if os.path.isdir(series_dir):
            series_files = list_image_files(series_dir)
            for gid, paths in group_by_prefix(series_files).items():
                groups.append(ImageGroup(
                    group_id=gid,
                    image_paths=sorted(paths),
                    group_type='a_series',
                    root_dir=input_root,
                    series_dir=series_dir,
                    object_dir=entry
                ))

        # 再处理对象图像组（排除 series 子目录的内容）
        obj_files: List[str] = []
        for root, dirs, files in os.walk(entry):
            if os.path.basename(root) == "series":
                continue
            for fn in files:
                fp = os.path.join(root, fn)
                if is_image_file(fp):
                    obj_files.append(fp)

        if obj_files:
            for gid, paths in group_by_prefix(obj_files).items():
                groups.append(ImageGroup(
                    group_id=gid,
                    image_paths=sorted(paths),
                    group_type='a_object',
                    root_dir=input_root,
                    series_dir=series_dir if os.path.isdir(series_dir) else None,
                    object_dir=entry
                ))

    # series 优先于对象组，类型b最后
    order = {'a_series': 0, 'a_object': 1, 'b': 2}
    groups.sort(key=lambda g: (order.get(g.group_type, 9), g.object_dir or '', g.group_id))

    logger.info(f"image_groups_discovered root={input_root} count={len(groups)} "
                f"types={{'a_series': {sum(1 for g in groups if g.group_type=='a_series')}, "
                f"'a_object': {sum(1 for g in groups if g.group_type=='a_object')}, "
                f"'b': {sum(1 for g in groups if g.group_type=='b')}}}")

    return groups