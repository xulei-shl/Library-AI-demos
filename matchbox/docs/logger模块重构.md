Logger 模块重构计划
背景
在当前的架构中，logger 模块被多个层级的核心业务模块直接引用。根据项目架构分析，logger 位于工具层（src/utils/logger.py），而业务层（如领域层和应用层）直接依赖于该工具层，这违反了分层架构设计中 "高内聚、低耦合" 的原则。具体来说，领域层和应用层不应该直接依赖表现层或工具层（如日志工具），这导致了架构的耦合度过高，并降低了维护性和扩展性。

目标
通过重构 logger 模块的使用方式，避免核心业务层（领域层和应用层）直接依赖 logger，改为使用依赖注入（DI）或者适配器模式，使各个层级之间的依赖更加合理，并符合分层架构的设计原则。

重构方案

1. 将 logger 移至基础设施层
   将 logger 模块归类为基础设施层的一部分，并通过适配器封装，使得其在领域层和应用层之间的依赖变得可控。具体操作如下：

封装 logger 逻辑：在基础设施层提供一个统一的接口，例如 ILogging 接口，定义记录日志的基本操作（如 info()、warning()、error() 等）。
实现适配器：在工具层中实现该接口，封装具体的日志记录逻辑（如 logging 或自定义日志方案）。
依赖注入：通过构造函数注入（或其他 DI 方式）将 ILogging 接口传递给业务层，而不是直接在业务层引用 logger。

2. 修改依赖关系
   领域层（domain） 和 应用层（application） 应该依赖于 ILogging 接口，而不是直接依赖 logger 模块。
   表现层（presentation） 可以继续依赖 logger，但这不应该影响业务逻辑的实现。
3. 增强日志功能的扩展性
   日志级别配置：通过配置文件或运行时参数设置日志级别，避免硬编码日志级别，提升灵活性。
   日志输出：支持将日志输出到多个目标（如控制台、文件、远程服务等），并提供可配置的输出格式。
4. 示例代码
   src/utils/logger.py（改动后的适配器实现）

```
import logging
from typing import Optional

class LoggerAdapter:
    def __init__(self, name: Optional[str] = None):
        self.logger = logging.getLogger(name or __name__)
        self.logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(ch)

    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
```

src/core/pipeline.py（依赖注入后的应用层使用）

```
from src.utils.logger import LoggerAdapter

class Pipeline:
    def __init__(self, logger: LoggerAdapter):
        self.logger = logger

    def run(self):
        self.logger.info("Pipeline started")
        # 执行具体逻辑
        self.logger.warning("Some warning message")
```

5. 改进后的依赖关系
   领域层、应用层和表现层之间通过接口进行解耦。
   logger 被基础设施层的适配器封装并注入到各层，而不是直接被引用。
   计划实施步骤
   阶段一：重构 logger 模块，封装为适配器。
   阶段二：更新业务层（如 pipeline.py, consensus/manager.py 等），引入 ILogging 接口并进行依赖注入。
   阶段三：调整测试模块，确保日志记录功能正常工作，并验证重构后的架构符合设计要求。
   阶段四：代码审查和优化，确保重构后的代码符合架构规范并且没有引入新的问题。
   预期效果
   架构解耦：各层之间的依赖关系变得更加合理，架构更加松耦合。
   扩展性提升：后期可以轻松切换日志框架或增加其他日志输出方式。
   可维护性增强：代码可读性和可维护性提高，减少了重复代码，降低了出错的可能性。