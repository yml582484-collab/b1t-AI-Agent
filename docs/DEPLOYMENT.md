# b1t-AI 部署指南

> 生产环境部署说明

---

## 1. 环境要求

### 1.1 系统要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 10 GB | 50 GB |
| 网络 | 10 Mbps | 100 Mbps |

### 1.2 软件依赖

- Python 3.9+
- pip 21.0+
- Git 2.30+

---

## 2. 安装步骤

### 2.1 克隆仓库

```bash
git clone https://github.com/yml582484-collab/Agent.git
cd Agent
```

### 2.2 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

### 2.4 配置环境变量

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

获取 API Key:
- DeepSeek: https://platform.deepseek.com
- SiliconFlow: https://cloud.siliconflow.cn

### 2.5 启动服务

**开发模式**:
```bash
python main.py --port 8005 --reload
```

**生产模式**:
```bash
python main.py --port 8005
```

或使用启动脚本:
```bash
# Windows
start.bat
```

---

## 3. 生产部署

### 3.1 使用 systemd (Linux)

创建服务文件 `/etc/systemd/system/bit-ai.service`:

```ini
[Unit]
Description=b1t-AI Agent Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Agent
Environment=PATH=/path/to/Agent/venv/bin
ExecStart=/path/to/Agent/venv/bin/python main.py --port 8005
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bit-ai
sudo systemctl start bit-ai
```

### 3.2 使用 Docker

创建 `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8005

CMD ["python", "main.py", "--port", "8005"]
```

构建并运行:
```bash
docker build -t bit-ai .
docker run -d -p 8005:8005 --env-file .env bit-ai
```

### 3.3 使用 Nginx 反向代理

配置 `/etc/nginx/sites-available/bit-ai`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

启用配置:
```bash
sudo ln -s /etc/nginx/sites-available/bit-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 4. 监控与维护

### 4.1 日志查看

```bash
# 实时查看日志
tail -f logs/agent.log

# 查看错误日志
tail -f logs/error.log
```

### 4.2 性能监控

```bash
# 查看进程状态
ps aux | grep python

# 查看端口占用
netstat -tlnp | grep 8005

# 查看资源使用
top -p $(pgrep -d',' python)
```

### 4.3 备份策略

```bash
# 备份数据目录
tar -czvf backup-$(date +%Y%m%d).tar.gz workspace/ uploads/ data/

# 定时备份 (crontab)
0 2 * * * cd /path/to/Agent && tar -czvf backup-$(date +\%Y\%m\%d).tar.gz workspace/ uploads/ data/
```

---

## 5. 故障排查

### 5.1 常见问题

**问题1**: 端口被占用
```bash
# 查找占用进程
lsof -i :8005

# 或
netstat -tlnp | grep 8005

# 终止进程
kill -9 <PID>
```

**问题2**: 依赖安装失败
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**问题3**: API 调用失败
- 检查 `.env` 中的 API Key 是否正确
- 检查网络连接
- 查看 `logs/error.log` 获取详细错误信息

### 5.2 联系支持

- GitHub Issues: https://github.com/yml582484-collab/Agent/issues
