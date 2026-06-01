# b1t-AI 智能助手 - AI Agent 产品项目

> **AI产品经理项目** | 基于 DeepSeek API 的企业级智能 Agent 系统

---

## 项目概述

b1t-AI 是一款面向个人和企业用户的智能 AI Agent 系统，基于 DeepSeek 大语言模型构建，采用 ReAct (Reasoning + Acting) 推理框架，支持多工具协同、文件智能管理、附件上传解析等核心能力。项目采用模块化架构设计，具备完整的会话管理、记忆系统和安全沙箱机制。

**项目地址**: https://github.com/yml582484-collab/Agent

---

## 核心功能与技术实现

### 1. 双模式对话系统

#### 1.1 快速对话模式
- **技术实现**: 直接调用 DeepSeek API，无需工具调用
- **适用场景**: 日常问答、创意写作、知识咨询
- **响应速度**: 平均 1-3 秒首 token 返回
- **Token 控制**: 支持 4K/8K/16K 上下文长度配置

#### 1.2 ReAct 推理模式（默认开启）
- **技术架构**: 基于 ReAct (Reason-Act-Observe) 论文实现
- **核心循环**: Thought → Action → Observation → Final Answer
- **迭代控制**: 最大 8 次迭代，120 秒超时保护
- **失败处理**: 连续 3 次失败自动降级为直接回答

**ReAct 执行流程**:
```
用户输入
    ↓
[思考] 分析问题 → 制定执行计划
    ↓
[行动] 调用工具（计算器/代码执行/文件管理/搜索）
    ↓
[观察] 获取工具执行结果
    ↓
判断：任务完成？→ 是：生成最终答案 / 否：继续循环
```

### 2. 多模态附件处理系统

#### 2.1 支持格式
| 类型 | 格式 | 处理方式 | 技术实现 |
|------|------|----------|----------|
| 文本文件 | .txt, .md, .csv, .json | 直接读取 | Python 内置 IO |
| 代码文件 | .py, .js, .html, .css, .java, .cpp 等 | 语法高亮 + 内容提取 | 扩展名识别 + 编码检测 |
| 文档文件 | .pdf | 文本提取 | PyPDF2 库 |
| 办公文档 | .docx | 段落提取 | python-docx 库 |
| 图片文件 | .png, .jpg, .jpeg, .gif, .webp | OCR 识别 | SiliconFlow Vision API |

#### 2.2 图片识别技术栈
- **模型**: Qwen/Qwen3-VL-8B-Instruct (SiliconFlow 托管)
- **输入**: Base64 编码图片
- **输出**: 场景描述 + 文字提取 + 内容理解
- **集成方式**: 异步 HTTP API 调用

#### 2.3 文件上传安全机制
- 文件类型白名单校验
- 文件大小限制 (默认 10MB)
- 临时文件自动清理
- 文件名随机化处理 (防止路径遍历)

### 3. 智能工具生态系统

#### 3.1 工具架构设计
```python
# 基于抽象基类的插件化设计
class BaseTool(ABC):
    name: str                    # 工具标识
    description: str             # 功能描述
    parameters: Dict             # JSON Schema 参数定义
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass

# 自动注册机制
class ToolRegistry:
    _tools: Dict[str, BaseTool]  # 全局工具仓库
    
    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
```

#### 3.2 内置工具详解

**计算器 (Calculator)**
- 安全机制: AST 语法树解析替代 eval()
- 支持运算: +, -, *, /, //, %, **, 括号优先级
- 支持函数: abs, round, min, max, sum, pow
- 安全限制: 禁止变量定义、函数定义、导入语句

**代码执行器 (CodeExecutor)**
- 执行环境: 子进程隔离
- 超时控制: 默认 30 秒强制终止
- 危险代码检测: 正则匹配 import os, subprocess, eval, exec 等
- 支持语言: Python (系统解释器), JavaScript (Node.js)
- 资源限制: 单核 CPU, 256MB 内存

**文件管理器 (FileManager)**
- 工作目录: `./workspace/` (可配置)
- 支持操作: read, write, append, list, delete, exists, info, search
- 安全限制: 
  - 路径解析后必须位于 base_path 下
  - 扩展名白名单 (.txt, .md, .py, .json, .csv)
  - 禁止路径遍历攻击 (../ 检测)

