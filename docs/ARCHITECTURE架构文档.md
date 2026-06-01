# b1t-AI 架构设计文档

> 系统架构与技术实现详解

---

## 1. 系统架构概览

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  对话界面   │  │  文件上传   │  │  余额/统计面板      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                      HTML5 + CSS3 + Vanilla JS               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/REST + SSE
┌─────────────────────────────────────────────────────────────┐
│                      API 网关层 (FastAPI)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ /api/chat   │  │ /api/upload │  │   /api/stream       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                      CORS / 生命周期管理 / 错误处理            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Agent 核心层 (Core)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              ReActPlanner (推理规划器)                  │  │
│  │   Thought → Action → Observation → (循环/结束)         │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  LLM 接口   │  │  记忆系统   │  │    工具注册表       │  │
│  │  DeepSeek   │  │  三层架构   │  │    动态管理         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      能力层 (Capabilities)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────┐  │
│  │  WebSearch  │  │ Calculator  │  │ CodeExecutor│  │File│  │
│  │  DuckDuckGo │  │  AST解析    │  │  沙箱执行   │  │Mgr │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件职责

| 组件 | 职责 | 技术实现 |
|------|------|----------|
| Frontend | 用户界面、交互逻辑 | HTML5, CSS3, JavaScript |
| FastAPI | HTTP API、WebSocket、生命周期管理 | FastAPI, Uvicorn |
| Agent Core | 对话管理、ReAct规划、组件协调 | Python AsyncIO |
| LLM Provider | 大模型调用、流式响应 | OpenAI SDK |
| Memory System | 短期/长期/工作记忆管理 | ChromaDB, In-Memory |
| Tool Registry | 工具注册、发现、调度 | 插件化架构 |
| Tools | 具体工具实现 | 多语言支持 |

---

## 2. 核心模块详解

### 2.1 ReAct 规划器

#### 2.1.1 设计原理

基于论文 [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) 实现，将推理(Reasoning)和行动(Acting)结合，通过交替进行思考、行动、观察来解决问题。

#### 2.1.2 状态机

```
                    ┌─────────────┐
                    │ INITIALIZING│
                    └──────┬──────┘
                           │
                           ▼
┌──────────┐        ┌─────────────┐        ┌──────────┐
│  FAILED  │◄───────│  REASONING  │───────►│  ACTING  │
└──────────┘        └──────┬──────┘        └────┬─────┘
                           │                    │
                           │                    ▼
                           │              ┌──────────┐
                           │              │OBSERVING │
                           │              └────┬─────┘
                           │                   │
                           └───────────────────┘
                           (循环或结束)
```

#### 2.1.3 核心类设计

```python
class ReActPlanner:
    """ReAct 规划器主类"""
    
    # 配置参数
    max_iterations: int = 8          # 最大迭代次数
    max_execution_time: int = 120    # 最大执行时间(秒)
    max_consecutive_failures: int = 3 # 最大连续失败次数
    
    async def plan_and_execute(self, query: str, context: Dict) -> PlanExecutionResult:
        """执行 ReAct 循环"""
        
        for iteration in range(self.max_iterations):
            # 1. 生成思考
            thought = await self._generate_thought(query, result)
            
            # 2. 解析行动
            action = self._parse_action_from_thought(thought.content)
            
            # 3. 执行工具
            observation = await self._execute_action(action)
            
            # 4. 检查是否完成
            if self._is_final_answer(thought.content):
                return PlanExecutionResult(success=True, ...)
        
        return PlanExecutionResult(success=False, ...)
```

#### 2.1.4 Action 解析策略

采用三级解析策略，逐级降级：

1. **策略1**: 函数调用格式匹配
   ```
   calculator(expression="2+2")
   ```

2. **策略2**: 结构化格式匹配
   ```
   **Action:** calculator
   **Parameters:** {"expression": "2+2"}
   ```

3. **策略3**: 宽松搜索回退
   - 从文本中提取工具名称和参数

### 2.2 工具系统

#### 2.2.1 插件化架构

