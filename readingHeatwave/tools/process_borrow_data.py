import pandas as pd
import json
import os
from datetime import datetime
import holidays  # 导入中国节假日库

def process_borrow_data(excel_path, output_json_path):
    # 读取 Excel 数据
    df = pd.read_excel(excel_path)

    # 确保提交时间列存在
    if '提交时间' not in df.columns:
        raise ValueError("Excel 文件中未找到 '提交时间' 列，请检查文件格式。")

    # 提取日期部分并统计借阅数量
    df['日期'] = pd.to_datetime(df['提交时间']).dt.date
    borrow_count_by_date = df['日期'].value_counts().sort_index()

    # 按月统计借阅量
    df['月份'] = pd.to_datetime(df['提交时间']).dt.to_period('M')
    borrow_count_by_month = df['月份'].value_counts().sort_index()

    # 统计全年总借阅量
    total_borrows = int(borrow_count_by_date.sum())  # 转换为 int

    # 找到年度最高借阅日和最低借阅日
    top_day = borrow_count_by_date.idxmax()
    top_day_count = int(borrow_count_by_date.max())  # 转换为 int

    # 排除周一和指定日期，计算年度最低借阅日
    excluded_dates = [datetime(2024, 12, 24).date()]  # 指定要排除的日期列表

    borrow_count_no_excluded_dates = borrow_count_by_date[
        borrow_count_by_date.index.map(lambda x: x.weekday() != 0 and x not in excluded_dates)
    ]

    if not borrow_count_no_excluded_dates.empty:
        lowest_day = borrow_count_no_excluded_dates.idxmin()
        lowest_day_count = int(borrow_count_no_excluded_dates.min())  # 转换为 int
    else:
        lowest_day = None
        lowest_day_count = None

    # 找到借阅量最多和最少的月份
    top_month = borrow_count_by_month.idxmax()
    top_month_count = int(borrow_count_by_month.max())  # 转换为 int
    lowest_month = borrow_count_by_month.idxmin()
    lowest_month_count = int(borrow_count_by_month.min())  # 转换为 int

    # 获取中国节假日列表（包括节假日名称）
    cn_holidays = holidays.China(years=datetime.now().year)

    # 转换为 JSON 格式数据
    borrow_data = []
    for date, count in borrow_count_by_date.items():
        # 获取日期的“周几”信息
        weekday = date.strftime('%A')  # 获取周几的英文格式
        weekday_chinese = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                           "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周天"}[weekday]

        # 判断是否为节假日，并获取节假日名称
        is_holiday = date in cn_holidays
        holiday_name = cn_holidays.get(date, None)  # 获取节假日名称，如果不是节假日则返回 None

        borrow_data.append({
            "date": date.strftime('%Y-%m-%d'),
            "borrow_count": int(count),  # 转换为 int
            "weekday": weekday_chinese,  # 添加“周几”信息
            "is_holiday": is_holiday,    # 标记是否是节假日
            "holiday_name": holiday_name  # 添加节假日名称
        })

    # 每月统计数据
    monthly_summary = []
    for month, count in borrow_count_by_month.items():
        monthly_summary.append({
            "month": str(month),
            "borrow_count": int(count)  # 转换为 int
        })

    # 生成最终 JSON 结构
    json_data = {
        "year": datetime.now().year,
        "borrow_data": borrow_data,
        "summary": {
            "total_borrows": total_borrows,
            "top_day": {"date": top_day.strftime('%Y-%m-%d'), "borrow_count": top_day_count},
            "lowest_day": {"date": lowest_day.strftime('%Y-%m-%d'), "borrow_count": lowest_day_count},
            "monthly_summary": monthly_summary,
            "top_month": {"month": str(top_month), "borrow_count": top_month_count},
            "lowest_month": {"month": str(lowest_month), "borrow_count": lowest_month_count}
        }
    }

    # 保存为 JSON 文件
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_data, json_file, ensure_ascii=False, indent=4)

    print(f"数据处理完成！JSON 文件已保存到: {output_json_path}")


# 主函数
if __name__ == "__main__":
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 构造相对路径
    data_path = os.path.join(current_dir, "../data")
    excel_file = os.path.join(data_path, "library_data.xlsx")  # 输入的 Excel 文件
    output_json_file = os.path.join(data_path, "borrow_data.json")  # 输出的 JSON 文件

    try:
        process_borrow_data(excel_file, output_json_file)
    except Exception as e:
        print(f"数据处理时发生错误: {e}")
