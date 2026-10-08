from PIL import Image
from io import BytesIO


# Allowed output formats and their Pillow names
ALLOWED_FORMATS = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "tiff": "TIFF",
}


def convert_image(
    content: bytes,
    output_format: str,
    quality: int = 90,
) -> tuple[bytes, str]:
    """
    Convert image bytes to another format.

    Returns (output_bytes, mime_type).
    """
    fmt_key = output_format.lower().strip().lstrip(".")
    if fmt_key not in ALLOWED_FORMATS:
        raise ValueError(
            f"Unsupported output format: {output_format}. "
            f"Choose from {sorted(ALLOWED_FORMATS.keys())}"
        )

    pillow_format = ALLOWED_FORMATS[fmt_key]

    try:
        img = Image.open(BytesIO(content))
    except Exception as e:
        raise ValueError(f"Could not read image: {e}")

    # Prepare image for JPEG (no alpha, use white background)
    if pillow_format == "JPEG":
        if img.mode in ("RGBA", "LA", "P"):
            # Create white background
            bg = Image.new("RGB", img.size, (255, 255, 255))
            img_rgba = img.convert("RGBA")
            bg.paste(img_rgba, mask=img_rgba.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

    out = BytesIO()

    save_kwargs = {}
    if pillow_format in ("JPEG", "WEBP"):
        save_kwargs["quality"] = max(1, min(100, quality))
    if pillow_format == "PNG":
        save_kwargs["optimize"] = True
    if pillow_format == "WEBP":
        save_kwargs["method"] = 4

    try:
        img.save(out, format=pillow_format, **save_kwargs)
    except Exception as e:
        raise ValueError(f"Could not save as {pillow_format}: {e}")

    mime_map = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "BMP": "image/bmp",
        "TIFF": "image/tiff",
    }

    return out.getvalue(), mime_map[pillow_format]


def extension_for(format_key: str) -> str:
    """Map user-facing format to file extension."""
    fmt = format_key.lower().strip().lstrip(".")
    if fmt == "jpeg":
        return "jpg"
    return fmt


def compress_image(
    content: bytes,
    quality: int = 75,
    target_kb: int | None = None,
    output_format: str = "jpg",
) -> tuple[bytes, str, int]:
    """
    Compress an image.

    If target_kb is provided, iteratively reduce quality until size <= target_kb.
    Otherwise, use the fixed `quality`.

    Returns (output_bytes, mime_type, final_quality).
    """
    fmt_key = output_format.lower().strip().lstrip(".")
    if fmt_key not in ALLOWED_FORMATS:
        raise ValueError(f"Unsupported format: {output_format}")

    pillow_format = ALLOWED_FORMATS[fmt_key]

    try:
        img = Image.open(BytesIO(content))
    except Exception as e:
        raise ValueError(f"Could not read image: {e}")

    # JPEG needs RGB; WEBP/PNG can keep alpha
    if pillow_format == "JPEG":
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            img_rgba = img.convert("RGBA")
            bg.paste(img_rgba, mask=img_rgba.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
    elif pillow_format == "WEBP" and img.mode == "P":
        img = img.convert("RGBA")

    def _encode(q: int) -> bytes:
        buf = BytesIO()
        kwargs = {}
        if pillow_format in ("JPEG", "WEBP"):
            kwargs["quality"] = max(1, min(100, q))
        if pillow_format == "WEBP":
            kwargs["method"] = 4
        if pillow_format == "PNG":
            kwargs["optimize"] = True
        img.save(buf, format=pillow_format, **kwargs)
        return buf.getvalue()

    mime_map = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "BMP": "image/bmp",
        "TIFF": "image/tiff",
    }

    # Target size mode: binary search quality
    if target_kb is not None and target_kb > 0:
        target_bytes = target_kb * 1024
        best = None
        best_q = quality

        lo, hi = 10, 100
        for _ in range(7):
            mid = (lo + hi) // 2
            data = _encode(mid)
            if len(data) <= target_bytes:
                best = data
                best_q = mid
                lo = mid + 1
            else:
                hi = mid - 1

        if best is None:
            # Even at low quality it's too big — return lowest
            data = _encode(10)
            return data, mime_map[pillow_format], 10

        return best, mime_map[pillow_format], best_q

    # Fixed quality mode
    data = _encode(quality)
    return data, mime_map[pillow_format], quality