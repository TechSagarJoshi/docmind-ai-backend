from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.deps import get_current_user
from app.services import supabase_service as sb

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    language: Optional[str] = None


@router.get("")
async def get_my_profile(user=Depends(get_current_user)):
    profile = sb.get_profile(user["id"])
    stats = sb.get_profile_stats(user["id"])

    if not profile:
        # Auto-create if missing
        profile = {
            "id": user["id"],
            "email": user["email"],
            "full_name": None,
            "plan": "free",
            "credits": 10,
        }

    return {
        "profile": {
            **profile,
            "email": user["email"],
        },
        "stats": stats,
    }


@router.patch("")
async def update_my_profile(
    updates: ProfileUpdate,
    user=Depends(get_current_user),
):
    # Convert None to nothing (only send provided fields)
    payload = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not payload:
        raise HTTPException(400, "No fields to update")

    # Trim string values
    for k, v in payload.items():
        if isinstance(v, str):
            payload[k] = v.strip()

    # Validate bio length
    if "bio" in payload and len(payload["bio"]) > 500:
        raise HTTPException(400, "Bio must be 500 characters or less")

    updated = sb.update_profile(user["id"], payload)
    if not updated:
        raise HTTPException(500, "Failed to update profile")

    return {"profile": updated}

from typing import Optional


class SettingsUpdate(BaseModel):
    theme: Optional[str] = None
    notifications_email: Optional[bool] = None
    notifications_marketing: Optional[bool] = None
    default_output_format: Optional[str] = None
    auto_delete_days: Optional[int] = None
    analytics_opt_in: Optional[bool] = None


@router.get("/settings")
async def get_my_settings(user=Depends(get_current_user)):
    s = sb.get_settings(user["id"])
    if not s:
        # Return defaults if no row yet
        s = {
            "user_id": user["id"],
            "theme": "system",
            "notifications_email": True,
            "notifications_marketing": False,
            "default_output_format": "jpg",
            "auto_delete_days": 0,
            "analytics_opt_in": True,
        }
    return {"settings": s}


@router.patch("/settings")
async def update_my_settings(
    updates: SettingsUpdate,
    user=Depends(get_current_user),
):
    payload = {k: v for k, v in updates.model_dump().items() if v is not None}

    if not payload:
        raise HTTPException(400, "No settings to update")

    if "theme" in payload and payload["theme"] not in ("light", "dark", "system"):
        raise HTTPException(400, "theme must be light, dark, or system")
    if "auto_delete_days" in payload and payload["auto_delete_days"] < 0:
        raise HTTPException(400, "auto_delete_days must be >= 0")

    updated = sb.upsert_settings(user["id"], payload)
    if not updated:
        raise HTTPException(500, "Failed to update settings")

    return {"settings": updated}


@router.post("/delete-all-files")
async def delete_all_files(user=Depends(get_current_user)):
    count = sb.delete_all_user_files(user["id"])
    return {"deleted": count}