**网络搜索 (WebSearch)**
- 搜索引擎: DuckDuckGo (无需 API Key)
- 结果数量: 可配置 (默认 5 条)
- 返回字段: 标题、URL、摘要、来源时间

### 4. 三层记忆系统

#### 4.1 短期记忆 (ShortTermMemory)
- 存储介质: 内存 (Python List)
- 窗口大小: 默认 10 轮对话
- Token 限制: 8000 tokens
- 淘汰策略: FIFO (先进先出)
- 中文优化: 按 4 字符/token 估算

**数据结构**:
```python
class ConversationTurn:
    user_message: Message      # 用户输入
    assistant_message: Message # AI 回复
    timestamp: datetime        # 时间戳
    metadata: Dict             # 附加信息 (token 数、工具调用等)
```

#### 4.2 长期记忆 (LongTermMemory)
- 向量数据库: ChromaDB
- 嵌入模型: all-MiniLM-L6-v2 (384 维)
- 相似度算法: 余弦相似度
- 阈值: 0.7 (可配置)
- 最大返回: 5 条相关记忆
- 持久化: 本地文件存储 (`./data/chromadb/`)

**记忆类型分类**:
- `preference`: 用户偏好 (如"我喜欢 Python")
- `fact`: 重要事实 (如"用户是产品经理")
- `context`: 任务上下文
- `learning`: 学习记录

#### 4.3 工作记忆 (WorkingMemory)
- 用途: 单次任务执行期间的临时状态
- 生命周期: 随任务开始创建，结束销毁
- 存储内容: 任务进度、中间变量、错误记录

### 5. 安全与防护机制

#### 5.1 代码执行安全
```python
# AST 白名单机制
SAFE_OPERATORS = {
    ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd  # 一元运算符
}

SAFE_FUNCTIONS = {'abs', 'round', 'min', 'max', 'sum', 'pow', 'len'}

# 危险模式检测
DANGEROUS_PATTERNS = [
    r'import\s+os',
    r'import\s+subprocess',
    r'__import__',
    r'eval\s*\(',
    r'exec\s*\(',
    r'system\s*\(',
    r'open\s*\(',
]
```

#### 5.2 文件操作安全
- 路径规范化: `os.path.normpath()` + `resolve()`
- 前缀检查: 确保解析后路径以 base_path 开头
- 符号链接检测: 禁止跟随 symlink

#### 5.3 API 安全
- 环境变量隔离: 敏感信息存储于 `.env`
- 请求超时: 所有外部 API 调用设置 30 秒超时
- 重试机制: 指数退避 (1s, 2s, 4s, 8s)，最多 3 次

### 6. 前端交互设计

#### 6.1 技术栈
- 框架: 原生 JavaScript (ES6+)
- UI 组件: 自定义 CSS (无第三方 UI 库)
- Markdown 渲染: Marked.js
- 代码高亮: Highlight.js
- 样式: CSS3 + Flexbox + Grid

#### 6.2 核心功能实现

**文件上传交互**:
```javascript
// 拖拽上传 + 点击选择
// 多文件支持
// 实时预览 + 删除
// 上传进度显示
```

**流式响应显示**:
```javascript
// Server-Sent Events (SSE) 接收
// 逐字显示效果
// Markdown 实时渲染
// 代码块语法高亮
```

**余额实时查询**:
```javascript
// 调用 /api/usage 端点
// 显示 DeepSeek 官方余额
// 本地 Token 使用统计
// 成本估算 (基于输入/输出 Token)
```

#### 6.3 响应式设计
- 桌面端: 侧边栏常驻 (280px)
- 平板端: 侧边栏可折叠
- 移动端: 侧边栏变为抽屉式 (< 768px)

---

## 技术架构

### 系统架构图

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

### 后端技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Web 框架 | FastAPI | RESTful API + WebSocket |
| ASGI 服务器 | Uvicorn | 高性能异步服务 |
| LLM 客户端 | AsyncOpenAI | DeepSeek API 调用 |
| 数据验证 | Pydantic | 请求/响应模型 |
| 配置管理 | PyYAML + Pydantic | 类型安全的配置加载 |
| 日志 | Rich + logging | 彩色控制台输出 |
| 文件处理 | PyPDF2, python-docx | 文档解析 |
| 向量数据库 | ChromaDB | 长期记忆存储 |