```python
class BaseTool(ABC):
    """工具基类"""
    
    name: str                    # 工具标识
    description: str             # 功能描述
    parameters: Dict             # JSON Schema 参数定义
    
    def __init_subclass__(cls, **kwargs):
        """子类定义时自动注册"""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'name') and cls.name:
            tool_registry.register(cls())
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass
```

#### 2.2.2 工具注册表

```python
class ToolRegistry:
    """全局工具注册表 (单例模式)"""
    
    _instance: Optional['ToolRegistry'] = None
    _tools: Dict[str, BaseTool] = {}
    _enabled: Set[str] = set()
    
    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        self._enabled.add(tool.name)
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具实例"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict]:
        """列出所有可用工具"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for name, tool in self._tools.items()
            if name in self._enabled
        ]
```

### 2.3 记忆系统

#### 2.3.1 三层记忆架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户输入                            │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────┐
│   短期记忆       │ │   工作记忆   │ │   长期记忆   │
│  (Short-term)   │ │  (Working)  │ │  (Long-term) │
├─────────────────┤ ├─────────────┤ ├─────────────┤
│ • 最近10轮对话  │ │ • 任务进度   │ │ • 用户偏好   │
│ • 8000 tokens   │ │ • 中间变量   │ │ • 重要事实   │
│ • FIFO淘汰     │ │ • 临时状态   │ │ • 历史记录   │
│ • 内存存储     │ │ • 随任务销毁 │ │ • 向量检索   │
└─────────────────┘ └─────────────┘ └─────────────┘
```

#### 2.3.2 短期记忆实现

```python
class ShortTermMemory:
    """短期记忆 - 滑动窗口管理"""
    
    window_size: int = 10        # 窗口大小
    max_tokens: int = 8000       # Token 上限
    
    def add_turn(self, user_msg: Message, assistant_msg: Message):
        """添加一轮对话"""
        turn = ConversationTurn(
            user_message=user_msg,
            assistant_message=assistant_msg,
            timestamp=datetime.now()
        )
        self._history.append(turn)
        
        # 检查 Token 限制
        total_tokens = self._estimate_tokens()
        while total_tokens > self.max_tokens and len(self._history) > 1:
            self._history.pop(0)  # FIFO 淘汰
            total_tokens = self._estimate_tokens()
    
    def _estimate_tokens(self, text: str) -> int:
        """中文 Token 估算 (4字符/token)"""
        return len(text) // 4 + len(text) % 4 > 0
