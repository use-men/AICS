# ============================================
# Stage 1: 构建前端
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /build

# 先复制依赖文件，利用 Docker 缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build


# ============================================
# Stage 2: 运行时
# ============================================
FROM python:3.11-slim

WORKDIR /app

# 使用国内镜像源加速
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
RUN pip install --no-cache-dir --upgrade pip

# 安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 从前端构建阶段复制产物
COPY --from=frontend-builder /build/dist /app/frontend/dist

EXPOSE 8000

CMD ["python", "main.py"]
