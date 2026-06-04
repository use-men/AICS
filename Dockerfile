FROM python:3.11-slim

WORKDIR /app

# 使用国内镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 升级 pip
RUN pip install --no-cache-dir --upgrade pip

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 复制前端构建产物
COPY frontend/dist/ /app/frontend/dist/

EXPOSE 8000

CMD ["python", "main.py"]
