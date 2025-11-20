#!/usr/bin/env python3
"""
书海回响 - 那些被悄悄归还一本好书

支持多个功能模块：
- 模块1: 月归还数据分析模块（借阅统计）
- 模块3: 豆瓣模块（ISBN获取、豆瓣评分等）

系统架构：
数据加载 -> 数据清洗 -> 时间筛选 -> 借阅统计 -> 结果输出 -> 智能降噪 -> 豆瓣功能（可选）
"""

import sys
import time
import subprocess
import os
from pathlib import Path

# 添加src目录到路径
sys.path.append(str(Path(__file__).parent / "src"))

from src.utils.logger import get_logger
from src.utils.config_manager import config as app_config, get_config

# 初始化日志
logger = get_logger(__name__)


def get_outputs_dir():
    """获取运行输出目录"""
    outputs_dir = Path(get_config('paths.outputs_dir', 'runtime/outputs'))
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir


def find_latest_module2_excel():
    """
    查找模块2生成的原始筛选结果Excel：
    格式严格为：月归还数据筛选结果_YYYYMMDD_HHMMSS.xlsx
    （不包含“豆瓣结果”“partial”“副本”等后缀）
    """
    outputs_dir = get_outputs_dir()
    candidates = sorted(
        outputs_dir.glob("月归还数据筛选结果_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    import re
    pattern = re.compile(r"^月归还数据筛选结果_\d{8}_\d{6}\.xlsx$")
    for p in candidates:
        if pattern.match(p.name):
            return p
    return None


def find_latest_module3_excel():
    """
    查找模块3生成的最终豆瓣结果Excel：
    格式严格为：月归还数据筛选结果_YYYYMMDD_HHMMSS_豆瓣结果_YYYYMMDD_HHMMSS.xlsx
    （过滤掉任何"partial""副本"等临时或中间文件）
    """
    outputs_dir = get_outputs_dir()
    candidates = sorted(
        outputs_dir.glob("月归还数据筛选结果_*豆瓣结果*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    import re
    pattern = re.compile(r"^月归还数据筛选结果_\d{8}_\d{6}_豆瓣结果_\d{8}_\d{6}\.xlsx$")
    for p in candidates:
        if pattern.match(p.name):
            return p
    return None


def find_latest_module4_excel():
    """
    查找模块4生成的终评结果Excel：
    查找包含"终评"的最新Excel文件
    """
    outputs_dir = get_outputs_dir()
    candidates = sorted(
        outputs_dir.glob("月归还数据筛选结果_*豆瓣结果*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    # 查找文件名中包含终评相关内容的文件
    for p in candidates:
        # 检查文件是否包含终评结果列（需要读取Excel）
        try:
            import pandas as pd
            df = pd.read_excel(p, nrows=1)
            if '终评结果' in df.columns:
                return p
        except Exception:
            continue
    return None


def export_filtered_results(filtered_data, excluded_data, filter_engine, filter_summary):
    """输出筛选结果（包括被过滤的数据）"""
    import pandas as pd
    from pathlib import Path
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    from src.utils.time_utils import get_timestamp
    from src.core.result_exporter import ResultExporter
    
    # 加载配置
    outputs_dir = Path(get_config('paths.outputs_dir', 'runtime/outputs'))
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成时间戳
    timestamp = get_timestamp()
    
    # 读取评选批次配置,如果不存在则使用运行日期的前一个月
    target_month = get_config('statistics.target_month', None)
    if not target_month:
        # 计算前一个月:当前日期减去1个月
        current_date = datetime.now()
        previous_month = current_date - relativedelta(months=1)
        target_month = previous_month.strftime('%Y-%m')
        logger.info(f"未配置statistics.target_month,使用运行日期前一个月作为评选批次: {target_month}")
    
    output_files = {}
    
    try:
        # 在筛选数据中添加"评选批次"字段(插入到第一列)
        filtered_data_copy = filtered_data.copy()
        filtered_data_copy.insert(0, '评选批次', target_month)
        
        # 1. 输出筛选后的Excel数据
        excel_file = outputs_dir / f"月归还数据筛选结果_{timestamp}.xlsx"
        filtered_data_copy.to_excel(excel_file, index=False)
        output_files['筛选结果Excel'] = str(excel_file)
        logger.info(f"筛选结果已保存到: {excel_file} (评选批次: {target_month})")
        
        # 2. 输出被过滤的数据到独立Excel文件
        if not excluded_data.empty:
            excluded_excel_file = outputs_dir / f"被过滤数据_{timestamp}.xlsx"
            
            # 使用ResultExporter导出被过滤数据
            exporter = ResultExporter(str(outputs_dir))
            try:
                excluded_file_path = exporter.export_filtered_out_data(
                    excluded_data,
                    filter_summary.get('filter_results', {}),
                    f"被过滤数据_{timestamp}.xlsx"
                )
                output_files['被过滤数据Excel'] = excluded_file_path
                logger.info(f"被过滤数据已保存到: {excluded_file_path}")
            except Exception as e:
                logger.warning(f"使用ResultExporter导出被过滤数据失败，尝试简单导出: {e}")
                # 备用方案：简单导出
                excluded_data.to_excel(excluded_excel_file, index=False)
                output_files['被过滤数据Excel'] = str(excluded_excel_file)
                logger.info(f"被过滤数据已保存到（简单模式）: {excluded_excel_file}")
        else:
            # 即使没有数据，也创建一个说明文件
            empty_excel_file = outputs_dir / f"被过滤数据_{timestamp}.xlsx"
            empty_df = pd.DataFrame([["没有数据被过滤", ""]], columns=['说明', '详情'])
            empty_df.to_excel(empty_excel_file, index=False)
            output_files['被过滤数据Excel'] = str(empty_excel_file)
            logger.info(f"已创建空被过滤数据文件: {empty_excel_file}")
        
        # 3. 生成筛选报告
        report_file = outputs_dir / f"月归还数据筛选报告_{timestamp}.txt"
        report_content = filter_engine.generate_report(filtered_data)
        
        # 添加汇总信息
        if filter_summary:
            report_content += f"\n\n筛选汇总信息:\n"
            report_content += f"原始数据: {filter_summary['original_count']} 条记录\n"
            report_content += f"筛选后数据: {filter_summary['filtered_count']} 条记录\n"
            report_content += f"被过滤数据: {filter_summary.get('excluded_count', 0)} 条记录\n"
            report_content += f"总排除数量: {filter_summary['total_excluded']} 条记录\n"
            report_content += f"排除比例: {filter_summary['exclusion_ratio']:.2%}\n"
            
            # 添加每个筛选器的详细信息
            for filter_name, result in filter_summary.get('filter_results', {}).items():
                if result.get('excluded_count', 0) > 0:
                    report_content += f"\n{filter_name} 详情:\n"
                    report_content += f"  排除数量: {result['excluded_count']} 条\n"
                    if result.get('patterns_count'):
                        report_content += f"  模式数量: {result['patterns_count']}\n"
                    if result.get('target_column'):
                        report_content += f"  目标列: {result['target_column']}\n"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        output_files['筛选报告'] = str(report_file)
        logger.info(f"筛选报告已保存到: {report_file}")
        
        return output_files
        
    except Exception as e:
        logger.error(f"筛选结果输出失败: {str(e)}")
        return {}


def process_monthly_return_data_corrected():
    """处理月归还数据的主流程（模块1）"""
    from src.core.data_loader import load_monthly_return_data, load_recent_three_months_borrowing_data
    from src.core.data_cleaner import clean_monthly_return_data, clean_borrowing_data
    from src.core.statistics import calculate_corrected_borrowing_stats
    from src.core.result_exporter import export_borrowing_analysis_results
    from src.core.data_filter import BookFilterFinal
    
    start_time = time.time()
    logger.info("开始月归还数据分析流程")
    
    try:
        # 步骤1: 加载月归还数据
        logger.info("步骤1: 加载月归还数据")
        monthly_return_data = load_monthly_return_data()
        logger.info(f"月归还数据加载完成: {len(monthly_return_data)} 条记录")
        
        # 步骤2: 加载近三月借阅数据
        logger.info("步骤2: 加载近三月借阅数据")
        borrowing_data = load_recent_three_months_borrowing_data()
        logger.info(f"近三月借阅数据加载完成: {len(borrowing_data)} 条记录")
        
        # 步骤3: 清洗月归还数据
        logger.info("步骤3: 清洗月归还数据")
        cleaned_monthly_data = clean_monthly_return_data(monthly_return_data)
        logger.info(f"月归还数据清洗完成: {len(cleaned_monthly_data)} 条记录")
        
        # 步骤4: 清洗借阅数据
        logger.info("步骤4: 清洗借阅数据")
        cleaned_borrowing_data = clean_borrowing_data(borrowing_data)
        logger.info(f"借阅数据清洗完成: {len(cleaned_borrowing_data)} 条记录")
        
        # 步骤5: 使用借阅数据计算月归还数据的统计信息
        logger.info("步骤5: 计算借阅统计数据（基于近三月借阅数据）")
        final_data = calculate_corrected_borrowing_stats(
            cleaned_monthly_data, 
            cleaned_borrowing_data
        )
        logger.info(f"借阅统计计算完成: {len(final_data)} 条记录")
        
        # 步骤6: 结果输出
        logger.info("步骤6: 结果输出")
        output_files = export_borrowing_analysis_results(final_data)
        logger.info(f"结果输出完成: {len(output_files)} 个文件")
        
        # 步骤7: 降噪筛选
        logger.info("步骤7: 降噪筛选")
        filter_engine = BookFilterFinal()
        filtered_data, excluded_data, filter_summary = filter_engine.filter_books(final_data)
        
        # 步骤8: 筛选结果输出（包括被过滤数据）
        logger.info("步骤8: 筛选结果输出")
        filter_output_files = export_filtered_results(filtered_data, excluded_data, filter_engine, filter_summary)
        logger.info(f"筛选结果输出完成: {len(filter_output_files)} 个文件")
        
        # 计算处理时间
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 输出最终统计
        logger.info("=" * 50)
        logger.info("月归还数据分析流程完成")
        logger.info("=" * 50)
        logger.info(f"处理时间: {processing_time:.2f} 秒")
        logger.info(f"月归还数据量: {len(monthly_return_data)} 条")
        logger.info(f"近三月借阅数据量: {len(borrowing_data)} 条")
        logger.info(f"清洗后月归还数据量: {len(cleaned_monthly_data)} 条")
        logger.info(f"清洗后借阅数据量: {len(cleaned_borrowing_data)} 条")
        logger.info(f"最终结果数据量: {len(final_data)} 条")
        logger.info(f"输出文件: {len(output_files)} 个")
        
        for file_type, file_path in output_files.items():
            logger.info(f"  {file_type}: {file_path}")
        
        # 特别输出统计信息
        has_statistics = (final_data['近三个月总次数'] > 0).sum()
        total_borrowing_count = final_data['近三个月总次数'].sum()
        logger.info(f"修正后的借阅统计摘要:")
        logger.info(f"  有统计数据的记录: {has_statistics}/{len(final_data)} 条")
        logger.info(f"  总借阅次数: {total_borrowing_count} 次")
        
        # 筛选结果统计信息
        if filter_summary:
            logger.info(f"降噪筛选摘要:")
            logger.info(f"  原始数据: {filter_summary['original_count']} 条")
            logger.info(f"  筛选后数据: {filter_summary['filtered_count']} 条")
            logger.info(f"  被过滤数据: {filter_summary.get('excluded_count', 0)} 条")
            logger.info(f"  总排除数量: {filter_summary['total_excluded']} 条")
            logger.info(f"  排除比例: {filter_summary['exclusion_ratio']:.2%}")
        
        return True, final_data
        
    except Exception as e:
        logger.error(f"数据处理流程失败: {str(e)}", exc_info=True)
        return False, None


def run_douban_module(excel_file=None, douban_command="full", extra_args=None):
    """运行豆瓣模块（模块3）"""
    try:
        print("\n正在启动豆瓣模块...")
        
        # 调用豆瓣模块主程序
        douban_script = Path(__file__).parent / "src" / "core" / "douban" / "douban_main.py"
        
        if not douban_script.exists():
            print("错误: 找不到豆瓣模块主程序文件")
            return False

        cmd = [sys.executable, str(douban_script)]
        if douban_command:
            cmd.append(douban_command)

        if excel_file:
            cmd.extend(["--excel-file", str(excel_file)])
            print(f"使用筛选结果文件: {excel_file}")

        if extra_args:
            cmd.extend(extra_args)
        
        # 执行豆瓣模块
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("✓ 豆瓣模块执行完成")
            return True
        else:
            print(f"✗ 豆瓣模块执行失败 (退出码: {result.returncode})")
            return False
            
    except Exception as e:
        logger.error(f"运行豆瓣模块时出错: {str(e)}")
        print(f"✗ 运行豆瓣模块时出错: {str(e)}")
        return False


def run_module1():
    """运行模块1：月归还数据分析"""
    print("=" * 60)
    print("模块1: 月归还数据分析模块")
    print("使用近三月借阅数据作为统计基准")
    print("=" * 60)
    
    # 检查配置指定的输入文件是否存在
    monthly_file = Path(app_config.get(
        'paths.excel_files.monthly_return_file',
        'data/月归还.xlsx'
    ))
    borrowing_file = Path(app_config.get(
        'paths.excel_files.recent_three_months_borrowing_file',
        'data/近三月借阅.xlsx'
    ))
    
    missing_files = [path for path in (monthly_file, borrowing_file) if not path.exists()]
    if missing_files:
        print("错误: 找不到以下配置指定的输入文件:")
        for missing in missing_files:
            print(f"  - {missing}")
        print("请检查 config/setting.yaml 中 paths.excel_files 的配置，或确认文件路径正确")
        return 1
    
    # 执行数据处理流程
    success, final_data = process_monthly_return_data_corrected()
    
    if success and final_data is not None:
        print("\n" + "=" * 60)
        print("[成功] 模块1数据处理完成!")
        print("请查看 runtime/outputs/ 目录下的结果文件")
        print("请查看 runtime/logs/ 目录下的详细日志")
        print("使用近三月借阅数据进行统计计算")
        print("使用降噪筛选功能")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("X 模块1数据处理失败!")
        print("请查看 runtime/logs/error.log 获取详细错误信息")
        print("=" * 60)
        return 1

def run_module3():
    """运行模块3：豆瓣模块"""
    print("=" * 60)
    print("模块3: 豆瓣模块")
    print("ISBN获取、豆瓣评分等功能")
    print("=" * 60)
    
    latest_excel = find_latest_module2_excel()
    if not latest_excel:
        print("错误: 未找到模块2生成的筛选结果 Excel 文件。")
        print("请先运行模块1完成筛选，或将结果文件放到 runtime/outputs 目录。")
        return 1

    success = run_douban_module(excel_file=latest_excel)
    
    if success:
        print("\n" + "=" * 60)
        print("[成功] 模块3执行完成!")
        print("请查看豆瓣模块的输出结果")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("X 模块3执行失败!")
        print("请检查豆瓣模块的错误信息")
        print("=" * 60)
        return 1


def run_theme_module_initial():
    print("=" * 60)
    print("模块4: 主题推荐评选（初评）")
    print("按主题分批调用模型并写回初评结果")
    print("=" * 60)
    latest_excel = find_latest_module3_excel()
    if not latest_excel:
        print("错误: 未找到模块3生成的豆瓣结果 Excel 文件。")
        print("请先运行模块3生成豆瓣结果，或将结果文件放到 runtime/outputs 目录。")
        return 1
    try:
        from src.core.recommendation.controller import run_theme_recommendation
        run_theme_recommendation(str(latest_excel))
        print("\n" + "=" * 60)
        print("[成功] 模块4初评执行完成!")
        print("请查看筛选结果Excel的初评列")
        print("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"模块4初评执行失败: {str(e)}", exc_info=True)
        print("\n" + "=" * 60)
        print("X 模块4初评执行失败!")
        print("请查看 runtime/logs/error.log 获取详细错误信息")
        print("=" * 60)
        return 1


def run_theme_module_full():
    print("=" * 60)
    print("模块4: 完整三阶段评选流程")
    print("阶段1：主题内初评（海选）")
    print("阶段2：主题内决选（晋级赛，平衡主题）")
    print("阶段3：全局终评（决赛圈，智能模式选择）")
    print("=" * 60)
    latest_excel = find_latest_module3_excel()
    if not latest_excel:
        print("错误: 未找到模块3生成的豆瓣结果 Excel 文件。")
        print("请先运行模块3生成豆瓣结果，或将结果文件放到 runtime/outputs 目录。")
        return 1
    try:
        from src.core.recommendation.controller import run_theme_recommendation_full
        run_theme_recommendation_full(str(latest_excel))
        print("\n" + "=" * 60)
        print("[成功] 模块4完整三阶段评选完成!")
        print("请查看筛选结果Excel的初评、决选、终评列")
        print("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"模块4完整执行失败: {str(e)}", exc_info=True)
        print("\n" + "=" * 60)
        print("X 模块4完整执行失败!")
        print("请查看 runtime/logs/error.log 获取详细错误信息")
        print("=" * 60)
        return 1


def run_module5():
    """运行模块5：图书卡片生成"""
    print("=" * 60)
    print("模块5: 图书卡片生成模块")
    print("生成精美的HTML图书卡片和PNG图片")
    print("=" * 60)

    latest_excel = find_latest_module4_excel()
    if not latest_excel:
        print("错误: 未找到模块4生成的终评结果 Excel 文件。")
        print("请先运行模块4完成评选，或将结果文件放到 runtime/outputs 目录。")
        return 1

    try:
        # 调用模块5主程序
        card_script = Path(__file__).parent / "src" / "core" / "card_generator" / "card_main.py"

        if not card_script.exists():
            print("错误: 找不到卡片生成模块主程序文件")
            return 1

        cmd = [sys.executable, str(card_script), "--excel-file", str(latest_excel)]

        print(f"使用终评结果文件: {latest_excel}")

        # 执行模块5
        result = subprocess.run(cmd, capture_output=False, text=True)

        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("[成功] 模块5执行完成!")
            print("请查看 runtime/outputs/ 目录下的图书卡片")
            print("=" * 60)
            return 0
        else:
            print(f"\n" + "=" * 60)
            print(f"X 模块5执行失败 (退出码: {result.returncode})")
            print("=" * 60)
            return 1

    except Exception as e:
        logger.error(f"运行模块5时出错: {str(e)}", exc_info=True)
        print(f"\n" + "=" * 60)
        print(f"X 运行模块5时出错: {str(e)}")
        print("=" * 60)
        return 1
def run_data_collection_pipeline():
    """依次运行模块1（含模块2）和模块3 - 数据采集流程"""
    print("=" * 60)
    print("数据采集流程: 模块1 -> 模块2 -> 模块3")
    print("=" * 60)

    module1_exit = run_module1()
    if module1_exit != 0:
        print("数据采集流程中止：模块1/2 执行失败。")
        return module1_exit

    print("\n模块1/2 执行完成，即将进入模块3 (豆瓣爬取)...")
    module3_exit = run_module3()
    if module3_exit == 0:
        print("\n数据采集流程执行完成！")
    else:
        print("\n数据采集流程执行完成，但模块3失败。")
    return module3_exit


def run_data_analysis_and_evaluation_pipeline():
    """运行数据分析与评选流程：模块1 -> 模块2 -> 模块3 -> 模块4"""
    print("=" * 60)
    print("数据分析与评选流程: 模块1 -> 模块2 -> 模块3 -> 模块4")
    print("=" * 60)

    # 执行模块1
    module1_exit = run_module1()
    if module1_exit != 0:
        print("数据分析与评选流程中止：模块1/2 执行失败。")
        return module1_exit

    # 执行模块3
    print("\n模块1/2 执行完成，即将进入模块3 (豆瓣爬取)...")
    module3_exit = run_module3()
    if module3_exit != 0:
        print("数据分析与评选流程中止：模块3 执行失败。")
        return module3_exit

    # 执行模块4（完整评选流程）
    print("\n模块3 执行完成，即将进入模块4 (主题推荐评选)...")
    module4_exit = run_theme_module_full()
    if module4_exit == 0:
        print("\n数据分析与评选流程执行完成！")
        print("注意：模块4完成后会进入人工筛选阶段")
        print("完成人工筛选后，可单独运行模块5生成图书卡片")
    else:
        print("\n数据分析与评选流程执行完成，但模块4失败。")
    return module4_exit


def run_complete_pipeline():
    """依次运行所有模块：模块1 -> 模块2 -> 模块3 -> 模块4（初评+终评） -> 模块5"""
    print("=" * 60)
    print("完整流程: 模块1 -> 模块2 -> 模块3 -> 模块4（初评→决选→终评） -> 模块5")
    print("=" * 60)

    # 执行模块1
    module1_exit = run_module1()
    if module1_exit != 0:
        print("完整流程中止：模块1/2 执行失败。")
        return module1_exit

    # 执行模块3
    print("\n模块1/2 执行完成，即将进入模块3 (豆瓣爬取)...")
    module3_exit = run_module3()
    if module3_exit != 0:
        print("完整流程中止：模块3 执行失败。")
        return module3_exit

    # 执行模块4（初评+终评）
    print("\n模块3 执行完成，即将进入模块4 (主题推荐评选)...")
    module4_exit = run_theme_module_full()
    if module4_exit != 0:
        print("完整流程中止：模块4 执行失败。")
        return module4_exit

    # 执行模块5
    print("\n模块4 执行完成，即将进入模块5 (图书卡片生成)...")
    module5_exit = run_module5()
    if module5_exit == 0:
        print("\n完整流程执行完成！")
    else:
        print("\n完整流程执行完成，但模块5失败。")
    return module5_exit


def main():
    """主函数 - 提供模块选择菜单"""
    print("=" * 60)
    print("书海回响 - 那些被悄悄归还一本好书")
    print("=" * 60)

    while True:
        print("\n请选择要运行的功能模块:")
        print("1. 模块1/2: 月归还数据分析 + 智能筛选")
        print("2. 模块3: 豆瓣模块（FOLIO ISBN + 豆瓣链接 + 评分过滤 + 豆瓣 API）")
        print("3. 数据采集流程: 模块1 -> 模块2 -> 模块3")
        print("4. 模块4: 初评（海选阶段）")
        print("5. 模块4: 完整评选（初评→决选→终评）")
        print("6. 数据分析与评选流程: 模块1 -> 模块2 -> 模块3 -> 模块4")
        print("7. 模块5: 图书卡片生成")
        print("8. 退出程序")

        choice = input("\n请输入选择 (1-8): ").strip()

        if choice == '1':
            return run_module1()
        elif choice == '2':
            return run_module3()
        elif choice == '3':
            return run_data_collection_pipeline()
        elif choice == '4':
            return run_theme_module_initial()
        elif choice == '5':
            return run_theme_module_full()
        elif choice == '6':
            return run_data_analysis_and_evaluation_pipeline()
        elif choice == '7':
            return run_module5()
        elif choice == '8':
            print("感谢使用 书海回响 脚本!")
            return 0
        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