```

#### 2.3.3 长期记忆实现

```python
class LongTermMemory:
    """长期记忆 - 向量数据库存储"""
    
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("memories")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def add_memory(self, content: str, memory_type: str):
        """添加记忆"""
        embedding = self.embedding_model.encode(content)
        self.collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[{"type": memory_type}],
            ids=[str(uuid.uuid4())]
        )
    
    async def search(self, query: str, top_k: int = 5) -> List[str]:
        """检索相关记忆"""
        query_embedding = self.embedding_model.encode(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        return results['documents'][0]
```

### 2.4 安全机制

#### 2.4.1 代码执行安全

```python
class CodeExecutor(BaseTool):
    """安全代码执行器"""
    
    # 危险代码模式
    DANGEROUS_PATTERNS = [
        r'import\s+os',
        r'import\s+subprocess',
        r'__import__',
        r'eval\s*\(',
        r'exec\s*\(',
        r'system\s*\(',
        r'open\s*\(',
    ]
    
    # AST 白名单
    SAFE_OPERATORS = {
        ast.Add, ast.Sub, ast.Mult, ast.Div,
        ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd
    }
    
    SAFE_FUNCTIONS = {'abs', 'round', 'min', 'max', 'sum', 'pow', 'len'}
    
    async def execute(self, code: str, language: str = "python") -> ToolResult:
        # 1. 危险代码检测
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                return ToolResult(success=False, error="检测到危险代码")
        
        # 2. AST 语法检查
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if node.func.id not in self.SAFE_FUNCTIONS:
                        return ToolResult(success=False, error="禁止的函数调用")
        except SyntaxError:
            return ToolResult(success=False, error="语法错误")
        
        # 3. 子进程执行
        process = await asyncio.create_subprocess_exec(
            sys.executable, temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024*1024  # 1MB 输出限制
        )
        
        # 4. 超时控制
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return ToolResult(success=False, error="执行超时")
```

#### 2.4.2 文件操作安全

```python
class FileManager(BaseTool):
    """安全文件管理器"""
    
    base_path: Path = Path("./workspace")
    allowed_extensions: Set[str] = {'.txt', '.md', '.py', '.json', '.csv'}
    
    def _validate_path(self, path: str) -> Path:
        """路径安全校验"""
        # 解析路径
        target = self.base_path / path
        resolved = target.resolve()
        
        # 检查是否在 base_path 下
        if not str(resolved).startswith(str(self.base_path.resolve())):
            raise SecurityError("路径遍历攻击检测")
        
        # 检查扩展名
        if resolved.suffix not in self.allowed_extensions:
            raise SecurityError(f"不允许的文件类型: {resolved.suffix}")
        
        return resolved
```

---

## 3. 数据流

### 3.1 对话流程

```
用户输入
    │
    ▼
┌─────────────────┐
│  前端界面        │
│  - 文件上传      │
│  - 参数组装      │
└────────┬────────┘
         │ HTTP POST /api/chat
         ▼
┌─────────────────┐
│  FastAPI 路由    │
│  - 请求验证      │
│  - 附件处理      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Agent.process() │────►│  ReActPlanner   │
│                 │     │  - 生成 Thought  │
└────────┬────────┘     │  - 解析 Action   │
         │              │  - 执行工具      │
         │              │  - 循环或结束    │
         │              └─────────────────┘
         │
         ▼
┌─────────────────┐
│  LLM Provider   │
│  - DeepSeek API │
│  - 流式响应     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  响应组装        │
│  - 结果格式化    │
│  - Token 统计    │
└────────┬────────┘
         │ JSON Response
         ▼
┌─────────────────┐
│  前端展示        │
│  - Markdown渲染  │
│  - 代码高亮      │
└─────────────────┘
```

### 3.2 文件上传流程

```
用户选择文件
    │
    ▼
┌─────────────────┐
│  前端 FileReader │
│  - 类型检查      │
│  - 大小检查      │
└────────┬────────┘
         │ FormData
         ▼
┌─────────────────┐
│  /api/upload    │
│  - 文件保存      │
│  - 类型识别      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  内容提取        │
├─────────────────┤
│ 文本: 直接读取   │
│ PDF: PyPDF2     │
│ DOCX: python-docx│
│ 图片: Vision API │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  返回内容        │
│  - 文件名        │
│  - 文件类型      │
│  - 提取内容      │
└─────────────────┘
```

---

## 4. 技术选型

### 4.1 后端技术栈

| 组件 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| Web 框架 | FastAPI | 0.100+ | 高性能、自动文档、类型安全 |
| ASGI 服务器 | Uvicorn | 0.23+ | 异步支持、生产就绪 |
| LLM 客户端 | OpenAI SDK | 1.0+ | 标准接口、流式支持 |
| 数据验证 | Pydantic | 2.0+ | 类型安全、性能优秀 |
| 配置管理 | PyYAML + Pydantic | - | 灵活配置、类型校验 |
| 日志 | Rich + logging | - | 彩色输出、结构化日志 |
| 向量数据库 | ChromaDB | 0.4+ | 轻量、本地优先 |
| 嵌入模型 | SentenceTransformers | - | 本地推理、无需 API |

### 4.2 前端技术栈

| 组件 | 技术 | 选型理由 |
|------|------|----------|
| 框架 | 原生 JavaScript | 轻量、无依赖、快速加载 |
| Markdown | Marked.js | 标准、可扩展 |
| 代码高亮 | Highlight.js | 语言丰富、主题多样 |
| 样式 | CSS3 + Flexbox | 现代布局、响应式 |
| 通信 | Fetch API + SSE | 标准 API、实时推送 |

---

## 5. 部署架构

### 5.1 单机部署

```
┌─────────────────────────────────────┐
│           用户浏览器                 │
└─────────────┬───────────────────────┘
              │ HTTP/WebSocket
┌─────────────▼───────────────────────┐
│        服务器 (单实例)               │
│  ┌─────────────────────────────┐    │
│  │  Uvicorn (ASGI Server)      │    │
│  │  ┌─────────────────────┐    │    │
│  │  │  FastAPI Application │    │    │
│  │  │  ┌─────────────┐    │    │    │
│  │  │  │  Agent Core │    │    │    │
│  │  │  │  ┌───────┐  │    │    │    │
│  │  │  │  │ Tools │  │    │    │    │
│  │  │  │  └───────┘  │    │    │    │
│  │  │  └─────────────┘    │    │    │
│  │  └─────────────────────┘    │    │
│  └─────────────────────────────┘    │
│                                     │
│  数据存储:                          │
│  - 向量数据: ./data/chromadb/       │
│  - 上传文件: ./uploads/             │
│  - 工作文件: ./workspace/           │
│  - 日志文件: ./logs/                │
└─────────────────────────────────────┘
```

### 5.2 环境要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 10 GB | 50 GB |
| 网络 | 10 Mbps | 100 Mbps |

---

## 6. 扩展设计

### 6.1 新增工具

```python
# 1. 继承 BaseTool
class MyTool(BaseTool):
    name = "my_tool"
    description = "工具描述"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string"}
        }
    }
    
    async def execute(self, param1: str) -> ToolResult:
        # 实现逻辑
        return ToolResult(success=True, result="...")

