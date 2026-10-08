from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.deps import get_current_user
from app.services import supabase_service as sb

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    try:
        storage_path = sb.upload_file(
            user_id=user["id"],
            filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
        record = sb.save_file_record(
            user_id=user["id"],
            name=file.filename,
            file_type=file.content_type or "unknown",
            size=len(content),
            storage_path=storage_path,
        )
        return {"file": record}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {e}")


@router.get("")
async def list_files(user=Depends(get_current_user)):
    return {"files": sb.list_user_files(user["id"])}


@router.get("/{file_id}/download")
async def download(file_id: str, user=Depends(get_current_user)):
    record = sb.get_file_record(file_id, user["id"])
    if not record:
        raise HTTPException(404, "File not found")
    url = sb.get_signed_url(record["storage_path"], expires_in=3600)
    return {"url": url, "name": record["name"]}


@router.delete("/{file_id}")
async def delete(file_id: str, user=Depends(get_current_user)):
    record = sb.get_file_record(file_id, user["id"])
    if not record:
        raise HTTPException(404, "File not found")
    try:
        sb.delete_file(record["storage_path"])
        sb.delete_file_record(file_id, user["id"])
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {e}")