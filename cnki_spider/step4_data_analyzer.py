           
"""
第四步：相关性分析模块
选择excel进行数据分析，调用大模型分析并给出评分，添加到当前行的新增列中
"""

import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import time
import threading
from datetime import datetime
from openai import OpenAI

class DataAnalyzer:
    """相关性分析类"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.selected_file = None
        self.analysis_results = []
        self.config = self.load_config()
        self.is_analyzing = False
        self.stop_analysis = False  # 添加停止标志
    
    def reset_stop_flag(self):
        """重置停止标志"""
        self.stop_analysis = False
    
    def stop_current_analysis(self):
        """停止当前分析"""
        self.stop_analysis = True
    
    def load_config(self):
        """加载配置文件"""
        try:
            if self.config_manager:
                return self.config_manager.config
            else:
                with open('config.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"无法加载配置文件: {str(e)}")
            return {}
    
    def get_analysis_status(self, file_path, progress_callback=None):
        """获取分析状态"""
        try:
            # 根据文件扩展名选择合适的引擎
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path, engine='openpyxl')
            elif file_path.endswith('.xls'):
                try:
                    df = pd.read_excel(file_path, engine='xlrd')
                except:
                    # 如果xlrd失败，尝试openpyxl
                    df = pd.read_excel(file_path, engine='openpyxl')
            else:
                # 尝试自动检测
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                except:
                    df = pd.read_excel(file_path, engine='xlrd')
            
            total = len(df)
            processed = 0
            failed = 0
            
            # 检查是否有分析状态列
            if '分析状态' in df.columns:
                processed = len(df[df['分析状态'] == '已完成'])
                failed = len(df[df['分析状态'].str.contains('错误|失败', na=False)])
            elif '相关性评分' in df.columns:
                # 如果没有分析状态列但有相关性评分列，检查评分不为0的记录
                processed = len(df[df['相关性评分'] > 0])
            
            remaining = total - processed - failed
            
            # 如果全部数据已分析完成，直接显示统计结果
            if remaining == 0 and processed > 0 and progress_callback:
                score_stats = self.generate_score_statistics(df)
                self.display_score_statistics(score_stats, progress_callback)
            
            return {
                'total': total,
                'processed': processed,
                'failed': failed,
                'remaining': remaining
            }
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"读取文件出错: {str(e)}")
            return {
                'total': 0,
                'processed': 0,
                'failed': 0,
                'remaining': 0
            }
    
    def analyze_data(self, file_path, progress_callback=None, stop_event=None):
        """分析数据的主要方法"""
        try:
            # 读取Excel文件
            if progress_callback:
                progress_callback(0, "正在读取Excel文件...")
            
            # 根据文件扩展名选择合适的引擎
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path, engine='openpyxl')
            elif file_path.endswith('.xls'):
                df = pd.read_excel(file_path, engine='xlrd')
            else:
                # 尝试自动检测
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                except:
                    df = pd.read_excel(file_path, engine='xlrd')
            
            if progress_callback:
                progress_callback(10, f"成功读取 {len(df)} 条文献数据")
            
            # 添加新列用于存储评分结果
            if '相关性评分' not in df.columns:
                df['相关性评分'] = 0
            if '评分理由' not in df.columns:
                df['评分理由'] = ''
            if '分析状态' not in df.columns:
                df['分析状态'] = '待分析'
            
            total_rows = len(df)
            processed_count = 0
            
            for index, row in df.iterrows():
                # 检查是否需要停止分析
                if stop_event and stop_event.is_set():
                    if progress_callback:
                        progress_callback(
                            processed_count / total_rows * 100,
                            f"分析已停止，已完成 {processed_count}/{total_rows} 条文献"
                        )
                    break
                
                # 跳过已经分析过的记录
                if df.at[index, '分析状态'] == '已完成':
                    processed_count += 1
                    continue
                
                if progress_callback:
                    progress = (processed_count / total_rows) * 100
                    progress_callback(progress, f"正在分析第 {index + 1}/{total_rows} 条文献...")
                
                try:
                    # 提取文献信息
                    title = str(row.get('Title-题名', ''))
                    keywords = str(row.get('Keyword-关键词', ''))
                    abstract = str(row.get('Summary-摘要', ''))
                    
                    # 调用大模型进行评分
                    result = self.call_llm_for_scoring("智慧教育", title, abstract, keywords)
                    
                    if result:
                        df.at[index, '相关性评分'] = result.get('score', 0)
                        df.at[index, '评分理由'] = result.get('reason', '')
                        df.at[index, '分析状态'] = '已完成'
                        
                        if progress_callback:
                            progress_callback(
                                (processed_count + 1) / total_rows * 100,
                                f"第 {index + 1} 条文献分析完成，评分: {result.get('score', 0)}"
                            )
                    else:
                        df.at[index, '分析状态'] = '分析失败'
                        if progress_callback:
                            progress_callback(
                                (processed_count + 1) / total_rows * 100,
                                f"第 {index + 1} 条文献分析失败"
                            )
                
                except Exception as e:
                    df.at[index, '分析状态'] = f'错误: {str(e)}'
                    if progress_callback:
                        progress_callback(
                            (processed_count + 1) / total_rows * 100,
                            f"第 {index + 1} 条文献分析出错: {str(e)}"
                        )
                
                processed_count += 1
                
                # 短暂延迟避免API调用过快
                time.sleep(0.5)
                
                # 每处理3条记录保存一次
                if processed_count % 3 == 0:
                    self.save_analyzed_file(df, file_path)
            
            # 最终保存
            self.save_analyzed_file(df, file_path)
            
            # 生成评分统计
            score_stats = self.generate_score_statistics(df)
            
            if progress_callback:
                progress_callback(100, "分析完成！")
                # 显示统计结果
                self.display_score_statistics(score_stats, progress_callback)
            
            return True
            
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"分析失败: {str(e)}")
            raise e
    
    def call_llm_for_scoring(self, research_topic, title, abstract, keywords, max_retries=3):
        """调用大模型对单篇文献进行评分"""
        for attempt in range(max_retries):
            try:
                # 获取系统提示词
                system_prompt = self.config.get('prompts', {}).get('prompt2', {}).get('content', '')
                if not system_prompt:
                    system_prompt = """你是一个文献相关性评估专家。请根据给定的研究主题，评估文献的相关性。

