from fastapi import APIRouter

api_v1_router = APIRouter()


# Auth
from app.api.v1 import auth  # noqa: E402
api_v1_router.include_router(auth.router)

# Users
from app.api.v1 import users  # noqa: E402
api_v1_router.include_router(users.router)

# Tickets
from app.api.v1 import tickets  # noqa: E402
api_v1_router.include_router(tickets.router)

# Chat
from app.api.v1 import chat  # noqa: E402
api_v1_router.include_router(chat.router)

# AI Agent
from app.api.v1 import agent  # noqa: E402
api_v1_router.include_router(agent.router)

# Knowledge Base
from app.api.v1 import knowledge  # noqa: E402
api_v1_router.include_router(knowledge.router)

# Dispatch
from app.api.v1 import dispatch  # noqa: E402
api_v1_router.include_router(dispatch.router)

# WebSocket
from app.api.v1 import ws  # noqa: E402
api_v1_router.include_router(ws.router)

# Chat WebSocket
from app.api.v1 import chat_ws  # noqa: E402
api_v1_router.include_router(chat_ws.router)
