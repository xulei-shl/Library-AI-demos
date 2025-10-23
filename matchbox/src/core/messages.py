# -*- coding: utf-8 -*-
import os
from typing import List, Optional, Dict, Any
from src.utils.llm_api import image_to_base64
from src.utils.logger import get_logger

logger = get_logger(__name__)

MIME_MAP = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
    '.gif': 'image/gif',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.avif': 'image/avif',
}

def guess_mime_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return MIME_MAP.get(ext, 'image/png')

def load_text_file(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f'system_prompt_not_found path={path}')
        return ''

def make_image_part(path: str, *, as_data_url: bool = True) -> Dict[str, Any]:
    b64 = image_to_base64(path)
    mime = guess_mime_type(path)
    if as_data_url:
        return {
            'type': 'image_url',
            'image_url': {
                'url': f'data:{mime};base64,{b64}'
            }
        }
    else:
        return {
            'type': 'input_image',
            'input_image': {
                'data': b64,
                'mime_type': mime
            }
        }

def build_vision_user_content(text: Optional[str], image_paths: List[str], *, as_data_url: bool = True) -> List[Dict[str, Any]]:
    content: List[Dict[str, Any]] = []
    if text:
        content.append({'type': 'text', 'text': str(text)})
    for p in image_paths:
        content.append(make_image_part(p, as_data_url=as_data_url))
    return content

def build_messages(system_prompt_file: str, user_text: Optional[str], image_paths: List[str], *, as_data_url: bool = True) -> List[Dict[str, Any]]:
    system_prompt = load_text_file(system_prompt_file)
    messages: List[Dict[str, Any]] = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    else:
        messages.append({'role': 'system', 'content': ''})
    messages.append({
        'role': 'user',
        'content': build_vision_user_content(user_text, image_paths, as_data_url=as_data_url)
    })
    return messages

def build_messages_for_task(task_name: str, settings: Dict[str, Any], user_text: Optional[str], image_paths: List[str], *, as_data_url: bool = True) -> List[Dict[str, Any]]:
    task_cfg = settings.get('tasks', {}).get(task_name, {})
    system_prompt_file = task_cfg.get('system_prompt_file', '')
    if not system_prompt_file:
        logger.warning(f'missing_system_prompt task={task_name}')
    return build_messages(system_prompt_file, user_text, image_paths, as_data_url=as_data_url)