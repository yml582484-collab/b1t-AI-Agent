# b1t-AI API 接口文档

> RESTful API 接口说明

---

## 基础信息

- **Base URL**: `http://localhost:8005`
- **API 版本**: v1
- **Content-Type**: `application/json`

---

## 接口列表

### 1. 对话接口

#### 1.1 普通对话

**Endpoint**: `POST /api/chat`

**请求参数**:

```json
{
  "message": "string, required",
  "session_id": "string, optional",
  "use_react": "boolean, default: true",
  "attachments": [
    {
      "filename": "string",
      "type": "string",
      "content": "string",
      "url": "string"
    }
  ]
}
```

**响应**:

```json
{
  "success": true,
  "response": "AI 回复内容",
  "metadata": {
    "steps_completed": 5,
    "state": "completed",
    "tools_used": ["calculator"],
    "token_usage": {
      "prompt_tokens": 1500,
      "completion_tokens": 800,
      "total_tokens": 2300
    }
  }
}
```

**示例**:

```bash
curl -X POST http://localhost:8005/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "计算 123 的平方根",
    "use_react": true
  }'
```

#### 1.2 流式对话

**Endpoint**: `POST /api/chat/stream`

**请求参数**: 同普通对话

**响应**: SSE (Server-Sent Events)

```
data: {"content": "正在", "is_complete": false}
data: {"content": "正在计算", "is_complete": false}
data: {"content": "正在计算...", "is_complete": false}
data: {"content": "123 的平方根约等于 11.09", "is_complete": true}
```

---

### 2. 文件接口

#### 2.1 文件上传

**Endpoint**: `POST /api/upload`

**请求参数**: `multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| file | File | 上传的文件 |

**响应**:

```json
{
  "success": true,
  "filename": "example.txt",
  "type": "text",
  "content": "文件内容...",
  "url": "/uploads/abc123_example.txt"
}
```

**示例**:

```bash
curl -X POST http://localhost:8005/api/upload \
  -F "file=@example.txt"
```

---

### 3. 系统接口

#### 3.1 获取余额

**Endpoint**: `GET /api/usage`

**响应**:

```json
{
  "success": true,
  "data": {
    "balance": "1.53",
    "currency": "CNY",
    "total_tokens": 150000,
    "total_cost": "0.45"
  }
}
```

#### 3.2 获取工具列表

**Endpoint**: `GET /api/tools`

**响应**:

```json
{
  "success": true,
  "tools": [
    {
      "name": "calculator",
      "description": "执行数学计算",
      "parameters": {
        "type": "object",
        "properties": {
          "expression": {"type": "string"}
        }
      }
    }
  ]
}
```

#### 3.3 系统状态

**Endpoint**: `GET /api/status`

**响应**:

```json
{
  "success": true,
  "status": "running",
  "version": "1.0.0",
  "uptime": 3600,
  "active_sessions": 5
}
```

#### 3.4 健康检查

**Endpoint**: `GET /api/health`

**响应**:

```json
{
  "status": "healthy"
}
```

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 422 | 验证错误 |
| 500 | 服务器内部错误 |

---

## 附件类型

| 类型 | MIME Type | 说明 |
|------|-----------|------|
| text | text/plain | 文本文件 |
| code | text/x-python | 代码文件 |
| pdf | application/pdf | PDF 文档 |
| docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document | Word 文档 |
| image | image/png, image/jpeg | 图片文件 |
