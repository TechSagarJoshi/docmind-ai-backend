from pypdf import PdfWriter, PdfReader
from pypdf.generic import RectangleObject
import pikepdf
from pdf2image import convert_from_bytes
from PIL import Image
from io import BytesIO


def merge_pdfs(files: list[bytes]) -> bytes:
    writer = PdfWriter()
    for content in files:
        writer.append(PdfReader(BytesIO(content)))
    out = BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()


def split_pdf(content: bytes, pages: str) -> bytes:
    reader = PdfReader(BytesIO(content))
    total = len(reader.pages)
    writer = PdfWriter()
    for part in pages.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = map(int, part.split("-"))
            if start < 1 or end > total or start > end:
                raise ValueError(f"Invalid range {part} (total pages: {total})")
            for i in range(start - 1, end):
                writer.add_page(reader.pages[i])
        else:
            idx = int(part)
            if idx < 1 or idx > total:
                raise ValueError(f"Invalid page {idx} (total pages: {total})")
            writer.add_page(reader.pages[idx - 1])
    if len(writer.pages) == 0:
        raise ValueError("No pages selected")
    out = BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()


def compress_pdf(content: bytes, quality: str = "medium") -> bytes:
    pdf = pikepdf.open(BytesIO(content))
    out = BytesIO()
    save_kwargs = {
        "compress_streams": True,
        "object_stream_mode": pikepdf.ObjectStreamMode.generate,
    }
    if quality in ("medium", "high"):
        save_kwargs["recompress_flate"] = True
    if quality == "high":
        save_kwargs["linearize"] = True
    pdf.save(out, **save_kwargs)
    pdf.close()
    return out.getvalue()


def pdf_to_images(content: bytes, fmt: str = "jpeg") -> list[tuple[str, bytes]]:
    from app.config import settings
    import os
    poppler_path = None
    if settings.POPPLER_PATH and os.path.isdir(settings.POPPLER_PATH):
        poppler_path = settings.POPPLER_PATH
    images = convert_from_bytes(content, dpi=150, poppler_path=poppler_path)
    out = []
    for i, img in enumerate(images, start=1):
        buf = BytesIO()
        if fmt.lower() == "png":
            img.save(buf, format="PNG")
            out.append((f"page_{i}.png", buf.getvalue()))
        else:
            img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=85)
            out.append((f"page_{i}.jpg", buf.getvalue()))
    return out


def images_to_pdf(files: list[bytes]) -> bytes:
    images = []
    for content in files:
        img = Image.open(BytesIO(content))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        images.append(img)
    if not images:
        raise ValueError("No images provided")
    out = BytesIO()
    images[0].save(
        out,
        format="PDF",
        save_all=True,
        append_images=images[1:],
    )
    return out.getvalue()


# ============================================================
# NEW: Advanced PDF tools
# ============================================================


def rotate_pdf(content: bytes, angle: int) -> bytes:
    """Rotate all pages by angle (must be 90, 180, or 270)."""
    if angle not in (90, 180, 270):
        raise ValueError("angle must be 90, 180, or 270")

    reader = PdfReader(BytesIO(content))
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()


def extract_pages(content: bytes, pages: str) -> bytes:
    """Extract specific pages into a new PDF. Same syntax as split."""
    return split_pdf(content, pages)


def delete_pages(content: bytes, pages: str) -> bytes:
    """Delete specific pages from a PDF. pages syntax like '1,3,5-7'."""
    reader = PdfReader(BytesIO(content))
    total = len(reader.pages)

    # Figure out which page indices (0-based) to keep
    to_delete = set()
    for part in pages.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = map(int, part.split("-"))
            if start < 1 or end > total or start > end:
                raise ValueError(f"Invalid range {part} (total pages: {total})")
            for i in range(start - 1, end):
                to_delete.add(i)
        else:
            idx = int(part)
            if idx < 1 or idx > total:
                raise ValueError(f"Invalid page {idx} (total pages: {total})")
            to_delete.add(idx - 1)

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i not in to_delete:
            writer.add_page(page)

    if len(writer.pages) == 0:
        raise ValueError("Cannot delete all pages — keep at least one")

    out = BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()


