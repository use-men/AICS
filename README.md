# SmartDesk — AI 智能客服工单协同平台

> 基于 RAG + 多 Agent 协作的智能客服系统

## 功能特性

- 🤖 **AI 智能问答** — RAG 检索 + DeepSeek 大模型，流式输出
- 🔄 **自动转人工** — 低置信度/用户要求时自动创建工单 + 派单
- 💬 **实时聊天** — WebSocket 全双工通信，已读状态，在线状态
- 🤖 **AI 辅助回复** — 客服端一键生成推荐回复
- 📊 **AI 运营大屏** — ECharts 可视化分析
- 👥 **三端协同** — 用户端 / 客服端 / 管理端

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + Ant Design + ECharts + Redux Toolkit |
| 后端 | Python FastAPI + SQLAlchemy + FAISS |
| 数据库 | MySQL + Redis |
| AI | DeepSeek API + RAG + 多 Agent 协作 |
| 实时通信 | WebSocket (FastAPI) |
| 部署 | Docker + GitHub Actions CI/CD |

## 快速开始

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python main.py

# 前端
cd frontend
npm install
npm run dev
```

### Docker 部署

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 一键启动
docker-compose up -d
```

访问 http://localhost:8000

### 测试账号

| 端 | 账号 | 密码 |
|---|---|---|
| 用户端 | zhangsan | 123456 |
| 客服端 | cs_1001 | 123456 |
| 管理端 | admin | admin123 |

## 项目结构

```
SmartDesk/
├── backend/                 # FastAPI 后端
│   ├── app/ai/              # AI Agent 系统
│   │   ├── agents/          # 多 Agent 协作
│   │   ├── services/        # 业务服务
│   │   └── workflows/       # 工作流
│   ├── app/api/v1/          # API 接口
│   ├── app/models/          # 数据模型
│   └── main.py              # 入口
├── frontend/                # React 前端
│   ├── src/client/          # 用户端页面
│   ├── src/customer-service/# 客服端页面
│   ├── src/admin/           # 管理端页面
│   └── src/shared/          # 共享组件/Hook
├── .github/workflows/       # CI/CD 配置
├── Dockerfile               # Docker 构建
└── docker-compose.yml       # Docker 编排
```

## License

MIT
