import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from io import BytesIO
from pdf2docx import Converter
from app.config import settings


def _check_soffice() -> str:
    """Return the soffice path or raise if missing."""
    path = settings.SOFFICE_PATH
    if not path or not os.path.isfile(path):
        raise RuntimeError(
            f"LibreOffice not found at {path!r}. "
            f"Set SOFFICE_PATH in .env to the full path of soffice.exe"
        )
    return path


def pdf_to_word(content: bytes) -> bytes:
    """Convert PDF bytes to DOCX bytes using pdf2docx."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf.write(content)
        pdf_path = tmp_pdf.name
    docx_path = pdf_path.replace(".pdf", ".docx")

    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path)
        cv.close()
        with open(docx_path, "rb") as f:
            return f.read()
    finally:
        for p in (pdf_path, docx_path):
            try:
                os.unlink(p)
            except OSError:
                pass


def _soffice_convert(content: bytes, input_ext: str, output_ext: str) -> bytes:
    """Generic converter using LibreOffice headless."""
    soffice = _check_soffice()

    # LibreOffice writes output in the same folder as input
    tmpdir = tempfile.mkdtemp(prefix="docmind_")
    try:
        in_path = os.path.join(tmpdir, f"input{input_ext}")
        with open(in_path, "wb") as f:
            f.write(content)

        # soffice --headless --convert-to <ext> --outdir <tmpdir> <input>
        cmd = [
            soffice,
            "--headless",
            "--norestore",
            "--convert-to",
            output_ext.lstrip("."),
            "--outdir",
            tmpdir,
            in_path,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # LibreOffice names output as <basename>.<ext>
        expected = os.path.join(tmpdir, f"input{output_ext}")
        if not os.path.isfile(expected):
            raise RuntimeError(
                f"LibreOffice conversion failed. "
                f"stdout: {result.stdout!r} stderr: {result.stderr!r}"
            )

        with open(expected, "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def word_to_pdf(content: bytes) -> bytes:
    return _soffice_convert(content, ".docx", ".pdf")


def excel_to_pdf(content: bytes) -> bytes:
    # Accept .xlsx; if user uploads .xls, we can still pass .xls
    return _soffice_convert(content, ".xlsx", ".pdf")


def ppt_to_pdf(content: bytes) -> bytes:
    return _soffice_convert(content, ".pptx", ".pdf")