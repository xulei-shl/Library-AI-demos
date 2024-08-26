## 读者荐购信息整理
这个程序使用 Streamlit 框架构建，旨在帮助用户从读者荐购数据中提取有价值的信息，并将其保存到 Excel 文件中。

## 场景描述：
- 读者荐购数据包括手写投诉单、电话、网络表单、12315或其他途径提交。
- 这些信息最终汇总为手写拍照图片、截图图片和excel表单到采编中心老师手里。
- 程序需要自动处理这些图像文件，并使用大语言模型(GLM-4-Air 或 GLM-4-0520)从OCR识别的文本中获取书籍信息和提交人信息。

## 功能
- 自动创建每日文件夹，并在其中创建 handwriting 和 screenshot 子文件夹。
- 处理 handwriting 和 screenshot 文件夹中的图像文件，使用 Baidu OCR API 进行文本提取。
- 使用大语言模型(GLM-4-Air 或 GLM-4-0520)从提取的文本中获取书籍信息，如书名、作者等。
- 将提取的信息保存到 Excel 文件中。

## 使用说明
1. 安装所需的依赖库。
2. 在 `.env` 文件中设置 **OCR CCESS_TOKEN** 和 **LLM API_KEY** 环境变量。
3. 运行程序，输入要处理的文件夹路径，并选择要使用的大模型。
4. 点击"生成路径"按钮，程序会自动创建每日文件夹。
5. 点击"开始处理"按钮，程序会处理图像文件并将结果保存到 Excel 文件中。
6. 处理完成后，您可以在生成的文件夹中找到 Excel 文件。

## TODO
- OCR后处理纠错：
  - [shibing624/pycorrector: pycorrector is a toolkit for text error correction. 文本纠错，实现了Kenlm，T5，MacBERT，ChatGLM3，LLaMA等模型应用在纠错场景，开箱即用。](https://github.com/shibing624/pycorrector)
  - [Dicklesworthstone/llm_aided_ocr: Enhance Tesseract OCR output for scanned PDFs by applying Large Language Model (LLM) corrections.](https://github.com/Dicklesworthstone/llm_aided_ocr)