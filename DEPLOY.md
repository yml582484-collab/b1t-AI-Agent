# b1t-AI-Agent 部署指南

## 推荐方案：Render 云平台部署（免费）

Render 提供免费的 Web 服务托管，适合个人/小团队使用，无需维护服务器。

### 快速部署步骤

#### 1. 准备工作
- 确保代码已推送到 GitHub: `https://github.com/yml582484-collab/b1t-AI-Agent`
- 准备好 DeepSeek API Key

#### 2. 在 Render 上创建服务

1. 访问 [Render Dashboard](https://dashboard.render.com/)
2. 点击 **New +** → **Web Service**
3. 选择你的 GitHub 仓库 `b1t-AI-Agent`
4. 配置如下：
   - **Name**: `b1t-ai-agent`（或你喜欢的名称）
   - **Region**: 选择离你最近的区域（如 Singapore）
   - **Branch**: `master`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`

5. 点击 **Advanced** 展开高级设置，添加环境变量：
   - `DEEPSEEK_API_KEY`: 你的 DeepSeek API 密钥
   - `DEEPSEEK_API_BASE`: `https://api.deepseek.com/v1`
   - `LOG_LEVEL`: `INFO`

6. 点击 **Create Web Service**

#### 3. 等待部署完成
- Render 会自动构建和部署
- 首次部署约需 2-3 分钟
- 部署成功后，会显示服务 URL，如 `https://b1t-ai-agent.onrender.com`

#### 4. 验证部署
访问以下地址验证：
- 前端界面：`https://你的服务名.onrender.com/`
- API 文档：`https://你的服务名.onrender.com/docs`
- 健康检查：`https://你的服务名.onrender.com/health`

---

## 备选方案

### Railway 部署
1. 访问 [Railway](https://railway.app/)
2. 从 GitHub 导入项目
3. 添加环境变量 `DEEPSEEK_API_KEY`
4. 自动部署完成

### 自有服务器部署
```bash
# 1. 克隆代码
git clone https://github.com/yml582484-collab/b1t-AI-Agent.git
cd b1t-AI-Agent

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入 DEEPSEEK_API_KEY

# 5. 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 环境变量说明

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE` | ❌ | API 基础地址，默认 `https://api.deepseek.com/v1` |
| `LOG_LEVEL` | ❌ | 日志级别，默认 `INFO` |
| `SILICONFLOW_API_KEY` | ❌ | 可选，用于图片识别功能 |

---

## 注意事项

1. **免费版限制**：Render 免费版会在 15 分钟无活动后休眠，首次访问需要等待唤醒（约 30 秒）
2. **API 密钥安全**：永远不要将 `.env` 文件提交到 GitHub
3. **文件上传**：上传的文件存储在临时目录，服务重启后会丢失

---

## 故障排查

### 部署失败
- 检查 `requirements.txt` 是否完整
- 查看 Render 的 Logs 标签页获取详细错误信息

### 服务启动后无法访问
- 确认 `PORT` 环境变量被正确使用（Render 会自动设置）
- 检查健康检查端点 `/health` 是否返回正常

### API 调用失败
- 确认 `DEEPSEEK_API_KEY` 已正确设置
- 检查 DeepSeek API 账户余额是否充足
