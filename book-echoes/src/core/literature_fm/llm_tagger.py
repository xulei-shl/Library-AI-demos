"""
LLM打标器
负责调用LLM为书目生成情境标签
"""

import json
import time
from typing import Dict, List, Optional
from pathlib import Path
import yaml

from src.utils.logger import get_logger
from src.utils.llm.client import UnifiedLLMClient
from .tag_manager import TagManager

logger = get_logger(__name__)


class LLMTagger:
    """负责调用LLM为书目生成标签"""
    
    def __init__(self, config: dict):
        """
        Args:
            config: llm_tagging配置字典
        """
        self.config = config
        self.llm_client = UnifiedLLMClient()
        self.tag_manager = TagManager()
        self.vocabulary = self._load_vocabulary()
        self.prompt_template = self._load_prompt_template()
    
    def _load_vocabulary(self) -> dict:
        """加载标签词表"""
        vocab_path = self.config.get('vocabulary_file')
        if not vocab_path:
            raise ValueError("vocabulary_file 未配置")
        
        vocab_file = Path(vocab_path)
        if not vocab_file.exists():
            raise FileNotFoundError(f"标签词表文件不存在: {vocab_path}")
        
        with open(vocab_file, 'r', encoding='utf-8') as f:
            vocabulary = yaml.safe_load(f)
        
        logger.info(f"✓ 标签词表加载成功: {vocab_path}")
        return vocabulary
    
    def _load_prompt_template(self) -> str:
        """加载Prompt模板"""
        prompt_config = self.config.get('prompt', {})
        fallback_file = prompt_config.get('fallback_file', 'prompts/literary_tagging.md')
        
        prompt_file = Path(fallback_file)
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt模板文件不存在: {fallback_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            template = f.read()
        
        logger.info(f"✓ Prompt模板加载成功: {fallback_file}")
        return template
    
    def tag_books(self, books: List[Dict]) -> Dict[str, int]:
        """
        批量打标
        
        Args:
            books: 书目列表，每个元素包含 id, title, author, douban_summary 等
            
        Returns:
            Dict[str, int]: 统计信息 {'success': 10, 'failed': 2}
        """
        if not books:
            logger.warning("待打标书目列表为空")
            return {'success': 0, 'failed': 0}
        
        batch_config = self.config.get('batch_processing', {})
        batch_size = batch_config.get('batch_size', 10)
        delay = batch_config.get('delay_between_batches', 2)
        show_progress = batch_config.get('show_progress', True)
        
        stats = {'success': 0, 'failed': 0}
        total_batches = (len(books) - 1) // batch_size + 1
        
        logger.info(f"开始批量打标，共 {len(books)} 本书，分 {total_batches} 批处理")
        
        for i in range(0, len(books), batch_size):
            batch = books[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            if show_progress:
                logger.info(f"{'='*60}")
                logger.info(f"处理批次 {batch_num}/{total_batches} (共 {len(batch)} 本)")
                logger.info(f"{'='*60}")
            
            for idx, book in enumerate(batch, 1):
                if show_progress:
                    logger.info(f"[{batch_num}-{idx}/{len(batch)}] 正在处理: {book.get('title', 'Unknown')}")
                
                success = self._tag_single_book(book)
                
                if success:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
            
            # 批次间延迟
            if i + batch_size < len(books):
                logger.info(f"批次完成，等待 {delay} 秒后继续...")
                time.sleep(delay)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"批量打标完成！成功: {stats['success']}, 失败: {stats['failed']}")
        logger.info(f"{'='*60}\n")
        
        return stats
    
    def _tag_single_book(self, book: Dict) -> bool:
        """
        为单本书打标
        
        Args:
            book: 书目信息字典
            
        Returns:
            bool: 是否成功
        """
        try:
            # 1. 构建Prompt
            user_prompt = self._build_user_prompt(book)
            
            # 2. 调用LLM
            response = self.llm_client.call(
                task_name='literary_tagging',
                user_prompt=user_prompt
            )
            
            # 3. 解析响应
            tags_data = self._parse_response(response)
            
            # 4. 验证标签数据
            if not self._validate_tags(tags_data):
                raise ValueError("标签数据验证失败")
            
            # 5. 获取使用的模型信息（从配置中读取）
            llm_model, llm_provider = self._get_model_info()
            
            # 6. 保存到数据库
            book_title = book.get('douban_title') or book.get('book_title', '')
            self.tag_manager.save_tags(
                book_id=book['id'],
                call_no=book.get('call_no', ''),
                title=book_title,
                tags_json=json.dumps(tags_data, ensure_ascii=False),
                llm_model=llm_model,
                llm_provider=llm_provider,
                llm_status='success'
            )
            
            logger.info(f"  ✓ 打标成功")
            return True
            
        except Exception as e:
            logger.error(f"  ✗ 打标失败: {str(e)}")
            
            # 记录失败状态
            self.tag_manager.save_tags(
                book_id=book['id'],
                call_no=book.get('call_no', ''),
                title=book.get('title', ''),
                tags_json='',
                llm_model='',
                llm_provider='',
                llm_status='failed',
                error_message=str(e)[:500]
            )
            
            return False
    
    def _get_model_info(self) -> tuple:
        """
        从配置中获取模型信息

        Returns:
            tuple: (model_name, provider_name)
        """
        try:
            # 从 llm.yaml 配置中获取
            task_config = self.llm_client.get_task_config('literary_tagging')
            provider_type = task_config.get('provider_type', 'text')

            api_providers = self.llm_client.settings.get('api_providers', {})
            provider_group = api_providers.get(provider_type, {})

            # 优先使用 primary，其次是 secondary
            primary = provider_group.get('primary', {})
            provider_info = primary or provider_group.get('secondary', {})

            if provider_info:
                model_name = provider_info.get('model', 'unknown')
                provider_name = provider_info.get('name', 'unknown')
                return model_name, provider_name

            return 'unknown', 'unknown'

        except Exception as e:
            logger.warning(f"获取模型信息失败: {str(e)}")
            return 'unknown', 'unknown'
    
    def _build_user_prompt(self, book: Dict) -> str:
        """
        构建用户提示词（动态注入词表）

        Args:
            book: 书目信息

        Returns:
            str: 完整的用户提示词
        """
        # 1. 构建标签候选词部分
        tags_section = self._build_tags_section()

        # 2. 构建书目信息部分
        book_info = self._build_book_info(book)

        # 3. 构建用户提示词（只包含用户需要看到的部分：标签词表 + 书目信息）
        user_prompt = f"""# Vocabulary (候选标签词表)

{tags_section}

# Output Format

请严格遵守以下 JSON 格式，不要包含任何 Markdown 代码块标记（如 ```json），直接输出纯文本 JSON：

{{
  "reasoning": "这里填写你的推理过程。例如：本书是马尔克斯的代表作，属于魔幻现实主义。虽然故事精彩，但人物关系复杂，叙事跨度大，需要读者保持专注（需正襟危坐）。文字风格华丽且充满隐喻（浓墨重彩/诗意流动），氛围带有浓重的历史宿命感（历史回响）。",
  "reading_context": ["标签1", "标签2"],
  "reading_load": ["标签1"],
  "text_texture": ["标签1", "标签2"],
  "spatial_atmosphere": ["标签1"],
  "emotional_tone": ["标签1", "标签2"],
  "confidence_scores": {{
    "reading_context": 0.85,
    "reading_load": 0.90,
    "text_texture": 0.88,
    "spatial_atmosphere": 0.92,
    "emotional_tone": 0.80
  }}
}}

{book_info}"""

        return user_prompt

    def _build_book_info(self, book: Dict) -> str:
        """构建书目信息部分"""
        # 优先使用 douban_title，其次用 book_title
        title = book.get('douban_title') or book.get('book_title', 'Unknown')
        # 优先使用 douban_author，其次用 author
        author = book.get('douban_author') or book.get('author', 'Unknown')

        return f"""## 待打标书目信息

- **书名**: {title}
- **作者**: {author}
- **出版年份**: {book.get('douban_pub_year', 'Unknown')}
- **豆瓣评分**: {book.get('douban_rating', 'N/A')}
- **内容简介**:
{book.get('douban_summary', '无简介')}
"""
    
    def _build_tags_section(self) -> str:
        """构建标签候选词部分"""
        dimensions = self.vocabulary.get('tag_dimensions', {})
        prompt_config = self.vocabulary.get('prompt_config', {})
        include_desc = prompt_config.get('include_descriptions', True)
        
        sections = []
        
        for dim_key, dim_data in dimensions.items():
            section_lines = [f"### {dim_data['description']}"]
            section_lines.append("")
            
            for candidate in dim_data.get('candidates', []):
                label = candidate.get('label', '')
                desc = candidate.get('description', '')
                
                if include_desc and desc:
                    section_lines.append(f"- **{label}**: {desc}")
                else:
                    section_lines.append(f"- {label}")
            
            sections.append("\n".join(section_lines))
        
        return "\n\n".join(sections)
    
    def _parse_response(self, response: str) -> dict:
        """
        解析LLM响应
        
        Args:
            response: LLM返回的JSON字符串或字典
            
        Returns:
            dict: 解析后的标签数据
        """
        # UnifiedLLMClient 已启用 json_repair，这里直接解析
        if isinstance(response, str):
            return json.loads(response)
        return response
    
    def _validate_tags(self, tags_data: dict) -> bool:
        """
        验证标签数据的有效性
        
        Args:
            tags_data: 标签数据字典
            
        Returns:
            bool: 是否有效
        """
        required_keys = [
            'reading_context',
            'reading_load',
            'text_texture',
            'spatial_atmosphere',
            'emotional_tone',
            'confidence_scores'
        ]
        
        # 检查必需字段
        for key in required_keys:
            if key not in tags_data:
                logger.warning(f"标签数据缺少字段: {key}")
                return False
        
        # 检查置信度阈值
        confidence_threshold = self.vocabulary.get('prompt_config', {}).get('confidence_threshold', 0.65)
        confidence_scores = tags_data.get('confidence_scores', {})
        
        for dim, score in confidence_scores.items():
            if score < confidence_threshold:
                logger.warning(f"维度 {dim} 的置信度 {score} 低于阈值 {confidence_threshold}")
        
        return True
    
    def fallback_retry(self) -> Dict[str, int]:
        """
        兜底重试（对失败记录重新打标）
        
        Returns:
            Dict[str, int]: 重试统计 {'success': 5, 'failed': 1}
        """
        retry_config = self.config.get('retry_strategy', {})
        
        if not retry_config.get('fallback_retry_enabled', False):
            logger.info("兜底重试未启用，跳过")
            return {'success': 0, 'failed': 0}
        
        max_retries = retry_config.get('fallback_max_retries', 2)
        delay = retry_config.get('fallback_delay', 5)
        
        # 获取失败记录
        failed_records = self.tag_manager.get_failed_records(max_retry_count=max_retries)
        
        if not failed_records:
            logger.info("没有需要兜底重试的记录")
            return {'success': 0, 'failed': 0}
        
        logger.info(f"\n{'='*60}")
        logger.info(f"开始兜底重试，共 {len(failed_records)} 条记录")
        logger.info(f"{'='*60}\n")
        
        stats = {'success': 0, 'failed': 0}
        
        for idx, record in enumerate(failed_records, 1):
            logger.info(f"[{idx}/{len(failed_records)}] 重试: {record.get('title', 'Unknown')}")
            
            time.sleep(delay)
            
            # 重新打标
            success = self._tag_single_book(record)
            
            if success:
                stats['success'] += 1
            else:
                # 更新重试计数
                self.tag_manager.update_status(
                    book_id=record['id'],
                    llm_status='failed',
                    increment_retry=True
                )
                stats['failed'] += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"兜底重试完成！成功: {stats['success']}, 失败: {stats['failed']}")
        logger.info(f"{'='*60}\n")
        
        return stats