# 2. 自动注册 (无需额外操作)
# 定义时自动注册到 tool_registry

# 3. 配置启用
# configs/config.yaml:
tools:
  my_tool:
    enabled: true
```

### 6.2 新增 LLM 提供商

```python
# 1. 实现 LLMProvider 接口
class ClaudeProvider(LLMProvider):
    async def chat(self, messages: List[Message]) -> LLMResponse:
        # 调用 Claude API
        pass
    
    async def chat_stream(self, messages: List[Message]):
        # 流式响应
        pass

# 2. 配置切换
# configs/config.yaml:
llm:
  provider: "claude"
  model: "claude-3-opus-20240229"
```

---

## 7. 监控与日志

### 7.1 日志结构

```
logs/
├── agent.log          # 应用日志
├── access.log         # 访问日志
└── error.log          # 错误日志
```

### 7.2 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| api_latency | API 响应延迟 | > 5s |
| token_usage | Token 使用量 | > 100K/小时 |
| tool_success_rate | 工具成功率 | < 90% |
| error_rate | 错误率 | > 5% |
| memory_usage | 内存使用 | > 80% |

---

## 8. 附录

### 8.1 目录结构

```
Agent/
├── main.py                 # FastAPI 入口
├── src/
│   ├── agent/             # Agent 核心
│   │   ├── core.py        # Agent 主类
│   │   └── planner.py     # ReAct 规划器
│   ├── llm/               # LLM 接口
│   │   ├── provider.py    # 提供商实现
│   │   └── prompts.py     # 提示词模板
│   ├── memory/            # 记忆系统
│   │   ├── short_term.py  # 短期记忆
│   │   ├── long_term.py   # 长期记忆
│   │   └── working_memory.py # 工作记忆
│   ├── tools/             # 工具集合
│   │   ├── base.py        # 工具基类
│   │   ├── calculator.py  # 计算器
│   │   ├── code_executor.py # 代码执行
│   │   ├── file_manager.py  # 文件管理
│   │   └── web_search.py    # 网络搜索
│   └── utils/             # 工具函数
│       ├── config.py      # 配置管理
│       └── logger.py      # 日志系统
├── frontend/              # 前端代码
├── configs/               # 配置文件
├── docs/                  # 文档
├── workspace/             # 工作目录
└── uploads/               # 上传目录
```

### 8.2 参考资料

- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [ChromaDB 文档](https://docs.trychroma.com/)
