import re
from io import BytesIO
import fitz  # PyMuPDF


# ============================================================
# IMPROVED Regex patterns with normalization
# ============================================================

# Emails — strip trailing punctuation handled after match
EMAIL_RE = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
    re.IGNORECASE,
)

# Indian phones — must start with 6-9, exactly 10 digits
# Handles: 9876543210, +91 9876543210, +91-9876-543210, (91) 9876543210
PHONE_INDIAN_RE = re.compile(
    r"(?:(?:\+|00)\s?91[\s\-.]?)?"    # optional +91 prefix
    r"(?:\(?\d{3,5}\)?[\s\-.]?)?"      # optional STD-like prefix (rare in mobile)
    r"[6-9]\d{9}\b"                    # 10 digits starting 6-9
)

# International phones — country code + 8-15 digits
PHONE_INTL_RE = re.compile(
    r"\+\d{1,3}[\s\-.]?(?:\(\d{1,4}\)[\s\-.]?)?\d{6,14}\b"
)

# URLs
URL_RE = re.compile(
    r"\b(?:https?://|www\.)[^\s<>\"')\],]+",
    re.IGNORECASE,
)

# Currency amounts
AMOUNT_RE = re.compile(
    r"(?:₹|Rs\.?|INR|USD|\$|€|£)\s?[\d,]+(?:\.\d{1,2})?",
    re.IGNORECASE,
)

# GSTIN — strict 15-char format
GSTIN_RE = re.compile(
    r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"
)

# PAN
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

# Dates
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"
    r"|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}"
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{2,4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4})\b",
    re.IGNORECASE,
)

# Indian PIN code (6 digits, first digit 1-9) — but only when preceded by
# a state name context OR standalone (reduces false positives)
PINCODE_RE = re.compile(r"\b[1-9]\d{5}\b")


# ============================================================
# Text extraction
# ============================================================

def extract_pdf_text(content: bytes) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open PDF: {e}")

    if doc.page_count == 0:
        raise ValueError("PDF has no pages")

    pages_text = []
    for page_num in range(doc.page_count):
        try:
            page = doc.load_page(page_num)
            # Use sort=True to get better reading order
            pages_text.append(page.get_text("text", sort=True))
        except Exception as e:
            pages_text.append(f"[page {page_num + 1} error: {e}]")

    doc.close()

    # Join pages with double newline to preserve separation
    raw = "\n\n".join(pages_text)

    # Normalize whitespace but preserve some structure
    # - Collapse 3+ newlines to 2
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    # - Collapse tabs/spaces runs but keep single spaces
    raw = re.sub(r"[ \t]{2,}", "  ", raw)

    return raw


def _normalize_text_for_matching(text: str) -> str:
    """Collapse newlines within lines — helps find split numbers."""
    # Replace "98765\n43210" with "98765 43210"
    # Only do this between digits
    normalized = re.sub(r"(\d)\s*\n\s*(\d)", r"\1\2", text)
    return normalized


# ============================================================
# Normalization helpers
# ============================================================