### 前端技术栈

| 功能 | 技术 |
|------|------|
| Markdown 渲染 | Marked.js |
| 代码高亮 | Highlight.js |
| HTTP 请求 | Fetch API |
| 实时通信 | Server-Sent Events |
| 本地存储 | localStorage |

---

## 项目结构

```
Agent/
├── main.py                      # FastAPI 服务入口 (830行)
│   ├── API 路由定义
│   ├── 文件上传处理
│   ├── 视觉识别集成
│   └── 流式响应实现
│
├── start.bat                    # Windows 一键启动脚本
├── requirements.txt             # Python 依赖清单
├── .env.example                 # 环境变量模板
│
├── configs/
│   └── config.yaml              # 应用配置 (模型/记忆/工具)
│
├── frontend/                    # Web 前端
│   ├── index.html               # 主页面结构
│   └── static/
│       ├── css/style.css        # 样式表 (深色主题)
│       └── js/app.js            # 前端应用逻辑 (800+行)
│
├── src/                         # 核心源代码
│   ├── agent/
│   │   ├── core.py              # Agent 主类 (350行)
│   │   └── planner.py           # ReAct 规划器 (820行)
│   │
│   ├── llm/
│   │   ├── provider.py          # DeepSeek 提供商 (350行)
│   │   └── prompts.py           # 提示词模板 (250行)
│   │
│   ├── memory/
│   │   ├── short_term.py        # 短期记忆 (150行)
│   │   ├── long_term.py         # 长期记忆 (200行)
│   │   └── working_memory.py    # 工作记忆 (100行)
│   │
│   ├── tools/
│   │   ├── base.py              # 工具基类与注册表 (420行)
│   │   ├── web_search.py        # 网络搜索 (80行)
│   │   ├── calculator.py        # 安全计算器 (120行)
│   │   ├── code_executor.py     # 代码执行器 (180行)
│   │   └── file_manager.py      # 文件管理器 (250行)
│   │
│   └── utils/
│       ├── config.py            # 配置管理 (150行)
│       └── logger.py            # 日志系统 (100行)
│
├── workspace/                   # AI 文件操作目录
└── uploads/                     # 上传文件临时存储
```

---

## 核心代码亮点

### 1. ReAct 规划器实现

**文件**: `src/agent/planner.py` (820行)

**核心逻辑**:
```python
async def plan_and_execute(self, query: str, context: Dict) -> PlanExecutionResult:
    # 初始化执行状态
    result = PlanExecutionResult(query=query)
    
    for iteration in range(self.max_iterations):
        # 1. 生成思考
        thought = await self._generate_thought(query, result)
        result.thoughts.append(thought)
        
        # 2. 解析行动
        action = self._parse_action_from_thought(thought.content)
        if not action:
            continue
        result.actions.append(action)
        
        # 3. 执行工具
        observation = await self._execute_action(action)
        result.observations.append(observation)
        
        # 4. 检查是否完成
        if self._is_final_answer(thought.content):
            result.final_answer = self._extract_answer(thought.content)
            result.success = True
            break
    
    return result
```

**安全机制**:
- 最大迭代次数限制 (默认 8 次)
- 执行时间限制 (120 秒)
- 连续失败检测 (3 次失败后停止)

### 2. 工具自动注册机制

**文件**: `src/tools/base.py`

```python
class BaseTool(ABC):
    # 类属性定义工具元数据
    name: str
    description: str
    parameters: Dict
    
    def __init_subclass__(cls, **kwargs):
        """子类定义时自动注册"""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'name') and cls.name:
            tool_registry.register(cls())
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass

# 使用示例
class Calculator(BaseTool):
    name = "calculator"
    description = "执行数学计算"
    # 定义时自动注册，无需手动调用
```

### 3. 安全代码执行

**文件**: `src/tools/code_executor.py`

