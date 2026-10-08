from fastapi import Header, HTTPException
from app.services.supabase_service import verify_token


async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = authorization.replace("Bearer ", "").strip()
    try:
        user = verify_token(token)
    except Exception as e:
        raise HTTPException(401, f"Invalid token: {e}")
    if not user:
        raise HTTPException(401, "User not found")
    return {"id": user.id, "email": getattr(user, "email", None)}