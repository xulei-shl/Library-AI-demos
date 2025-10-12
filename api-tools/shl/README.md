# 上海图书馆开放数据接口（SHL API）使用说明

本文档提供了上海图书馆（SHL）开放数据接口的Python示例代码的说明。这些示例展示了如何查询不同类型的数据，如建筑、人物、事件等。

## 准备工作

在运行任何示例代码之前，您需要完成以下步骤：

1.  **安装依赖**:
    确保您已安装 `requests` 和 `python-dotenv` 库。
    ```bash
    pip install requests python-dotenv
    ```

2.  **获取API Key**:
    您需要一个上海图书馆的 `API Key` 才能访问这些接口。

3.  **配置环境变量**:
    在项目的根目录（即 `api-tools` 文件夹）下创建一个名为 `.env` 的文件。在该文件中，添加您的 API Key，格式如下：
    ```
    SHL_API_KEY=YOUR_ACTUAL_API_KEY
    ```
    脚本会自动从该文件加载 `SHL_API_KEY`。

## 基本代码结构

所有示例脚本都遵循相似的结构：
1.  导入 `requests`, `os`, `sys`, `dotenv` 等必要库。
2.  自动查找并加载 `.env` 文件中的环境变量。
3.  从环境变量中读取 `SHL_API_KEY`。
4.  定义目标API的URL和查询参数（`params`）。
5.  设置请求头（`headers`），特别是 `User-Agent`。
6.  使用 `requests.get()` 发送HTTP GET请求。
7.  处理响应：
    - 如果请求成功（状态码 200），则解析返回的JSON数据。
    - 如果请求失败，则打印错误信息。

## API 接口示例

以下是每个脚本对应的API接口说明。

### 1. 建筑查询 (`architecture.py`)

-   **功能**: 根据关键词查询建筑信息。
-   **URL**: `http://data1.library.sh.cn/shnh/dydata/webapi/architecture/getArchitecture`
-   **主要参数**: `freetext` (关键词)
-   **示例**: 脚本中以 "长江剧场" 为例进行查询。

### 2. 事件查询 (`event.py`)

-   **功能**: 根据关键词查询历史事件。
-   **URL**: `http://data1.library.sh.cn/webapi/hsly/route/getEventList`
-   **主要参数**: `eventFreeText` (关键词)
-   **示例**: 脚本中以 "欧阳予倩" 为例进行查询。

### 3. 机构查询 (`org.py`)

-   **功能**: 根据关键词查询机构信息。
-   **URL**: `http://data1.library.sh.cn/shnh/whzk/webapi/org/list`
-   **主要参数**: `freetext` (关键词)
-   **示例**: 脚本中以 "上海业余剧人协会" 为例进行查询。

### 4. 人物查询 (`person.py`)

-   **功能**: 根据姓名查询人物信息。
-   **URL**: `http://data1.library.sh.cn/persons/data`
-   **主要参数**: `name` (姓名)
-   **示例**: 脚本中以 "封凤子" 为例进行查询。

### 5. 地点查询 (`place.py`)

-   **功能**: 根据地名查询地点信息。
-   **URL**: `http://data1.library.sh.cn/place/{地名}`
-   **主要参数**: 查询的关键词直接放在URL路径中。
-   **示例**: 脚本中以 "上海" 为例进行查询。

### 6. 作品查询 (`work.py`)

-   **功能**: 根据书名或标题查询著作信息。
-   **URL**: `http://data1.library.sh.cn/bib/webapi/work/list`
-   **主要参数**: `title` (标题)
-   **示例**: 脚本中以 "日出" 为例进行查询。

## 通用参数

大多数查询接口都支持以下通用参数，用于分页控制：
-   `key`: 您的API Key（必需）。
-   `pageth`: 页码，从1开始。
-   `pageSize`: 每页返回的记录数。

请参考每个脚本中的 `params` 字典以了解具体用法。