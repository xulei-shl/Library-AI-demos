# 未编文献图片OCR文本与元数据提取

## 场景与功能：
1. 图书馆未编文献（联合国资料）图片OCR识别与元数据提取
2. 读取本地文件夹下的图片，将OCR文本和LLM整理的元数据保存到同一个路径下的excel中
   
## 工具
1. 百度 OCR API：提取原文
2. 百川API：原文整理
3. （附）got-4o API：基于图片和OCR文本，生成JSON元数据

## 相关研究

1. 芬兰有个专门的灰色文献PDF元数据提取研究项目：[NatLibFi/FinGreyLit](https://github.com/NatLibFi/FinGreyLit)，并且有一个专用的 Python 库：[NationalLibraryOfNorway/meteor: A python module and REST API for automatic extraction of metadata from PDF files](https://github.com/NationalLibraryOfNorway/meteor)