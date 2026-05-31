FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements-hf.txt .
RUN pip install --no-cache-dir -r requirements-hf.txt

# 复制项目文件
COPY . .

# 创建上传目录
RUN mkdir -p uploads

# 暴露端口
EXPOSE 7860

# 环境变量
ENV HOST=0.0.0.0
ENV PORT=7860

# 启动命令
CMD ["python", "main.py", "--port", "7860"]
