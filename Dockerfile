# ============================================================
# 智能火锅点餐顾问 - Docker 镜像（Cloud Run 部署）
# ============================================================
FROM python:3.11-slim

# 防止 Python 生成 .pyc 文件，强制 stdout/stderr 不缓冲
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先复制依赖文件以利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# Cloud Run 使用 PORT 环境变量（默认 8080）
ENV PORT=8080
EXPOSE 8080

# 启动 FastAPI（gunicorn + uvicorn worker 适合生产环境）
CMD exec uvicorn api:app --host 0.0.0.0 --port ${PORT} --workers 1
