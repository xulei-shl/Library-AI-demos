"""
Excel数据自动合并系统主程序
自动处理脚本目录下的Excel文件，合并到指定目标文件
"""
import sys
from pathlib import Path
from typing import List
import traceback

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.utils.logger import logger
from src.utils.excel_utils import ExcelUtils
from src.core.data_merger import DataMerger
from src.core.file_manager import FileManager
from src.core.statistics_analyzer import StatisticsAnalyzer
from src.processors.processor_factory import ProcessorFactory
from src.config.settings import (
    TARGET_FILE_PATH, STATISTICS_CONFIG, 
    get_target_file_name, get_source_excel_path
)


class ExcelMergeSystem:
    """Excel数据自动合并系统主类"""
    
    def __init__(self):
        # 使用配置中的源Excel路径作为工作目录
        self.base_directory = get_source_excel_path()
        self.data_merger = DataMerger()
        self.file_manager = FileManager(self.base_directory)
        self.processed_files = []
        self.failed_files = []
        
        logger.info("=" * 60)
        logger.info("Excel数据自动合并系统启动")
        logger.info(f"源Excel目录: {self.base_directory}")
        logger.info(f"目标文件: {TARGET_FILE_PATH}")
        logger.info(f"目标文件名: {get_target_file_name()}")
        logger.info("=" * 60)
    
    def run(self) -> bool:
        """
        运行主程序
        
        Returns:
            是否执行成功
        """
        try:
            # 1. 初始化环境
            if not self._initialize():
                return False
            
            # 2. 扫描Excel文件
            excel_files = self._scan_excel_files()
            
            # 3. 检查目标文件（无论是否有文件需要合并，都需要检查目标文件以便统计分析）
            if not self._check_target_file():
                return False
            
            # 如果有文件需要处理，执行合并流程
            if excel_files:
                # 4. 处理Excel文件
                processed_data_list = self._process_excel_files(excel_files)
                
                # 5. 合并数据
                if processed_data_list:
                    merged_data = self.data_merger.merge_data(processed_data_list)
                    if merged_data is not None:
                        # 6. 追加到目标文件
                        if self.data_merger.append_to_target_file(merged_data):
                            # 7. 移动已处理文件
                            self._move_processed_files()
                            # 8. 生成处理报告
                            self._generate_report()
                            logger.info("Excel数据合并任务完成")
                        else:
                            logger.error("数据追加到目标文件失败")
                            return False
                    else:
                        logger.error("数据合并失败")
                        return False
                else:
                    logger.warning("没有成功处理的数据")
                    return False
            else:
                logger.info("未找到需要处理的Excel文件")
            
            # 9. 询问是否执行统计分析（无论是否有文件合并都提供此选项）
            if self._ask_for_statistics_analysis():
                self._run_statistics_analysis()
            
            return True
                
        except Exception as e:
            logger.exception(f"程序执行失败: {str(e)}")
            return False
    
    def _initialize(self) -> bool:
        """
        初始化系统环境
        
        Returns:
            是否初始化成功
        """
        try:
            logger.info("初始化系统环境...")
            
            # 确保必要目录存在
            if not self.file_manager.ensure_directories():
                logger.error("创建必要目录失败")
                return False
            
            logger.info("系统环境初始化完成")
            return True
            
        except Exception as e:
            logger.exception(f"系统初始化失败: {str(e)}")
            return False
    
    def _scan_excel_files(self) -> List[Path]:
        """
        扫描工作目录下的Excel文件（过滤目标文件和已处理文件）
        
        Returns:
            Excel文件路径列表
        """
        try:
            logger.info("扫描Excel文件...")
            
            # 获取所有Excel文件
            all_excel_files = ExcelUtils.find_excel_files(self.base_directory)
            
            # 获取目标文件名用于比较
            target_file_name = get_target_file_name()
            
            # 过滤掉已处理的文件和目标文件
            unprocessed_files = []
            for file_path in all_excel_files:
                # 检查是否为目标文件（比较文件名）
                if file_path.name == target_file_name:
                    logger.info(f"跳过目标文件: {file_path.name}")
                    continue
                
                # 检查是否已处理
                if not self.file_manager.is_file_processed(file_path.name):
                    unprocessed_files.append(file_path)
                else:
                    logger.info(f"跳过已处理文件: {file_path.name}")
            
            logger.info(f"找到 {len(unprocessed_files)} 个待处理Excel文件")
            for file_path in unprocessed_files:
                logger.info(f"  - {file_path.name}")
            
            return unprocessed_files
            
        except Exception as e:
            logger.exception(f"扫描Excel文件失败: {str(e)}")
            return []
    
    def _check_target_file(self) -> bool:
        """
        检查目标文件是否存在且可访问
        
        Returns:
            目标文件是否可用
        """
        try:
            target_path = Path(TARGET_FILE_PATH)
            
            if not target_path.exists():
                logger.error(f"目标文件不存在: {target_path}")
                return False
            
            # 尝试获取目标文件的列结构
            target_columns = self.data_merger.get_target_columns()
            if not target_columns:
                logger.error("无法读取目标文件结构")
                return False
            
            logger.info(f"目标文件检查通过，列数: {len(target_columns)}")
            return True
            
        except Exception as e:
            logger.exception(f"检查目标文件失败: {str(e)}")
            return False
    
    def _process_excel_files(self, excel_files: List[Path]) -> List[tuple]:
        """
        处理Excel文件列表
        
        Args:
            excel_files: Excel文件路径列表
            
        Returns:
            包含(DataFrame, file_type)元组的列表
        """
        processed_data_list = []
        
        for file_path in excel_files:
            try:
                logger.info(f"开始处理文件: {file_path.name}")
                
                # 读取Excel文件
                df = ExcelUtils.read_excel_file(file_path)
                if df is None:
                    logger.error(f"读取文件失败: {file_path.name}")
                    self.failed_files.append(file_path)
                    continue
                
                # 创建对应的处理器
                processor = ProcessorFactory.create_processor(file_path.name)
                if processor is None:
                    logger.error(f"创建处理器失败: {file_path.name}")
                    self.failed_files.append(file_path)
                    continue
                
                # 获取文件类型
                file_type = processor.get_file_type()
                
                # 执行数据处理
                processed_df = processor.execute(df)
                if processed_df is None or processed_df.empty:
                    logger.warning(f"文件处理后无有效数据: {file_path.name}")
                    self.failed_files.append(file_path)
                    continue
                
                # 添加到处理结果列表，包含文件类型信息
                processed_data_list.append((processed_df, file_type))
                self.processed_files.append(file_path)
                logger.info(f"文件处理成功: {file_path.name}, 数据行数: {len(processed_df)}, 文件类型: {file_type}")
                
            except Exception as e:
                logger.exception(f"处理文件失败: {file_path.name}, 错误: {str(e)}")
                self.failed_files.append(file_path)
        
        logger.info(f"文件处理完成 - 成功: {len(self.processed_files)}, 失败: {len(self.failed_files)}")
        return processed_data_list
    
    def _move_processed_files(self) -> None:
        """移动已成功处理的文件到已处理文件夹"""
        try:
            logger.info("移动已处理文件...")
            
            moved_count = 0
            for file_path in self.processed_files:
                if self.file_manager.move_to_processed(file_path):
                    moved_count += 1
                else:
                    logger.warning(f"移动文件失败: {file_path.name}")
            
            logger.info(f"成功移动 {moved_count} 个文件到已处理文件夹")
            
        except Exception as e:
            logger.exception(f"移动已处理文件失败: {str(e)}")
    
    def _generate_report(self) -> None:
        """生成处理报告"""
        try:
            logger.info("=" * 60)
            logger.info("处理报告")
            logger.info("=" * 60)
            logger.info(f"总文件数: {len(self.processed_files) + len(self.failed_files)}")
            logger.info(f"成功处理: {len(self.processed_files)}")
            logger.info(f"处理失败: {len(self.failed_files)}")
            
            if self.processed_files:
                logger.info("成功处理的文件:")
                for file_path in self.processed_files:
                    logger.info(f"  ✓ {file_path.name}")
            
            if self.failed_files:
                logger.info("处理失败的文件:")
                for file_path in self.failed_files:
                    logger.info(f"  ✗ {file_path.name}")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.exception(f"生成处理报告失败: {str(e)}")
    
    def _ask_for_statistics_analysis(self) -> bool:
        """
        询问用户是否执行统计分析
        
        Returns:
            用户是否选择执行统计分析
        """
        try:
            # 检查统计分析功能是否启用
            if not STATISTICS_CONFIG.get('enabled', False):
                logger.info("统计分析功能已禁用")
                return False
            
            print("\n" + "=" * 60)
            print("Excel数据合并已完成！")
            print("=" * 60)
            print("是否执行统计分析？")
            print("统计分析将：")
            print("1. 筛选目标文件中上个月的业务数据")
            print("2. 按馆藏编号分组计算数量求和")
            print("3. 将结果保存到统计表文件")
            print(f"4. 输出文件：{STATISTICS_CONFIG['output_file_path']}")
            print("-" * 60)
            
            while True:
                choice = input("请选择 (y/n): ").strip().lower()
                if choice in ['y', 'yes', '是']:
                    return True
                elif choice in ['n', 'no', '否']:
                    return False
                else:
                    print("请输入 y 或 n")
                    
        except KeyboardInterrupt:
            print("用户取消操作")
            return False
        except Exception as e:
            logger.exception(f"询问统计分析选择失败: {str(e)}")
            return False
    
    def _run_statistics_analysis(self) -> None:
        """执行统计分析"""
        try:
            logger.info("用户选择执行统计分析")
            analyzer = StatisticsAnalyzer()
            success = analyzer.run_analysis()
            
            if success:
                print("✓ 统计分析执行成功！")
                print(f"结果已保存到: {STATISTICS_CONFIG['output_file_path']}")
            else:
                print("✗ 统计分析执行失败，请查看日志了解详情")
                
        except Exception as e:
            logger.exception(f"执行统计分析失败: {str(e)}")
            print("✗ 统计分析执行异常，请查看日志了解详情")


def main():
    """主函数"""
    try:
        # 创建并运行系统
        system = ExcelMergeSystem()
        success = system.run()
        
        # 根据执行结果设置退出码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("用户中断程序执行")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"程序异常退出: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()