def add_page_numbers(
    content: bytes,
    position: str = "bottom-center",
    start_number: int = 1,
    font_size: int = 11,
) -> bytes:
    """Add page numbers to a PDF."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    reader = PdfReader(BytesIO(content))
    writer = PdfWriter()

    total = len(reader.pages)
    for idx, page in enumerate(reader.pages):
        # Get page dimensions (in points)
        try:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
        except Exception:
            width, height = 612, 792  # letter default

        # Generate overlay PDF with the page number
        overlay_buf = BytesIO()
        c = canvas.Canvas(overlay_buf, pagesize=(width, height))
        c.setFont("Helvetica", font_size)

        page_num = idx + start_number
        text = f"{page_num} / {total + start_number - 1}"

        margin = 30
        if position == "bottom-left":
            x, y = margin, margin
            c.drawString(x, y, text)
        elif position == "bottom-right":
            x, y = width - margin - 40, margin
            c.drawString(x, y, text)
        elif position == "bottom-center":
            x, y = width / 2 - 15, margin
            c.drawString(x, y, text)
        elif position == "top-center":
            x, y = width / 2 - 15, height - margin
            c.drawString(x, y, text)
        else:
            x, y = width / 2 - 15, margin
            c.drawString(x, y, text)
        c.save()
        overlay_buf.seek(0)

        overlay_page = PdfReader(overlay_buf).pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()


def add_text_watermark(
    content: bytes,
    text: str,
    opacity: float = 0.3,
    font_size: int = 50,
) -> bytes:
    """Add a diagonal text watermark to every page."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color

    if not text.strip():
        raise ValueError("Watermark text is required")

    reader = PdfReader(BytesIO(content))
    writer = PdfWriter()

    for page in reader.pages:
        try:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
        except Exception:
            width, height = 612, 792

        overlay_buf = BytesIO()
        c = canvas.Canvas(overlay_buf, pagesize=(width, height))
        c.saveState()
        c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
        c.setFont("Helvetica-Bold", font_size)
        c.translate(width / 2, height / 2)
        c.rotate(45)
        c.drawCentredString(0, 0, text)
        c.restoreState()
        c.save()
        overlay_buf.seek(0)

        overlay_page = PdfReader(overlay_buf).pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()
def pdf_to_text(content: bytes) -> str:
    """Extract plain text from a PDF."""
    import fitz
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open PDF: {e}")

    pages = []
    for i in range(doc.page_count):
        pages.append(doc.load_page(i).get_text("text", sort=True))
    doc.close()

    if not any(p.strip() for p in pages):
        raise ValueError("No text found. This PDF may be a scanned image — try OCR PDF.")

    return "\n\n".join(f"--- Page {i+1} ---\n{p}" for i, p in enumerate(pages))


def text_to_pdf(content: bytes, title: str = "Document") -> bytes:
    """Convert plain text bytes to a PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT

    # Decode text
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=title,
    )

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    story = []
    for line in text.split("\n"):
        line = line.rstrip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        # Escape XML special chars for reportlab
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        try:
            story.append(Paragraph(line, body_style))
        except Exception:
            story.append(Paragraph("(malformed line skipped)", body_style))

    if not story:
        story.append(Paragraph("(empty document)", body_style))

    doc.build(story)
    return buf.getvalue()


def ocr_pdf(content: bytes, language: str = "eng") -> str:
    """OCR a scanned PDF using Tesseract + Poppler."""
    from app.config import settings
    import os
    import pytesseract
    from pdf2image import convert_from_bytes

    # Configure Tesseract path
    if settings.TESSERACT_PATH and os.path.isfile(settings.TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

    # Check tesseract is reachable
    try:
        pytesseract.get_tesseract_version()
    except Exception as e:
        raise RuntimeError(
            f"Tesseract not found. Set TESSERACT_PATH in .env. Error: {e}"
        )

    poppler_path = None
    if settings.POPPLER_PATH and os.path.isdir(settings.POPPLER_PATH):
        poppler_path = settings.POPPLER_PATH

    # Render pages to images (200 DPI for OCR quality)
    images = convert_from_bytes(content, dpi=200, poppler_path=poppler_path)

    out = []
    for i, img in enumerate(images, start=1):
        try:
            text = pytesseract.image_to_string(img, lang=language)
            out.append(f"--- Page {i} ---\n{text}")
        except Exception as e:
            out.append(f"--- Page {i} (error: {e}) ---")

    result = "\n\n".join(out).strip()
    if not result:
        raise ValueError("OCR produced no text. Check that the PDF contains readable text.")

    return result