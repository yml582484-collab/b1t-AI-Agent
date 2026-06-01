# b1t-AI 智能助手

基于 DeepSeek API 的智能 AI Agent 系统，支持 ReAct 推理、工具调用、文件管理和附件上传。

## 功能特性

- **智能对话**：基于 DeepSeek 大模型的自然语言交互
- **ReAct 推理**：支持多步推理和任务规划
- **工具调用**：内置计算器、代码执行、文件管理、网络搜索等工具
- **附件上传**：支持文本文件、代码文件、图片等多种格式
- **图片识别**：集成 SiliconFlow 视觉模型，自动识别图片内容
- **文件管理**：AI 可创建、读取、编辑本地文件
- **会话管理**：支持多会话历史记录

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制 `.env.example` 为 `.env`，并填入你的 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# DeepSeek API (必需)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# SiliconFlow API (图片识别功能需要)
SILICONFLOW_API_KEY=your_siliconflow_api_key_here
```

- DeepSeek API Key: https://platform.deepseek.com
- SiliconFlow API Key: https://cloud.siliconflow.cn (免费额度足够使用)

### 3. 启动服务

**方式一：使用启动脚本（推荐）**

双击 `start.bat` 自动启动服务器并打开浏览器。

**方式二：手动启动**

```bash
python main.py --port 8005
```

然后访问 http://localhost:8005

## 使用方法

### 基础对话

在输入框中输入问题，AI 会直接回答。

### 文件上传

1. 点击输入框旁的 **+** 按钮
2. 选择要上传的文件（支持 .txt, .md, .py, .json, .csv, .pdf, .docx, .jpg, .png 等）
3. 输入你的问题，AI 会自动分析文件内容

### ReAct 模式

ReAct 模式默认开启，AI 会：
- 分析问题并制定执行计划
- 调用工具（计算器、代码执行、文件管理等）
- 完成任务并生成结果

例如：
- "计算 123 的平方根" → 调用计算器
- "创建一个 Python 脚本保存到文件" → 生成代码并保存
- "搜索今天的天气" → 调用网络搜索

### 文件管理

AI 可以在 `workspace/` 文件夹中创建和管理文件：

- 创建文本文件："写一篇日记保存到文件"
- 创建代码文件："生成一个爬虫脚本保存为 .py 文件"
- 读取文件："读取 workspace/test.txt 的内容"

## 项目结构

```
Agent/
├── main.py                 # 主程序入口
├── start.bat              # Windows 启动脚本
├── requirements.txt       # Python 依赖
├── .env                   # 环境变量配置（需自行创建）
├── .env.example           # 环境变量示例
├── configs/
│   └── config.yaml        # 配置文件
├── frontend/              # Web 前端
│   ├── index.html
│   └── static/
│       ├── css/
│       └── js/
├── src/                   # 核心代码
│   ├── agent/            # Agent 核心逻辑
│   ├── llm/              # LLM 提供商
│   ├── memory/           # 记忆系统
│   ├── tools/            # 工具集合
│   └── utils/            # 工具函数
├── workspace/            # 文件管理工作目录
└── uploads/              # 上传文件临时存储
```

## 配置说明

### 模型选择

在 `.env` 中配置：

```env
# 轻量级模型（速度快、便宜）
DEEPSEEK_MODEL=deepseek-chat

# 专业版模型（推理能力强）
# DEEPSEEK_MODEL=deepseek-v4-pro
```

### 工具开关

在 `configs/config.yaml` 中启用/禁用工具：

```yaml
tools:
  web_search:
    enabled: true
  calculator:
    enabled: true
  code_executor:
    enabled: true
  file_manager:
    enabled: true
    config:
      base_path: "./workspace"
```

## 注意事项

1. **API 密钥安全**：`.env` 文件包含敏感信息，请勿提交到 GitHub
2. **文件保存位置**：AI 创建的文件默认保存在 `workspace/` 文件夹
3. **图片识别**：需要配置 SiliconFlow API 密钥
4. **网络搜索**：需要配置搜索引擎 API

## 技术栈

- **后端**：Python + FastAPI
- **前端**：原生 HTML + JavaScript
- **AI 模型**：DeepSeek API
- **视觉模型**：SiliconFlow Qwen-VL

## 许可证

MIT License

## 致谢

- [DeepSeek](https://deepseek.com/) 提供大模型 API
- [SiliconFlow](https://siliconflow.cn/) 提供视觉模型 API
