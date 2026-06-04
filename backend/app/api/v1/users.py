from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
async def list_users():
    return {"data": [], "total": 0}


@router.get("/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id, "username": "user"}
