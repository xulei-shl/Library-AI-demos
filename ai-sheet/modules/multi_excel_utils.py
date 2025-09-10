#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""  
多Excel多Sheet处理工具模块
提供多Excel文件解析、验证和预览生成等功能
"""

import os
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from modules.config_manager import MultiModelConfigManager
from modules.excel_utils import validate_excel_file, format_file_size


class MultiExcelManager:
    """多Excel多Sheet管理器"""
    
    def __init__(self):
        self.config = self._get_excel_config()
        self.excel_files = {}  # {file_path: {sheets: [], data: {}}}
        
    def _get_excel_config(self):
        """获取Excel相关配置"""
        config_manager = MultiModelConfigManager()
        return config_manager.get_excel_config()
    
    def add_excel_file(self, file_path: str) -> Tuple[bool, str, List[str]]:
        """添加Excel文件并获取Sheet列表
        
        参数:
            file_path: Excel文件路径
            
        返回:
            (是否成功, 错误信息, Sheet列表)
        """
        # 验证文件
        is_valid, error_msg = validate_excel_file(file_path)
        if not is_valid:
            return False, error_msg, []
        
        try:
            # 获取所有Sheet名称
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # 存储文件信息
            self.excel_files[file_path] = {
                'sheets': sheet_names,
                'data': {},
                'file_info': {
                    'name': os.path.basename(file_path),
                    'size': os.path.getsize(file_path),
                    'total_sheets': len(sheet_names)
                }
            }
            
            return True, "", sheet_names
            
        except Exception as e:
            return False, f"读取Excel文件失败: {str(e)}", []
    
    def remove_excel_file(self, file_path: str) -> bool:
        """移除Excel文件"""
        if file_path in self.excel_files:
            del self.excel_files[file_path]
            return True
        return False
    
    def get_sheet_data(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """获取指定Sheet的数据
        
        参数:
            file_path: Excel文件路径
            sheet_name: Sheet名称
            
        返回:
            Sheet数据字典
        """
        if file_path not in self.excel_files:
            raise ValueError(f"Excel文件未加载: {file_path}")
        
        # 检查是否已缓存
        cache_key = f"{file_path}#{sheet_name}"
        if cache_key in self.excel_files[file_path]['data']:
            return self.excel_files[file_path]['data'][cache_key]
        
        try:
            # 读取Sheet数据
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # 检查数据行数，超出限制时截取
            total_rows = len(df)
            max_rows = self.config['max_rows']
            if total_rows > max_rows:
                df = df.iloc[:max_rows]
                truncated = True
            else:
                truncated = False
            
            # 生成列名列表
            columns = [f"{chr(65+i)}列-{col}" for i, col in enumerate(df.columns)]
            
            # 生成预览数据
            preview_rows = self.config['preview_rows']
            preview = self._generate_markdown_preview(df, preview_rows)
            
            sheet_data = {
                'data': df,
                'preview': preview,
                'total_rows': total_rows,
                'truncated': truncated,
                'columns': columns,
                'column_names': list(df.columns),
                'sheet_name': sheet_name
            }
            
            # 缓存数据
            self.excel_files[file_path]['data'][cache_key] = sheet_data
            
            return sheet_data
            
        except Exception as e:
            raise Exception(f"读取Sheet数据失败: {str(e)}")
    
    def _generate_markdown_preview(self, df: pd.DataFrame, rows: int = 5) -> str:
        """生成Markdown格式的数据预览"""
        if df.empty:
            return "*数据为空*"
        
        # 取前N行数据
        preview_df = df.head(rows)
        
        # 构建Markdown表格
        header = "| " + " | ".join(f"{chr(65+i)}-{col}" for i, col in enumerate(preview_df.columns)) + " |"
        separator = "| " + " | ".join(["-" * max(len(str(col)), 3) for col in preview_df.columns]) + " |"
        
        rows_md = []
        for _, row in preview_df.iterrows():
            # 处理特殊字符和空值
            row_values = [str(val).replace("|", "\\|").replace("\n", " ") if pd.notna(val) else "" for val in row]
            rows_md.append("| " + " | ".join(row_values) + " |")
        
        return "\n".join([header, separator] + rows_md)
    
    def get_all_files(self) -> List[str]:
        """获取所有已加载的Excel文件路径"""
        return list(self.excel_files.keys())
    
    def get_file_sheets(self, file_path: str) -> List[str]:
        """获取指定文件的所有Sheet名称"""
        if file_path in self.excel_files:
            return self.excel_files[file_path]['sheets']
        return []
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        if file_path in self.excel_files:
            return self.excel_files[file_path]['file_info']
        return {}
    
    def clear_all(self):
        """清除所有数据"""
        self.excel_files.clear()
    
    def generate_combined_preview(self, selections: List[Tuple]) -> str:
        """生成多个文件-Sheet组合的预览
        
        参数:
            selections: [(file_path, sheet_name), ...] 或 [(file_path, sheet_name, selected_columns), ...] 选择的文件-Sheet组合
            
        返回:
            组合预览的Markdown字符串
        """
        if not selections:
            return "*请选择要预览的Excel文件和Sheet*"
        
        preview_parts = []
        
        for selection in selections:
            # 兼容旧格式和新格式
            if len(selection) == 2:
                file_path, sheet_name = selection
                selected_columns = []
            elif len(selection) == 3:
                file_path, sheet_name, selected_columns = selection
            else:
                continue  # 跳过无效的选择
            
            try:
                # 获取文件名
                file_name = os.path.basename(file_path)
                
                # 获取Sheet数据
                sheet_data = self.get_sheet_data(file_path, sheet_name)
                
                # 添加标题
                preview_parts.append(f"## 📊 {file_name} - {sheet_name}")
                
                # 根据是否有选中列显示不同信息
                if selected_columns:
                    preview_parts.append(f"**总行数:** {sheet_data['total_rows']} | **已选列数:** {len(selected_columns)} / {len(sheet_data['column_names'])}")
                    preview_parts.append(f"**选中列:** {', '.join(selected_columns)}")
                else:
                    preview_parts.append(f"**总行数:** {sheet_data['total_rows']} | **列数:** {len(sheet_data['column_names'])}")
                    preview_parts.append("**选中列:** 全部列")
                
                preview_parts.append("")
                
                # 生成过滤后的预览
                if selected_columns:
                    from modules.column_utils import generate_filtered_preview
                    filtered_preview = generate_filtered_preview(sheet_data, selected_columns, self.config['preview_rows'])
                    preview_parts.append(filtered_preview)
                else:
                    preview_parts.append(sheet_data['preview'])
                
                preview_parts.append("")
                
            except Exception as e:
                preview_parts.append(f"## ❌ {os.path.basename(file_path)} - {sheet_name}")
                preview_parts.append(f"*读取失败: {str(e)}*")
                preview_parts.append("")
        
        return "\n".join(preview_parts)
    
    def export_selections_info(self, selections: List[Tuple]) -> Dict[str, Any]:
        """导出选择的文件-Sheet信息，供其他模块使用
        
        参数:
            selections: [(file_path, sheet_name, selected_columns), ...] 选择的文件-Sheet组合
            
        返回:
            包含所有选择信息的字典
        """
        # 提取文件路径用于统计
        file_paths = []
        for selection in selections:
            if len(selection) >= 2:
                file_paths.append(selection[0])
        
        export_data = {
            'selections': [],
            'total_files': len(set(file_paths)),
            'total_sheets': len(selections),
            'combined_preview': self.generate_combined_preview(selections)
        }
        
        for selection in selections:
            # 兼容旧格式和新格式
            if len(selection) == 2:
                file_path, sheet_name = selection
                selected_columns = []
            else:
                file_path, sheet_name, selected_columns = selection
            try:
                sheet_data = self.get_sheet_data(file_path, sheet_name)
                file_info = self.get_file_info(file_path)
                
                selection_info = {
                    'file_path': file_path,
                    'file_name': file_info.get('name', os.path.basename(file_path)),
                    'file_size': file_info.get('size', 0),
                    'sheet_name': sheet_name,
                    'total_rows': sheet_data['total_rows'],
                    'columns': sheet_data['columns'],
                    'column_names': sheet_data['column_names'],
                    'selected_columns': selected_columns,
                    'preview': sheet_data['preview'],
                    'truncated': sheet_data['truncated']
                }
                
                export_data['selections'].append(selection_info)
                
            except Exception as e:
                # 添加错误信息
                error_info = {
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'sheet_name': sheet_name,
                    'error': str(e)
                }
                export_data['selections'].append(error_info)
        
        return export_data


def save_final_selections(manager: MultiExcelManager, selections: List[Tuple]) -> bool:
    """保存最终确认的选择（优化版，去除冗余）
    
    参数:
        manager: MultiExcelManager实例
        selections: 选择的文件-Sheet组合列表（支持列选择）
        
    返回:
        是否保存成功
    """
    try:
        # 确保logs目录存在
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # 检查并自动加载未加载的Excel文件
        loaded_files = manager.get_all_files()
        for selection in selections:
            # 兼容旧格式和新格式
            if len(selection) >= 2:
                file_path = selection[0]
                if file_path not in loaded_files:
                    print(f"检测到未加载的文件，正在加载: {file_path}")
                    success, error_msg, sheet_names = manager.add_excel_file(file_path)
                    if not success:
                        print(f"自动加载文件失败: {file_path}, 错误: {error_msg}")
                        # 继续处理其他文件，不中断整个流程
                    else:
                        print(f"文件加载成功: {file_path}, 包含 {len(sheet_names)} 个Sheet")
        
        # 导出选择信息
        export_data = manager.export_selections_info(selections)
        
        # 保存组合预览到MD文件（只保存预览）
        preview_file = os.path.join(logs_dir, "multi_excel_preview.md")
        with open(preview_file, 'w', encoding='utf-8') as f:
            f.write(export_data['combined_preview'])
        
        # 保存优化后的JSON文件（去除预览冗余）
        import json
        from datetime import datetime
        
        info_file = os.path.join(logs_dir, "multi_excel_selections.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            # 构建优化后的数据结构
            optimized_data = {
                'metadata': {
                    'saved_at': datetime.now().isoformat(),
                    'total_files': export_data['total_files'],
                    'total_sheets': export_data['total_sheets'],
                    'is_final': True
                },
                'selections': []
            }
            
            # 只保存结构化数据，移除预览冗余
            for selection in export_data['selections']:
                if 'error' not in selection:  # 只保存成功的选择
                    clean_selection = {
                        'file_path': selection['file_path'],
                        'file_name': selection['file_name'],
                        'file_size': selection.get('file_size', 0),
                        'sheet_name': selection['sheet_name'],
                        'total_rows': selection['total_rows'],
                        'columns': selection['columns'],
                        'column_names': selection['column_names'],
                        'selected_columns': selection.get('selected_columns', []),
                        'truncated': selection['truncated']
                    }
                    optimized_data['selections'].append(clean_selection)
                else:
                    # 保存错误信息但不包含预览
                    error_selection = {
                        'file_path': selection['file_path'],
                        'file_name': selection['file_name'],
                        'sheet_name': selection['sheet_name'],
                        'error': selection['error']
                    }
                    optimized_data['selections'].append(error_selection)
            
            json.dump(optimized_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 最终选择已保存到: {preview_file}, {info_file}")
        return True
        
    except Exception as e:
        print(f"❌ 保存最终选择失败：{e}")
        return False


def save_multi_excel_data_to_temp(manager: MultiExcelManager, selections: List[Tuple]) -> bool:
    """将多Excel数据保存到临时文件（兼容性保留）
    
    参数:
        manager: MultiExcelManager实例
        selections: 选择的文件-Sheet组合列表（支持列选择）
        
    返回:
        是否保存成功
    """
    # 调用新的优化版本
    return save_final_selections(manager, selections)


def load_multi_excel_data_from_temp() -> Optional[Dict[str, Any]]:
    """从临时文件加载多Excel数据
    
    返回:
        加载的数据字典，失败时返回None
    """
    try:
        import json
        info_file = os.path.join("logs", "multi_excel_selections.json")
        
        if not os.path.exists(info_file):
            return None
        
        with open(info_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 加载预览内容
        preview_file = os.path.join("logs", "multi_excel_preview.md")
        if os.path.exists(preview_file):
            with open(preview_file, 'r', encoding='utf-8') as f:
                data['combined_preview'] = f.read()
        
        return data
        
    except Exception as e:
        print(f"从临时文件加载多Excel数据失败：{e}")
        return None


def check_save_status(current_selections: List[Tuple]) -> Dict[str, Any]:
    """检查当前选择的保存状态
    
    参数:
        current_selections: 当前选择的文件-Sheet组合列表（支持列选择）
        
    返回:
        保存状态信息字典
    """
    try:
        import json
        from datetime import datetime
        
        info_file = os.path.join("logs", "multi_excel_selections.json")
        
        # 如果没有保存文件，返回未保存状态
        if not os.path.exists(info_file):
            return {
                'is_saved': False,
                'has_changes': len(current_selections) > 0,
                'saved_count': 0,
                'current_count': len(current_selections),
                'last_saved': None,
                'status_message': '尚未保存任何选择'
            }
        
        # 读取已保存的选择
        with open(info_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        # 提取已保存的选择（只比较成功的选择）
        saved_selections = []
        for selection in saved_data.get('selections', []):
            if 'error' not in selection:
                selected_columns = selection.get('selected_columns', [])
                saved_selections.append((selection['file_path'], selection['sheet_name'], tuple(selected_columns)))
        
        # 标准化当前选择格式
        normalized_current = []
        for selection in current_selections:
            if len(selection) == 2:
                file_path, sheet_name = selection
                normalized_current.append((file_path, sheet_name, tuple()))
            else:
                file_path, sheet_name, selected_columns = selection
                normalized_current.append((file_path, sheet_name, tuple(selected_columns)))
        
        # 比较当前选择与已保存选择
        current_set = set(normalized_current)
        saved_set = set(saved_selections)
        has_changes = current_set != saved_set
        
        return {
            'is_saved': not has_changes and len(current_selections) > 0,
            'has_changes': has_changes,
            'saved_count': len(saved_selections),
            'current_count': len(current_selections),
            'last_saved': saved_data.get('metadata', {}).get('saved_at'),
            'status_message': _get_status_message(has_changes, len(current_selections), len(saved_selections))
        }
        
    except Exception as e:
        return {
            'is_saved': False,
            'has_changes': True,
            'saved_count': 0,
            'current_count': len(current_selections),
            'last_saved': None,
            'status_message': f'检查状态失败: {str(e)}'
        }


def _get_status_message(has_changes: bool, current_count: int, saved_count: int) -> str:
    """生成状态提示消息"""
    if current_count == 0:
        return '请选择Excel文件和Sheet'
    elif not has_changes and current_count > 0:
        return f'✅ 已保存 {saved_count} 个选择'
    elif has_changes:
        if saved_count == 0:
            return f'⚠️ 请点击"保存"按钮确认 {current_count} 个选择'
        else:
            return f'⚠️ 选择已变更，请重新保存（当前 {current_count} 个，已保存 {saved_count} 个）'
    else:
        return '状态未知'


def get_unsaved_selections_count(current_selections: List[Tuple]) -> int:
    """获取未保存的选择数量
    
    参数:
        current_selections: 当前选择的文件-Sheet组合列表（支持列选择）
        
    返回:
        未保存的选择数量
    """
    status = check_save_status(current_selections)
    if status['has_changes']:
        return status['current_count']
    return 0


def get_save_status_info(current_selections: List[Tuple]) -> Dict[str, Any]:
    """获取保存状态信息（用于UI显示）
    
    参数:
        current_selections: 当前选择的文件-Sheet组合列表（支持列选择）
        
    返回:
        UI显示用的状态信息
    """
    status = check_save_status(current_selections)
    
    # 根据状态生成UI信息
    if status['is_saved']:
        ui_info = {
            'show_reminder': False,
            'reminder_type': 'success',
            'reminder_title': '✅ 已保存最终选择',
            'reminder_message': f"保存时间: {_format_datetime(status['last_saved'])}📊 可用于公式生成和提示词生成",
            'button_text': '重新保存',
            'button_style': 'secondary'
        }
    elif status['has_changes'] and status['current_count'] > 0:
        ui_info = {
            'show_reminder': True,
            'reminder_type': 'warning',
            'reminder_title': '⚠️ 请点击"保存"按钮确认选择',
            'reminder_message': f"当前已选择: {status['current_count']}个文件和Sheet需要保存后才能用于后续操作",
            'button_text': '📋 保存选择',
            'button_style': 'primary'
        }
    else:
        ui_info = {
            'show_reminder': False,
            'reminder_type': 'info',
            'reminder_title': '请选择Excel文件和Sheet',
            'reminder_message': '上传Excel文件并选择需要的Sheet',
            'button_text': '保存选择',
            'button_style': 'disabled'
        }
    
    # 添加原始状态信息
    ui_info.update(status)
    
    return ui_info


def _format_datetime(datetime_str: str) -> str:
    """格式化日期时间字符串"""
    if not datetime_str:
        return '未知'
    
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return datetime_str


def clear_multi_excel_temp_files():
    """清除多Excel临时文件"""
    try:
        temp_files = [
            os.path.join("logs", "multi_excel_preview.md"),
            os.path.join("logs", "multi_excel_selections.json")
        ]
        
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"临时文件已删除: {temp_file}")
                
    except Exception as e:
        print(f"清除多Excel临时文件失败：{e}")