# Playwright网站监控功能集成指南

## 功能概述

本项目已成功集成Playwright网站监控功能，支持对不支持RSS的网站进行动态抓取。特别针对澎湃新闻手机端网站进行了优化，能够追踪文章更新列表，并按时间范围过滤文章。

## 主要特性

### 1. 动态网页抓取
- 支持JavaScript渲染的动态网页
- 自动滚动加载更多内容
- 模拟手机端访问（375x667屏幕）

### 2. 智能元素识别
- 针对澎湃手机端优化的CSS选择器
- 支持相对时间解析（如"19小时前"）
- 自动提取标题、链接、时间信息

### 3. 配置化管理
- 完全配置化，支持多网站监控
- 可控制启用/禁用状态
- 支持重试机制和超时设置

### 4. 无缝集成
- 与现有RSS系统完美兼容
- 三阶段流程：抓取 -> 提取 -> 分析
- 自动去重和数据聚合

## 配置文件说明

在 `config/subject_bibliography.yaml` 中新增了 `playwright_sites` 配置段。

## 使用方法

### 1. 仅运行抓取阶段
```bash
python -m src.core.pipeline --stage fetch
```

### 2. 运行完整流程
```bash
python -m src.core.pipeline --stage all
```

### 3. 测试集成功能
```bash
python test_playwright_integration.py
```

## 输出结果

抓取结果会保存在 `runtime/outputs/` 目录中，按月聚合为Excel文件，包含标题、时间、网址、来源等信息。

## 技术实现

### 核心模块

1. **PlaywrightSiteFetcher** (`src/core/playwright_fetcher.py`)
   - 网站抓取核心逻辑
   - 支持多网站批量抓取
   - 时间范围过滤

2. **PengpaiPlaywrightExtractor** (`src/core/content_extractors/pengpai_playwright.py`)
   - 澎湃网站专用全文提取器
   - 支持完整文章内容获取

3. **Pipeline集成** (`src/core/pipeline.py`)
   - 三阶段流程集成
   - RSS和Playwright源统一处理

## 测试验证

系统包含完整的测试套件，所有测试通过后可放心使用。

## 总结

Playwright网站监控功能的成功集成，为RSS系统提供了强大的补充能力，特别适合处理动态加载内容和移动端网站。通过配置化管理，实现了灵活、易维护的网站监控解决方案。