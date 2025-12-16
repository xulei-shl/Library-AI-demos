# RSSHub 协议支持实现说明

## 概述

我们已经成功实现了一个单独的文件 `src/core/rsshub_fetcher.py` 来支持 RSSHub 协议的订阅源fetcher，并将其完整集成到现有的RSS fetcher系统中。

## 功能特性

### 1. 协议转换
- 将 `rsshub://` 协议转换为标准的 HTTP URL
- 支持多个 RSSHub 实例的备用机制
- 自动处理 URL 解析和路径构造

### 2. 多实例支持
实现了多个 RSSHub 实例的轮询和备用机制：
- `https://rsshub.app` (官方实例)
- `https://rsshub.smzdm.com` (什么值得买镜像)
- `https://rsshub.t1qx.com` (备用镜像1)
- `https://rsshub.iowen.cn` (备用镜像2)

### 3. 完整集成
- 与现有 RSS fetcher 系统完全兼容
- 支持配置文件中的 `rsshub://` 协议源
- 统一的数据格式和错误处理
- 支持重试机制和备用URL

## 使用方法

### 在配置文件中添加 RSSHub 源

在 `config/subject_bibliography.yaml` 文件中，可以像这样添加 RSSHub 源：

```yaml
rss_feeds:
  # 现有常规RSS源
  - name: "澎湃新闻"
    url: "http://www.thepaper.cn/rss_xhd.xml"
    enabled: true
    retry_config:
      max_retries: 3
      retry_delay: 2
      
  # 新的RSSHub源 - 澎湃思想
  - name: "澎湃思想"
    url: "rsshub://thepaper/list/25483"
    enabled: true
    retry_config:
      max_retries: 2
      retry_delay: 3
      
  # 其他RSSHub源示例
  - name: "微博用户动态"
    url: "rsshub://weibo/user/123456"
    enabled: false  # 可以禁用
    backup_urls:
      - "rsshub://weibo/user/789012"
      
  - name: "知乎专栏"
    url: "rsshub://zhihu/zhuanlan/888"
    enabled: true
```

### 支持的 RSSHub 服务

当前支持的主要服务包括：

#### 新闻资讯
- `thepaper` - 澎湃新闻
- `toutiao` - 今日头条  
- `tencent` - 腾讯新闻
- `sina` - 新浪新闻
- `netease` - 网易新闻
- `sohu` - 搜狐新闻

#### 社交媒体
- `weibo` - 微博
- `zhihu` - 知乎
- `jianshu` - 简书

#### 技术社区
- `juejin` - 掘金
- `csdn` - CSDN
- `github` - GitHub
- `stackoverflow` - Stack Overflow

#### 视频媒体
- `bilibili` - B站
- `iqiyi` - 爱奇艺
- `youku` - 优酷
- `youtube` - YouTube

### 运行测试

提供了专门的测试脚本来验证功能：

```bash
python test_rsshub_fetcher.py
```

测试脚本会验证：
- URL 解析功能
- 协议转换功能
- 源可用性检查
- 实际内容获取
- 支持的服务列表

## 实现详情

### 核心模块

1. **`src/core/rsshub_fetcher.py`** - RSSHub 协议处理器
   - `RSSHubFetcher` 类：主要处理逻辑
   - `is_rsshub_url()` - 检查是否是 rsshub:// 协议
   - `parse_rsshub_url()` - 解析 rsshub:// URL
   - `convert_to_http_url()` - 转换为 HTTP URL
   - `fetch_rsshub_feed()` - 获取RSS内容
   - `test_rsshub_url()` - 测试URL可用性

2. **修改 `src/core/pipeline.py`** - 集成到主流程
   - 在 `run_stage_fetch()` 方法中添加了 RSSHub 支持
   - 自动分离常规 RSS 源和 RSSHub 源
   - 统一处理和合并结果

### 工作流程

1. **URL 识别**：系统自动识别配置中的 `rsshub://` 协议源
2. **协议转换**：将 `rsshub://` URL 转换为实际的 HTTP URL
3. **实例轮询**：依次尝试多个 RSSHub 实例
4. **内容获取**：使用现有的 RSS fetcher 获取和解析内容
5. **结果合并**：将 RSSHub 源的结果与常规源合并

### 错误处理

- 连接超时：自动切换到下一个 RSSHub 实例
- HTTP 错误 (如429限流)：自动重试并切换实例
- 连接错误：尝试备用实例
- 解析失败：记录错误并继续处理其他源

## 实际应用示例

以澎湃思想的订阅源为例：

```yaml
# 配置文件中的条目
- name: "澎湃思想"
  url: "rsshub://thepaper/list/25483"
  enabled: true

# 系统内部转换过程：
# 原始URL: rsshub://thepaper/list/25483
# 解析结果: 
#   服务: thepaper
#   路由: list/25483
#   完整路径: thepaper/list/25483

# 转换后的HTTP URL:
# https://rsshub.app/thepaper/list/25483
# https://rsshub.smzdm.com/thepaper/list/25483
# https://rsshub.t1qx.com/thepaper/list/25483
# https://rsshub.iowen.cn/thepaper/list/25483
```

## 注意事项

1. **网络限制**：由于公共 RSSHub 实例可能有访问限制，建议在实际使用中根据网络环境调整重试参数
2. **内容时效性**：RSSHub 源的内容更新频率可能与官方 RSS 源有所不同
3. **可用性检查**：建议定期检查 RSSHub 实例的可用性，系统已内置自动切换机制

## 总结

这个实现提供了一个完整的、稳定的 rsshub:// 协议支持方案：

✅ **单独的Python文件实现** - `src/core/rsshub_fetcher.py`  
✅ **稳定的订阅源支持** - 包括澎湃思想的 `rsshub://thepaper/list/25483`  
✅ **完整集成到现有系统** - 支持配置文件和命令行使用  
✅ **多实例备用机制** - 确保服务的可靠性  
✅ **详细测试验证** - 提供完整的测试脚本和文档  

现在用户可以在配置文件中直接使用 `rsshub://` 协议的订阅源，享受 RSSHub 丰富的订阅源生态。