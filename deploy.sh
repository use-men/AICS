#!/bin/bash
# SmartDesk 手动部署脚本
# 使用方法: bash deploy.sh

set -e

echo "=========================================="
echo "  SmartDesk 部署脚本"
echo "=========================================="

# 1. 进入项目目录
echo ""
echo "📂 进入项目目录..."
cd /opt/SmartDesk || { echo "❌ 目录不存在: /opt/SmartDesk"; exit 1; }

# 2. 拉取最新代码
echo ""
echo "📥 拉取最新代码..."
git pull origin main

# 3. 创建 .env 文件（如果不存在）
if [ ! -f .env ]; then
    echo ""
    echo "📝 创建 .env 文件..."
    cat > .env << 'EOF'
# DeepSeek API Key（必填）
DEEPSEEK_API_KEY=your-api-key-here

# 数据库配置
DATABASE_URL=mysql+aiomysql://root:root@db:3306/smartdesk
REDIS_URL=redis://redis:6379/0

# JWT 密钥
JWT_SECRET_KEY=change-me-in-production

# CORS
CORS_ORIGINS=["http://localhost:8000"]
EOF
    echo "⚠️  请编辑 .env 文件填入正确的 DEEPSEEK_API_KEY"
    echo "    vim /opt/SmartDesk/.env"
fi

# 4. 停止旧容器
echo ""
echo "⏹  停止旧容器..."
docker-compose down

# 5. 重新构建并启动
echo ""
echo "🔨 构建并启动容器..."
docker-compose up -d --build

# 6. 等待 MySQL 就绪
echo ""
echo "⏳ 等待 MySQL 就绪..."
sleep 20

# 7. 初始化数据库
echo ""
echo "🗃  初始化数据库..."
docker-compose exec -T backend python scripts/init_db.py || true
docker-compose exec -T backend python scripts/seed.py || true
docker-compose exec -T backend python scripts/seed_cs.py || true
docker-compose exec -T backend python scripts/seed_roles.py || true

# 8. 健康检查
echo ""
echo "🔍 健康检查..."
for i in 1 2 3 4 5; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo "=========================================="
        echo "  ✅ 部署成功！"
        echo "=========================================="
        echo ""
        echo "  服务地址: http://$(hostname -I | awk '{print $1}'):8000"
        echo "  健康检查: http://$(hostname -I | awk '{print $1}'):8000/health"
        echo "  API 文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
        echo ""
        exit 0
    fi
    echo "  尝试 $i/5..."
    sleep 3
done

echo ""
echo "❌ 健康检查失败，请查看日志："
docker-compose logs --tail=30 backend
exit 1
