from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/conversations")
async def create_conversation(data: dict):
    return {"conversation_id": "conv-1", "title": data.get("title", "新对话")}


@router.get("/conversations")
async def list_conversations():
    return {"data": [], "total": 0}


@router.post("/conversations/{conv_id}/messages")
async def send_message(conv_id: str, data: dict):
    return {
        "user_message": {"message_id": "u1", "role": "user", "content": data.get("content")},
        "ai_response": {"message_id": "a1", "role": "assistant", "content": "Mock AI response"},
    }
