from supabase import create_client, Client
from app.config import settings
import uuid

# Two Supabase clients:
#   - supabase:   service_role key → for storage & DB writes (bypasses RLS)
#   - auth_client: anon key         → for verifying user JWTs
supabase: Client | None = None
auth_client: Client | None = None

if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )
    except Exception:
        supabase = None

if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
    try:
        auth_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY,
        )
    except Exception:
        auth_client = None


def is_supabase_configured() -> bool:
    return supabase is not None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def verify_token(token: str):
    """Verify a user's JWT using the Supabase admin (service_role) client.

    The admin client can validate both HS256 and ES256 tokens because
    Supabase verifies server-side.
    """
    if supabase is None:
        print("[verify_token] supabase admin client not configured")
        return None
    try:
        res = supabase.auth.get_user(token)
        if not res or not res.user:
            print("[verify_token] no user in response")
            return None
        return res.user
    except Exception as e:
        print(f"[verify_token] failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def upload_file(user_id: str, filename: str, content: bytes, content_type: str) -> str:
    """Upload bytes to Supabase Storage. Returns storage path."""
    path = f"{user_id}/{filename}"
    if not is_supabase_configured():
        return path
    try:
        supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
            path,
            content,
            {"content-type": content_type, "upsert": "true"},
        )
    except Exception as e:
        print(f"[upload_file] failed: {e}")
        return path
    return path


def download_file(path: str) -> bytes:
    if not is_supabase_configured():
        return b""
    try:
        return supabase.storage.from_(settings.SUPABASE_BUCKET).download(path)
    except Exception as e:
        print(f"[download_file] failed: {e}")
        return b""


def get_signed_url(path: str, expires_in: int = 3600) -> str:
    if not is_supabase_configured():
        return ""
    try:
        res = supabase.storage.from_(settings.SUPABASE_BUCKET).create_signed_url(
            path, expires_in
        )
        return res.get("signedURL") or res.get("signedUrl") or ""
    except Exception as e:
        print(f"[get_signed_url] failed: {e}")
        return ""


def delete_file(path: str) -> None:
    if not is_supabase_configured():
        return
    try:
        supabase.storage.from_(settings.SUPABASE_BUCKET).remove([path])
    except Exception as e:
        print(f"[delete_file] failed: {e}")
        return


# ---------------------------------------------------------------------------
# Database — files
# ---------------------------------------------------------------------------

def save_file_record(
    user_id: str, name: str, file_type: str, size: int, storage_path: str
) -> dict:
    default = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": name,
        "type": file_type,
        "size": size,
        "storage_path": storage_path,
        "status": "ready",
    }
    if not is_supabase_configured():
        return default
    try:
        res = (
            supabase.table("files")
            .insert(
                {
                    "user_id": user_id,
                    "name": name,
                    "type": file_type,
                    "size": size,
                    "storage_path": storage_path,
                    "status": "ready",
                }
            )
            .execute()
        )
    except Exception as e:
        print(f"[save_file_record] failed: {e}")
        return default
    return res.data[0] if res.data else default


def list_user_files(user_id: str) -> list:
    if not is_supabase_configured():
        return []
    try:
        res = (
            supabase.table("files")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as e:
        print(f"[list_user_files] failed: {e}")
        return []
    return res.data or []


def get_file_record(file_id: str, user_id: str) -> dict | None:
    if not is_supabase_configured():
        return None
    try:
        res = (
            supabase.table("files")
            .select("*")
            .eq("id", file_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
    except Exception as e:
        print(f"[get_file_record] failed: {e}")
        return None
    return res.data


def delete_file_record(file_id: str, user_id: str) -> None:
    if not is_supabase_configured():
        return
    try:
        supabase.table("files").delete().eq("id", file_id).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"[delete_file_record] failed: {e}")
        return


# ---------------------------------------------------------------------------
# Database — jobs
# ---------------------------------------------------------------------------

def log_job(
    user_id: str,
    file_id: str | None,
    job_type: str,
    status: str = "done",
    error: str | None = None,
):
    if not is_supabase_configured():
        return
    try:
        supabase.table("jobs").insert(
            {
                "user_id": user_id,
                "file_id": file_id,
                "job_type": job_type,
                "status": status,
                "error": error,
            }
        ).execute()
    except Exception as e:
        print(f"[log_job] failed: {e}")
        return

def get_profile(user_id: str) -> dict | None:
    """Fetch user's profile row."""
    if not is_supabase_configured():
        return None
    try:
        res = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return res.data
    except Exception as e:
        print(f"[get_profile] failed: {e}")
        return None


def update_profile(user_id: str, updates: dict) -> dict | None:
    """Update profile fields (whitelist)."""
    if not is_supabase_configured():
        return None

    allowed = {"full_name", "phone", "bio", "location", "language"}
    safe_updates = {k: v for k, v in updates.items() if k in allowed}

    if not safe_updates:
        return None

    try:
        res = (
            supabase.table("profiles")
            .update(safe_updates)
            .eq("id", user_id)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[update_profile] failed: {e}")
        return None


def get_profile_stats(user_id: str) -> dict:
    """Compute user's usage stats."""
    if not is_supabase_configured():
        return {"files_count": 0, "storage_used": 0, "jobs_count": 0}

    try:
        files = (
            supabase.table("files")
            .select("size", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        files_count = files.count or 0
        storage_used = sum((f.get("size") or 0) for f in (files.data or []))

        jobs = (
            supabase.table("jobs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        jobs_count = jobs.count or 0

        return {
            "files_count": files_count,
            "storage_used": storage_used,
            "jobs_count": jobs_count,
        }
    except Exception as e:
        print(f"[get_profile_stats] failed: {e}")
        return {"files_count": 0, "storage_used": 0, "jobs_count": 0}

def get_settings(user_id: str) -> dict | None:
    """Fetch user's settings row, or None if doesn't exist."""
    if not is_supabase_configured():
        return None
    try:
        res = (
            supabase.table("user_settings")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None


def upsert_settings(user_id: str, updates: dict) -> dict | None:
    """Insert or update user settings."""
    if not is_supabase_configured():
        return None

    allowed = {
        "theme",
        "notifications_email",
        "notifications_marketing",
        "default_output_format",
        "auto_delete_days",
        "analytics_opt_in",
    }
    safe = {k: v for k, v in updates.items() if k in allowed}

    # Ensure row exists
    existing = get_settings(user_id)

    try:
        if not existing:
            # Insert with defaults + overrides
            res = (
                supabase.table("user_settings")
                .insert({"user_id": user_id, **safe})
                .execute()
            )
        else:
            res = (
                supabase.table("user_settings")
                .update({**safe, "updated_at": "now()"})
                .eq("user_id", user_id)
                .execute()
            )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[upsert_settings] failed: {e}")
        return None


def delete_all_user_files(user_id: str) -> int:
    """Delete all files (storage + records) for a user. Returns count."""
    if not is_supabase_configured():
        return 0
    try:
        files = (
            supabase.table("files").select("id, storage_path").eq("user_id", user_id).execute()
        )
        paths = [f["storage_path"] for f in (files.data or []) if f.get("storage_path")]
        if paths:
            supabase.storage.from_(settings.SUPABASE_BUCKET).remove(paths)
        supabase.table("files").delete().eq("user_id", user_id).execute()
        return len(paths)
    except Exception as e:
        print(f"[delete_all_user_files] failed: {e}")
        return 0