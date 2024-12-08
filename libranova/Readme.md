# 项目介绍
借阅星空 - 图书借阅数据可视化


![](https://xulei-pic-1258542021.cos.ap-shanghai.myqcloud.com/mdpic/1733540890001.png)

---

![](./css/img/借阅可视化.gif)

## 数据预处理
1. 一级主题匹配
> B2 = 分类号

Excel公式： 

`=IFERROR(VLOOKUP(LEFT(B2,3),一级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,2),一级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,1),一级!A:B,2,FALSE),"其他")))`

2. 二级主题匹配

Excel公式：

`=IFERROR(VLOOKUP(B2,二级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,7),二级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,6),二级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,5),二级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,4),二级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,3),二级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,2),二级!A:B,2,FALSE),IFERROR(VLOOKUP(LEFT(B2,1),二级!A:B,2,FALSE),"其他"))))))))`

3. 处理好的数据放在项目data路径下

样例数据可见 exam-data路径

4. json数据处理
python tools/process_data.py

## 运行
python -m http.server

然后在浏览器中访问 http://localhost:8000

