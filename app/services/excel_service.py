import pandas as pd
from io import BytesIO


def excel_to_csv(content: bytes) -> bytes:
    """Convert first sheet of an Excel file to CSV."""
    df = pd.read_excel(BytesIO(content), engine="openpyxl")
    return df.to_csv(index=False).encode("utf-8")


def csv_to_excel(content: bytes) -> bytes:
    """Convert CSV to Excel (.xlsx)."""
    df = pd.read_csv(BytesIO(content))
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return out.getvalue()


def merge_excel(files: list[bytes]) -> bytes:
    """Merge multiple Excel files into one workbook (each becomes a sheet)."""
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for i, content in enumerate(files, start=1):
            df = pd.read_excel(BytesIO(content), engine="openpyxl")
            df.to_excel(writer, index=False, sheet_name=f"Sheet{i}")
    return out.getvalue()


def merge_csv(files: list[bytes]) -> bytes:
    """Stack multiple CSVs vertically into one."""
    frames = []
    for content in files:
        try:
            df = pd.read_csv(BytesIO(content))
        except UnicodeDecodeError:
            df = pd.read_csv(BytesIO(content), encoding="latin-1")
        frames.append(df)
    if not frames:
        raise ValueError("No CSV files provided")
    merged = pd.concat(frames, ignore_index=True)
    return merged.to_csv(index=False).encode("utf-8")
def split_excel(content: bytes) -> list[tuple[str, bytes]]:
    """
    Split an Excel file into separate files, one per sheet.
    Returns list of (filename, bytes).
    """
    xls = pd.ExcelFile(BytesIO(content), engine="openpyxl")
    out = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        # Sanitize filename
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in sheet_name).strip() or "sheet"
        out.append((f"{safe}.xlsx", buf.getvalue()))
    if not out:
        raise ValueError("Excel file has no sheets")
    return out


def remove_duplicates(content: bytes, column: str | None = None) -> bytes:
    """
    Remove duplicate rows. If column is given, dedupe on that column.
    Otherwise dedupe on full row.
    Supports .csv and .xlsx (detected by content).
    """
    # Detect format by trying xlsx first
    df = None
    is_xlsx = False
    try:
        df = pd.read_excel(BytesIO(content), engine="openpyxl")
        is_xlsx = True
    except Exception:
        try:
            df = pd.read_csv(BytesIO(content))
        except Exception as e:
            raise ValueError(f"Could not read as Excel or CSV: {e}")

    original = len(df)

    if column:
        if column not in df.columns:
            raise ValueError(
                f"Column '{column}' not found. Available: {list(df.columns)}"
            )
        df = df.drop_duplicates(subset=[column], keep="first")
    else:
        df = df.drop_duplicates(keep="first")

    removed = original - len(df)
    print(f"[remove_duplicates] {original} rows → {len(df)} (removed {removed})")

    buf = BytesIO()
    if is_xlsx:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
        return buf.getvalue()
    else:
        return df.to_csv(index=False).encode("utf-8")


def remove_empty_rows(content: bytes) -> bytes:
    """Remove rows where all values are empty/NaN."""
    is_xlsx = False
    df = None
    try:
        df = pd.read_excel(BytesIO(content), engine="openpyxl")
        is_xlsx = True
    except Exception:
        try:
            df = pd.read_csv(BytesIO(content))
        except Exception as e:
            raise ValueError(f"Could not read as Excel or CSV: {e}")

    original = len(df)
    df = df.dropna(how="all")

    # Also drop rows where every cell is empty string
    def _is_blank_row(row):
        return all(
            pd.isna(v) or (isinstance(v, str) and v.strip() == "")
            for v in row
        )

    df = df[~df.apply(_is_blank_row, axis=1)]
    removed = original - len(df)
    print(f"[remove_empty_rows] {original} rows → {len(df)} (removed {removed})")

    buf = BytesIO()
    if is_xlsx:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
        return buf.getvalue()
    else:
        return df.to_csv(index=False).encode("utf-8")