评分标准：
- 9-10分：高度相关，文献主要内容直接针对研究主题
- 7-8分：相关性较高，文献内容与研究主题密切相关
- 5-6分：中等相关，文献部分内容涉及研究主题
- 3-4分：相关性较低，文献仅略微涉及研究主题
- 1-2分：几乎无关，文献与研究主题基本无关

请以JSON格式返回结果：{"score": 评分, "reason": "评分理由"}"""
                
                # 构建用户提示词
                user_prompt = f"""研究主题: {research_topic}

文献信息:
- 标题: {title}
- 摘要: {abstract}
- 关键词: {keywords}

请评估该文献与研究主题的相关性并给出评分。"""
                
                # 调用大模型API
                response = self.call_llm_api(system_prompt, user_prompt)
                
                # 解析响应
                result = self.parse_llm_response(response)
                if result:
                    return result
                else:
                    raise Exception("无法解析大模型响应")
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                else:
                    return {
                        'score': 0,
                        'reason': f'分析失败: {str(e)}'
                    }
        
        return None
    
    def call_llm_api(self, system_prompt, user_prompt):
        """调用大模型API"""
        try:
            # 从配置文件获取API参数
            default_settings = self.config.get('default_settings', {})
            api_key = default_settings.get('api_key', '')
            base_url = default_settings.get('base_url', 'https://open.bigmodel.cn/api/paas/v4/')
            model = default_settings.get('ai_model', 'glm-4.5-flash')
            temperature = default_settings.get('temperature', 0.6)
            top_p = default_settings.get('top_p', 0.9)
            
            if not api_key:
                raise Exception("API密钥未配置")
            
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            
            # 调用API
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                top_p=top_p
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"调用大模型API失败: {str(e)}")
    
    def parse_llm_response(self, response):
        """解析大模型响应"""
        try:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{[^}]*\}', response)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 验证结果格式
                if 'score' in result and 'reason' in result:
                    # 确保评分在1-10范围内
                    score = int(result['score'])
                    if 1 <= score <= 10:
                        return {
                            'score': score,
                            'reason': str(result['reason'])
                        }
            
            # 如果JSON解析失败，尝试从文本中提取评分
            score_match = re.search(r'(\d+)分', response)
            if score_match:
                score = int(score_match.group(1))
                if 1 <= score <= 10:
                    return {
                        'score': score,
                        'reason': response
                    }
            
            return None
            
        except Exception as e:
            return None
    
    def save_analyzed_file(self, df, output_path):
        """保存分析结果"""
        try:
            # 根据文件扩展名选择保存格式
            if output_path.endswith('.xlsx'):
                df.to_excel(output_path, index=False, engine='openpyxl')
            elif output_path.endswith('.xls'):
                df.to_excel(output_path, index=False, engine='xlwt')
            else:
                # 默认保存为xlsx格式
                if not output_path.endswith('.xlsx'):
                    output_path += '.xlsx'
                df.to_excel(output_path, index=False, engine='openpyxl')
            
            return True
            
        except Exception as e:
            raise Exception(f"保存文件失败: {str(e)}")
    
    def generate_score_statistics(self, df):
        """生成评分统计信息"""
        try:
            # 筛选已完成分析的数据
            completed_df = df[df['分析状态'] == '已完成']
            
            if len(completed_df) == 0:
                return {
                    'total': 0,
                    'score_9_10': 0,
                    'score_8_9': 0,
                    'score_7_8': 0,
                    'score_6_7': 0,
                    'score_below_6': 0
                }
            
            # 统计各分数段的数量
            scores = completed_df['相关性评分'].astype(float)
            
            score_9_10 = len(scores[(scores >= 9) & (scores <= 10)])
            score_8_9 = len(scores[(scores >= 8) & (scores < 9)])
            score_7_8 = len(scores[(scores >= 7) & (scores < 8)])
            score_6_7 = len(scores[(scores >= 6) & (scores < 7)])
            score_below_6 = len(scores[scores < 6])
            
            return {
                'total': len(completed_df),
                'score_9_10': score_9_10,
                'score_8_9': score_8_9,
                'score_7_8': score_7_8,
                'score_6_7': score_6_7,
                'score_below_6': score_below_6
            }
            
        except Exception as e:
            return {
                'total': 0,
                'score_9_10': 0,
                'score_8_9': 0,
                'score_7_8': 0,
                'score_6_7': 0,
                'score_below_6': 0,
                'error': str(e)
            }
    
    def display_score_statistics(self, stats, progress_callback):
        """在日志窗口显示评分统计结果"""
        try:
            if stats['total'] == 0:
                progress_callback(100, "暂无已完成分析的数据进行统计")
                return
            
            # 构建统计信息字符串
            stats_message = f"""
