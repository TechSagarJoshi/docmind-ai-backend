import io
import zipfile
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import Response
from app.deps import get_current_user
from app.services.pdf_service import pdf_to_images, images_to_pdf
from app.services.image_service import convert_image, extension_for, compress_image
from app.services.excel_service import (
    excel_to_csv,
    csv_to_excel,
    merge_excel,
    merge_csv,
)
from app.services.pdf_service import (
    pdf_to_images,
    images_to_pdf,
    pdf_to_text,
    text_to_pdf,
    ocr_pdf,
)
from app.services.excel_service import (
    excel_to_csv,
    csv_to_excel,
    merge_excel,
    merge_csv,
    split_excel,
    remove_duplicates,
    remove_empty_rows,
)
from app.services.extraction_service import (
    extract_emails,
    extract_phones,
    extract_urls,
    extract_amounts,
    extract_gstin,
    extract_dates,
    extract_pincodes,
    extract_pan,
    extract_all,
    extraction_to_csv,
)
from app.services.office_service import (
    pdf_to_word,
    word_to_pdf,
    excel_to_pdf,
    ppt_to_pdf,
)
from app.services import supabase_service as sb

router = APIRouter(prefix="/api/convert", tags=["convert"])


# ---------- PDF <-> Images ----------

@router.post("/pdf-to-images")
async def pdf_to_images_endpoint(
    file: UploadFile = File(...),
    fmt: str = Form("jpeg"),
    user=Depends(get_current_user),
):
    if fmt not in ("jpeg", "png"):
        raise HTTPException(400, "fmt must be jpeg or png")
    content = await file.read()
    try:
        pages = pdf_to_images(content, fmt=fmt)
        sb.log_job(user["id"], None, "pdf_to_images", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "pdf_to_images", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in pages:
            zf.writestr(name, data)
    return Response(
        zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=pdf_images.zip"},
    )


@router.post("/images-to-pdf")
async def images_to_pdf_endpoint(
    files: list[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    if not files:
        raise HTTPException(400, "Upload at least 1 image")
    contents = [await f.read() for f in files]
    try:
        result = images_to_pdf(contents)
        sb.log_job(user["id"], None, "images_to_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "images_to_pdf", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")
    return Response(
        result,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=images.pdf"},
    )


# ---------- Excel <-> CSV ----------

@router.post("/excel-to-csv")
async def excel_to_csv_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = excel_to_csv(content)
        sb.log_job(user["id"], None, "excel_to_csv", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "excel_to_csv", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")
    return Response(
        result,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=converted.csv"},
    )


@router.post("/csv-to-excel")
async def csv_to_excel_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = csv_to_excel(content)
        sb.log_job(user["id"], None, "csv_to_excel", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "csv_to_excel", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")
    return Response(
        result,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=converted.xlsx"},
    )


# ---------- Merges ----------

@router.post("/merge-excel")
async def merge_excel_endpoint(
    files: list[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    if len(files) < 2:
        raise HTTPException(400, "Upload at least 2 Excel files")
    contents = [await f.read() for f in files]
    try:
        result = merge_excel(contents)
        sb.log_job(user["id"], None, "merge_excel", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "merge_excel", "failed", str(e))
        raise HTTPException(500, f"Merge failed: {e}")
    return Response(
        result,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=merged.xlsx"},
    )


@router.post("/merge-csv")
async def merge_csv_endpoint(
    files: list[UploadFile] = File(...),
    user=Depends(get_current_user),
):
    if len(files) < 2:
        raise HTTPException(400, "Upload at least 2 CSV files")
    contents = [await f.read() for f in files]
    try:
        result = merge_csv(contents)
        sb.log_job(user["id"], None, "merge_csv", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "merge_csv", "failed", str(e))
        raise HTTPException(500, f"Merge failed: {e}")
    return Response(
        result,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=merged.csv"},
    )


# ---------- Office conversions ----------

@router.post("/pdf-to-word")
async def pdf_to_word_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = pdf_to_word(content)
        sb.log_job(user["id"], None, "pdf_to_word", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "pdf_to_word", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")
    return Response(
        result,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=converted.docx"},
    )


@router.post("/word-to-pdf")
async def word_to_pdf_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = word_to_pdf(content)
        sb.log_job(user["id"], None, "word_to_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "word_to_pdf", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")
    return Response(
        result,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=converted.pdf"},
    )


@router.post("/excel-to-pdf")
async def excel_to_pdf_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = excel_to_pdf(content)
        sb.log_job(user["id"], None, "excel_to_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "excel_to_pdf", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")
    return Response(
        result,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=converted.pdf"},
    )


@router.post("/ppt-to-pdf")
async def ppt_to_pdf_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = ppt_to_pdf(content)
        sb.log_job(user["id"], None, "ppt_to_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "ppt_to_pdf", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")
    return Response(
        result,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=converted.pdf"},
    )


# ---------- Image conversion ----------

@router.post("/image-convert")
async def image_convert_endpoint(
    file: UploadFile = File(...),
    output_format: str = Form("png"),
    quality: int = Form(90),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result_bytes, mime = convert_image(
            content,
            output_format=output_format,
            quality=quality,
        )
        sb.log_job(user["id"], None, "image_convert", "done")
    except ValueError as e:
        sb.log_job(user["id"], None, "image_convert", "failed", str(e))
        raise HTTPException(400, str(e))
    except Exception as e:
        sb.log_job(user["id"], None, "image_convert", "failed", str(e))
        raise HTTPException(500, f"Conversion failed: {e}")

    ext = extension_for(output_format)
    return Response(
        result_bytes,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename=converted.{ext}"},
    )


# ---------- Image compression ----------

@router.post("/image-compress")
async def image_compress_endpoint(
    file: UploadFile = File(...),
    quality: int = Form(75),
    target_kb: int = Form(0),
    output_format: str = Form("jpg"),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result_bytes, mime, final_q = compress_image(
            content,
            quality=quality,
            target_kb=target_kb if target_kb > 0 else None,
            output_format=output_format,
        )
        sb.log_job(user["id"], None, "image_compress", "done")
    except ValueError as e:
        sb.log_job(user["id"], None, "image_compress", "failed", str(e))
        raise HTTPException(400, str(e))
    except Exception as e:
        sb.log_job(user["id"], None, "image_compress", "failed", str(e))
        raise HTTPException(500, f"Compression failed: {e}")

    ext = extension_for(output_format)
    return Response(
        result_bytes,
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename=compressed.{ext}",
            "X-Final-Quality": str(final_q),
            "X-Output-Size": str(len(result_bytes)),
        },
    )
# ---------- PDF data extraction ----------

import json


def _extract_response(items: list[str], label: str) -> Response:
    return Response(
        json.dumps({"type": label, "count": len(items), "items": items}),
        media_type="application/json",
    )


@router.post("/extract-emails")
async def extract_emails_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = extract_emails(content)
        sb.log_job(user["id"], None, "extract_emails", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "extract_emails", "failed", str(e))
        raise HTTPException(500, f"Extraction failed: {e}")
    return _extract_response(result, "emails")


@router.post("/extract-phones")
async def extract_phones_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = extract_phones(content)
        sb.log_job(user["id"], None, "extract_phones", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "extract_phones", "failed", str(e))
        raise HTTPException(500, f"Extraction failed: {e}")
    return _extract_response(result, "phones")


@router.post("/extract-urls")
async def extract_urls_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = extract_urls(content)
        sb.log_job(user["id"], None, "extract_urls", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "extract_urls", "failed", str(e))
        raise HTTPException(500, f"Extraction failed: {e}")
    return _extract_response(result, "urls")


@router.post("/extract-amounts")
async def extract_amounts_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = extract_amounts(content)
        sb.log_job(user["id"], None, "extract_amounts", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "extract_amounts", "failed", str(e))
        raise HTTPException(500, f"Extraction failed: {e}")
    return _extract_response(result, "amounts")


@router.post("/extract-gstin")
async def extract_gstin_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = extract_gstin(content)
        sb.log_job(user["id"], None, "extract_gstin", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "extract_gstin", "failed", str(e))
        raise HTTPException(500, f"Extraction failed: {e}")
    return _extract_response(result, "gstins")


@router.post("/extract-dates")
async def extract_dates_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = extract_dates(content)
        sb.log_job(user["id"], None, "extract_dates", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "extract_dates", "failed", str(e))
        raise HTTPException(500, f"Extraction failed: {e}")
    return _extract_response(result, "dates")


@router.post("/extract-all")
async def extract_all_endpoint(
    file: UploadFile = File(...),
    output: str = Form("json"),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = extract_all(content)
        sb.log_job(user["id"], None, "extract_all", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "extract_all", "failed", str(e))
        raise HTTPException(500, f"Extraction failed: {e}")

    if output == "csv":
        csv_bytes = extraction_to_csv(result)
        return Response(
            csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=extracted.csv"},
        )
    return Response(json.dumps(result), media_type="application/json")
# ---------- PDF → Text ----------

@router.post("/pdf-to-text")
async def pdf_to_text_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = pdf_to_text(content)
        sb.log_job(user["id"], None, "pdf_to_text", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "pdf_to_text", "failed", str(e))
        raise HTTPException(400, f"PDF to text failed: {e}")
    return Response(
        result.encode("utf-8"),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=extracted.txt"},
    )


# ---------- Text → PDF ----------

@router.post("/text-to-pdf")
async def text_to_pdf_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    title = file.filename.rsplit(".", 1)[0] if file.filename else "Document"
    try:
        result = text_to_pdf(content, title=title)
        sb.log_job(user["id"], None, "text_to_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "text_to_pdf", "failed", str(e))
        raise HTTPException(500, f"Text to PDF failed: {e}")
    return Response(
        result,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=converted.pdf"},
    )


# ---------- OCR PDF ----------

@router.post("/ocr-pdf")
async def ocr_pdf_endpoint(
    file: UploadFile = File(...),
    language: str = Form("eng"),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = ocr_pdf(content, language=language)
        sb.log_job(user["id"], None, "ocr_pdf", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "ocr_pdf", "failed", str(e))
        raise HTTPException(500, f"OCR failed: {e}")
    return Response(
        result.encode("utf-8"),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=ocr.txt"},
    )


# ---------- Excel → Split ----------

@router.post("/split-excel")
async def split_excel_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        sheets = split_excel(content)
        sb.log_job(user["id"], None, "split_excel", "done")
    except Exception as e:
        sb.log_job(user["id"], None, "split_excel", "failed", str(e))
        raise HTTPException(500, f"Split failed: {e}")

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in sheets:
            zf.writestr(name, data)
    return Response(
        zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=sheets.zip"},
    )


# ---------- Remove Duplicates ----------

@router.post("/remove-duplicates")
async def remove_duplicates_endpoint(
    file: UploadFile = File(...),
    column: str = Form(""),
    user=Depends(get_current_user),
):
    content = await file.read()
    col = column.strip() if column.strip() else None
    try:
        result = remove_duplicates(content, column=col)
        sb.log_job(user["id"], None, "remove_duplicates", "done")
    except ValueError as e:
        sb.log_job(user["id"], None, "remove_duplicates", "failed", str(e))
        raise HTTPException(400, str(e))
    except Exception as e:
        sb.log_job(user["id"], None, "remove_duplicates", "failed", str(e))
        raise HTTPException(500, f"Remove duplicates failed: {e}")

    # Return same format as input
    fn = file.filename or "file"
    if fn.lower().endswith(".xlsx") or fn.lower().endswith(".xls"):
        return Response(
            result,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=deduped.xlsx"},
        )
    return Response(
        result,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=deduped.csv"},
    )


# ---------- Remove Empty Rows ----------

@router.post("/remove-empty-rows")
async def remove_empty_rows_endpoint(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    content = await file.read()
    try:
        result = remove_empty_rows(content)
        sb.log_job(user["id"], None, "remove_empty_rows", "done")
    except ValueError as e:
        sb.log_job(user["id"], None, "remove_empty_rows", "failed", str(e))
        raise HTTPException(400, str(e))
    except Exception as e:
        sb.log_job(user["id"], None, "remove_empty_rows", "failed", str(e))
        raise HTTPException(500, f"Remove empty rows failed: {e}")

    fn = file.filename or "file"
    if fn.lower().endswith(".xlsx") or fn.lower().endswith(".xls"):
        return Response(
            result,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=cleaned.xlsx"},
        )
    return Response(
        result,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cleaned.csv"},
    )