```python
async def execute(self, code: str, language: str = "python") -> ToolResult:
    # 1. 危险代码检测
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            return ToolResult(
                success=False,
                error="检测到危险代码模式"
            )
    
    # 2. 创建临时文件
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.py',
        delete=False
    ) as f:
        f.write(code)
        temp_path = f.name
    
    try:
        # 3. 子进程执行 (隔离环境)
        process = await asyncio.create_subprocess_exec(
            sys.executable, temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1024*1024  # 1MB 输出限制
        )
        
        # 4. 超时控制
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=self.timeout
        )
        
        return ToolResult(
            success=process.returncode == 0,
            result=stdout.decode(),
            error=stderr.decode() if stderr else None
        )
    finally:
        # 5. 清理临时文件
        os.unlink(temp_path)
```

### 4. 流式响应实现

**文件**: `main.py` (行 533-630)

```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        async for chunk in agent_instance.chat_stream(
            message=full_message,
            session_id=request.session_id
        ):
            # SSE 格式: data: {...}\n\n
            yield f"data: {json.dumps({
                'content': chunk.content,
                'is_complete': chunk.is_complete,
                'token_usage': chunk.token_usage
            })}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

---

## 产品数据与成果

### 功能完整性

| 模块 | 功能点 | 状态 |
|------|--------|------|
| 对话系统 | 普通对话 | ✅ |
| | ReAct 推理 | ✅ |
| | 流式响应 | ✅ |
| 文件处理 | 文本文件 | ✅ |
| | 代码文件 | ✅ |
| | PDF/DOCX | ✅ |
| | 图片识别 | ✅ |
| 工具系统 | 计算器 | ✅ |
| | 代码执行 | ✅ |
| | 文件管理 | ✅ |
| | 网络搜索 | ✅ |
| 记忆系统 | 短期记忆 | ✅ |
| | 长期记忆 | ✅ (可启用) |
| | 工作记忆 | ✅ |

### 代码规模

- **总代码行数**: ~5,000+ 行
- **后端代码**: ~3,500 行 (Python)
- **前端代码**: ~1,500 行 (JS/CSS/HTML)
- **测试覆盖**: 核心模块单元测试

### 性能指标

- **API 响应时间**: 平均 1-3 秒 (首 token)
- **文件上传**: 支持最大 10MB
- **并发处理**: 基于 FastAPI 异步架构
- **内存占用**: 约 200-300MB (运行时)

---

## 使用指南

### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/yml582484-collab/Agent.git
cd Agent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API 密钥
cp .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key

# 4. 启动服务
# 方式一: 一键启动 (Windows)
start.bat

# 方式二: 手动启动
python main.py --port 8005

# 5. 访问
# 浏览器打开 http://localhost:8005
```

### 配置说明

**环境变量** (`.env`):
```env
# 必需
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 可选 (图片识别)
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxx

# 可选 (模型选择)
DEEPSEEK_MODEL=deepseek-chat  # 或 deepseek-v4-pro
```

**配置文件** (`configs/config.yaml`):
```yaml
agent:
  max_iterations: 8        # ReAct 最大迭代次数
  max_execution_time: 120  # 最大执行时间(秒)

memory:
  short_term:
    window_size: 10        # 短期记忆窗口
    max_tokens: 8000       # Token 上限

tools:
  code_executor:
    timeout: 30            # 代码执行超时
    allowed_languages: ["python", "javascript"]
  
  file_manager:
    base_path: "./workspace"  # 文件工作目录
```

---

## 技术亮点总结

1. **完整的 ReAct 框架实现**: 从论文到工程实践，完整实现推理-行动-观察循环
2. **企业级安全设计**: 多层防护机制，确保代码执行和文件操作安全
3. **模块化架构**: 插件化工具系统，易于扩展新功能
4. **多模态支持**: 文本、代码、图片统一处理流程
5. **中文优化**: 全中文提示词，强制中文回复
6. **实时交互**: SSE 流式响应，余额实时查询

---

## 未来规划

- [ ] 接入更多 LLM 提供商 (OpenAI, Claude, 文心一言)
- [ ] 实现 Function Calling 标准格式
- [ ] 添加更多工具 (数据库查询、API 调用、邮件发送)
- [ ] 前端重构 (React + TypeScript)
- [ ] 用户认证与多租户支持
- [ ] 对话分享与导出功能

---

## 许可证

MIT License

## 致谢

- [DeepSeek](https://deepseek.com/) - 提供大语言模型 API
- [SiliconFlow](https://siliconflow.cn/) - 提供视觉模型 API