=== 评分统计结果 ===
总计已分析文献: {stats['total']} 条

分数段统计:
• 9-10分 (高度相关): {stats['score_9_10']} 条 ({stats['score_9_10']/stats['total']*100:.1f}%)
• 8-9分 (相关性较高): {stats['score_8_9']} 条 ({stats['score_8_9']/stats['total']*100:.1f}%)
• 7-8分 (中等相关): {stats['score_7_8']} 条 ({stats['score_7_8']/stats['total']*100:.1f}%)
• 6-7分 (相关性较低): {stats['score_6_7']} 条 ({stats['score_6_7']/stats['total']*100:.1f}%)
• 6分以下 (几乎无关): {stats['score_below_6']} 条 ({stats['score_below_6']/stats['total']*100:.1f}%)

高质量文献 (7分以上): {stats['score_9_10'] + stats['score_8_9'] + stats['score_7_8']} 条 ({(stats['score_9_10'] + stats['score_8_9'] + stats['score_7_8'])/stats['total']*100:.1f}%)
=================="""
            
            # 分行显示统计信息
            for line in stats_message.strip().split('\n'):
                if line.strip():
                    progress_callback(100, line.strip())
                    time.sleep(0.1)  # 短暂延迟以便用户阅读
            
        except Exception as e:
            progress_callback(100, f"显示统计信息时出错: {str(e)}")

if __name__ == "__main__":
    # 测试代码
    analyzer = DataAnalyzer(None)
    
    # 测试分析功能
    test_file = "examples/CNKI_export_20250814_164337.xls"
    
    if os.path.exists(test_file):
        try:
            success = analyzer.analyze_data(
                test_file,
                progress_callback=lambda progress, msg: print(f"进度 {progress:.1f}%: {msg}")
            )
            print("分析完成!" if success else "分析失败!")
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print(f"测试文件不存在: {test_file}")