def _dedupe_ordered(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        item = item.strip()
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _normalize_email(email: str) -> str:
    """Strip trailing punctuation from emails."""
    return email.rstrip(".,;:!?)")


def _normalize_phone(raw: str) -> str:
    """Normalize a phone number to a canonical form.

    Returns:
      - '+91XXXXXXXXXX' if Indian
      - '+XXXXXXXXXXXXXXXX' for other international
      - 'XXXXXXXXXX' for plain 10-digit (assumed Indian)
    """
    digits = re.sub(r"\D", "", raw)

    if not digits:
        return raw

    # Indian: 10 digits (no country code)
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"

    # Indian: 12 digits starting with 91
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return f"+{digits}"

    # Indian: 11 digits starting with 0
    if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return f"+91{digits[1:]}"

    # International (11-15 digits)
    if 11 <= len(digits) <= 15:
        return f"+{digits}"

    return raw.strip()


def _dedupe_phones(phones: list[str]) -> list[str]:
    """Normalize then dedupe by digit sequence."""
    seen_digits = set()
    out = []
    for p in phones:
        norm = _normalize_phone(p)
        digits = re.sub(r"\D", "", norm)
        if len(digits) >= 10 and digits not in seen_digits:
            seen_digits.add(digits)
            out.append(norm)
    return out


def _normalize_amount(raw: str) -> str:
    """Normalize amount to a clean format like 'INR 500.00'."""
    # Extract currency symbol prefix and the number
    m = re.match(r"^(₹|Rs\.?|INR|USD|\$|€|£)\s*([\d,]+(?:\.\d{1,2})?)", raw.strip(), re.IGNORECASE)
    if not m:
        return raw.strip()

    symbol = m.group(1).upper().replace(".", "")
    symbol_map = {
        "₹": "INR",
        "RS": "INR",
        "INR": "INR",
        "$": "USD",
        "USD": "USD",
        "€": "EUR",
        "£": "GBP",
    }
    currency = symbol_map.get(symbol, symbol)

    number = m.group(2).replace(",", "")
    return f"{currency} {number}"


# ============================================================
# Extraction functions
# ============================================================

def extract_emails(content: bytes) -> list[str]:
    text = extract_pdf_text(content)
    raw = EMAIL_RE.findall(text)
    cleaned = [_normalize_email(e) for e in raw]
    # Filter out obviously invalid (double dots, trailing dot)
    cleaned = [e for e in cleaned if ".." not in e and not e.endswith(".")]
    return _dedupe_ordered(cleaned)


def extract_phones(content: bytes) -> list[str]:
    text = extract_pdf_text(content)
    # Fix page-break-split numbers
    text = _normalize_text_for_matching(text)

    matches = PHONE_INDIAN_RE.findall(text) + PHONE_INTL_RE.findall(text)
    return _dedupe_phones(matches)


def extract_urls(content: bytes) -> list[str]:
    text = extract_pdf_text(content)
    matches = URL_RE.findall(text)
    cleaned = [m.rstrip(".,;:!?)") for m in matches]
    return _dedupe_ordered(cleaned)


def extract_amounts(content: bytes) -> list[str]:
    text = extract_pdf_text(content)
    matches = AMOUNT_RE.findall(text)
    normalized = [_normalize_amount(m) for m in matches]
    return _dedupe_ordered(normalized)


def extract_gstin(content: bytes) -> list[str]:
    text = extract_pdf_text(content)
    return _dedupe_ordered(GSTIN_RE.findall(text))


def extract_dates(content: bytes) -> list[str]:
    text = extract_pdf_text(content)
    return _dedupe_ordered(DATE_RE.findall(text))


def extract_pincodes(content: bytes) -> list[str]:
    """Extract PIN codes — filters out likely false positives."""
    text = extract_pdf_text(content)
    matches = PINCODE_RE.findall(text)

    # Filter: exclude numbers that are part of longer sequences
    # (e.g., don't match "123456" inside "1234567890")
    filtered = []
    for m in matches:
        # Find position and check surrounding chars
        idx = text.find(m)
        if idx == -1:
            continue
        # Check char before and after
        before = text[idx - 1] if idx > 0 else " "
        after = text[idx + len(m)] if idx + len(m) < len(text) else " "
        if not before.isdigit() and not after.isdigit():
            filtered.append(m)

    return _dedupe_ordered(filtered)


def extract_pan(content: bytes) -> list[str]:
    text = extract_pdf_text(content)
    return _dedupe_ordered(PAN_RE.findall(text))


def extract_all(content: bytes) -> dict:
    """Extract everything in one pass."""
    text = extract_pdf_text(content)
    text_for_phone = _normalize_text_for_matching(text)

    phones_raw = PHONE_INDIAN_RE.findall(text_for_phone) + PHONE_INTL_RE.findall(text_for_phone)
    phones = _dedupe_phones(phones_raw)

    amounts_raw = AMOUNT_RE.findall(text)
    amounts = _dedupe_ordered([_normalize_amount(m) for m in amounts_raw])

    emails_raw = EMAIL_RE.findall(text)
    emails = _dedupe_ordered(
        [_normalize_email(e) for e in emails_raw if ".." not in e and not e.endswith(".")]
    )

    urls_raw = URL_RE.findall(text)
    urls = _dedupe_ordered([m.rstrip(".,;:!?)") for m in urls_raw])

    return {
        "emails": emails,
        "phones": phones,
        "urls": urls,
        "amounts": amounts,
        "gstins": _dedupe_ordered(GSTIN_RE.findall(text)),
        "dates": _dedupe_ordered(DATE_RE.findall(text)),
        "pincodes": extract_pincodes(content),
        "pans": _dedupe_ordered(PAN_RE.findall(text)),
    }


def extraction_to_csv(result: dict) -> bytes:
    """Convert extraction result to CSV."""
    import csv
    from io import StringIO

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["type", "value"])

    for category, values in result.items():
        singular = category.rstrip("s")
        for v in values:
            writer.writerow([singular, v])

    return buf.getvalue().encode("utf-8")