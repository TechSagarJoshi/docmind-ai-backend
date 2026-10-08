from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import Response
from app.deps import get_current_user
from app.services.pdf_service import (
    merge_pdfs,
    split_pdf,
    compress_pdf,
    rotate_pdf,
    extract_pages,
    delete_pages,
    add_page_numbers,
    add_text_watermark,
)
from app.services import supabase_service as sb

router = APIRouter(prefix="/api/pdf", tags=["pdf"])


def _pdf_response(data: bytes, filename: str) -> Response:
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/merge")
async def merge(
    files: list[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    if len(files) < 2:
        raise HTTPException(400, "Upload at least 2 PDF files")
    contents = [await f.read() for f in files]
    try:
        result = merge_pdfs(contents)
        sb.log_job(user["id"], None, "merge_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "merge_pdf", "failed", str(e))
        raise HTTPException(500, f"Merge failed: {e}")
    return _pdf_response(result, "merged.pdf")


@router.post("/split")
async def split(
    file: UploadFile = File(...),
    pages: str = Form(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = split_pdf(content, pages)
        sb.log_job(user["id"], None, "split_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "split_pdf", "failed", str(e))
        raise HTTPException(400, f"Split failed: {e}")
    return _pdf_response(result, "split.pdf")


@router.post("/compress")
async def compress(
    file: UploadFile = File(...),
    quality: str = Form("medium"),
    user=Depends(get_current_user),
):
    if quality not in ("low", "medium", "high"):
        raise HTTPException(400, "quality must be low/medium/high")
    content = await file.read()
    try:
        result = compress_pdf(content, quality)
        sb.log_job(user["id"], None, "compress_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "compress_pdf", "failed", str(e))
        raise HTTPException(500, f"Compress failed: {e}")
    return _pdf_response(result, "compressed.pdf")


@router.post("/rotate")
async def rotate(
    file: UploadFile = File(...),
    angle: int = Form(...),
    user=Depends(get_current_user),
):
    if angle not in (90, 180, 270):
        raise HTTPException(400, "angle must be 90, 180, or 270")
    content = await file.read()
    try:
        result = rotate_pdf(content, angle)
        sb.log_job(user["id"], None, "rotate_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "rotate_pdf", "failed", str(e))
        raise HTTPException(500, f"Rotate failed: {e}")
    return _pdf_response(result, "rotated.pdf")


@router.post("/extract-pages")
async def extract(
    file: UploadFile = File(...),
    pages: str = Form(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = extract_pages(content, pages)
        sb.log_job(user["id"], None, "extract_pages", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "extract_pages", "failed", str(e))
        raise HTTPException(400, f"Extract failed: {e}")
    return _pdf_response(result, "extracted.pdf")


@router.post("/delete-pages")
async def delete(
    file: UploadFile = File(...),
    pages: str = Form(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = delete_pages(content, pages)
        sb.log_job(user["id"], None, "delete_pages", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "delete_pages", "failed", str(e))
        raise HTTPException(400, f"Delete failed: {e}")
    return _pdf_response(result, "pages_deleted.pdf")


@router.post("/page-numbers")
async def page_numbers(
    file: UploadFile = File(...),
    position: str = Form("bottom-center"),
    start_number: int = Form(1),
    font_size: int = Form(11),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = add_page_numbers(content, position, start_number, font_size)
        sb.log_job(user["id"], None, "page_numbers", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "page_numbers", "failed", str(e))
        raise HTTPException(500, f"Page numbers failed: {e}")
    return _pdf_response(result, "numbered.pdf")


@router.post("/watermark")
async def watermark(
    file: UploadFile = File(...),
    text: str = Form(...),
    opacity: float = Form(0.3),
    font_size: int = Form(50),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = add_text_watermark(content, text, opacity, font_size)
        sb.log_job(user["id"], None, "watermark", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "watermark", "failed", str(e))
        raise HTTPException(400, f"Watermark failed: {e}")
    return _pdf_response(result, "watermarked.pdf")