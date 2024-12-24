# 介绍
Reading Heatwave（借阅热图）

使用 HTML, CSS 和 JavaScript 构建的图书馆年度借阅热图可视化工具。它可以展示一年中每天的借阅量，并提供一些统计信息。

## 预览

![1735024654038.png](https://xulei-pic-1258542021.cos.ap-shanghai.myqcloud.com/mdpic/1735024654038.png)

## 功能特性

*   **年度热图：** 以日历的形式展示全年的借阅情况，颜色深浅代表借阅量的多少。
*   **详细数据：** 鼠标悬停在日期上会显示该日期的借阅量、星期几以及是否为节假日。
*   **统计数据：** 提供总借阅量、最高日借阅量、最低日借阅量、最高月借阅量和最低月借阅量的统计信息。

## 文件结构

*   `index.html`: HTML 入口文件，包含页面结构。
*   `css/style.css`: 包含页面的样式定义。
*   `css/imgs/logo_shl.jpg`: 图书馆的 Logo 图片。
*   `data/`: 正式的借阅数据的 Excel 和 JSON 文件。
*   `src/main.js`: 包含 JavaScript 代码，用于数据处理和页面渲染。
*   `exe-data/`:  包含借阅数据示例的 Excel 和 JSON 文件。
*   `process_borrow_data.py`:  用于处理借阅数据并生成 `data/borrow_data.json` 的 Python 脚本。

## 数据处理

`data/borrow_data.json` 文件是由 `process_borrow_data.py` 脚本生成的。该脚本读取 `exe-data/sample_data.xlsx` 中（或指定其他数据文件）的借阅数据，进行处理，并生成 `data/borrow_data.json` 文件。

您可以使用以下命令运行该脚本：

```bash
python process_borrow_data.py
```

## 数据格式

`borrow_data.json` 文件包含以下格式的数据：

```json
{
    "borrow_data": [
        {
            "date": "2024-01-01",
            "borrow_count": 150,
            "is_holiday": true,
            "holiday_name": "元旦",
            "weekday":"周一"
        },
         {
            "date": "2024-01-02",
            "borrow_count": 200,
            "is_holiday": false,
            "holiday_name": null,
             "weekday":"周二"
        }
        // ...其他日期的数据
    ],
    "summary":{
      "total_borrows": 10000,
       "top_day": {
        "date":"2024-05-01",
        "borrow_count": 500
        },
        "lowest_day":{
           "date":"2024-02-14",
        "borrow_count": 10
        },
          "top_month": {
        "month":"2024-05",
        "borrow_count": 3000
        },
        "lowest_month":{
        "month":"2024-02",
        "borrow_count": 100
        },
        "monthly_summary":[
            {
                "month": "2024-01",
                "borrow_count": 1000
            },
            {
                "month": "2024-02",
                "borrow_count": 500
            },
             {
                 "month":"2024-12",
                 "borrow_count": 400
            }
        ]
    }
}
```
