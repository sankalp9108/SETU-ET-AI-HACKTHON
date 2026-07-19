"""
Spreadsheet text extraction — Phase 3 (spreadsheet slice).

Handles .xlsx, .xls, and .csv. Not needed by your current 8 named demo files,
but included for hackathon completeness — a real plant will have exported
CMMS/EAM data, incident logs, or equipment registers as spreadsheets, and the
build plan's ingestion pipeline explicitly covers this format.

Each row is flattened into a single text line (columns joined by ' | ', with
the header row's column names inlined per cell as 'ColumnName: value') so
retrieval can match on either a value or its column meaning without needing
a separate structured-table representation. Multi-sheet Excel files are
each treated as a separate "page" in the returned ParsedDocument, with a
sheet-name header line — mirroring how pdf_parser.py numbers PDF pages.
"""

import pandas as pd

from app.ingestion.pdf_parser import ParsedDocument, ParsedPage


def _dataframe_to_text(df: pd.DataFrame) -> str:
    """Converts one sheet/CSV's DataFrame into readable text, one line per
    row, each cell labeled with its column name so a chunk of this text is
    self-describing even out of context (e.g. 'Equipment ID: P204 | Status:
    Active' rather than a bare 'P204 | Active' that means nothing on its own
    once split into a chunk far from the header row)."""
    df = df.fillna("")
    lines = []
    for _, row in df.iterrows():
        cells = [f"{col}: {row[col]}" for col in df.columns if str(row[col]).strip()]
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def parse_spreadsheet(filepath) -> ParsedDocument:
    """Extracts all sheet/CSV data as readable text. Raises ValueError if
    the result is suspiciously empty (e.g. a spreadsheet with only headers
    and no data rows)."""
    suffix = str(filepath).lower()
    pages: list[ParsedPage] = []

    if suffix.endswith(".csv"):
        df = pd.read_csv(filepath)
        text = _dataframe_to_text(df)
        pages.append(ParsedPage(page_number=1, text=text))
    else:
        # .xlsx / .xls — one page per sheet, in workbook order.
        sheets = pd.read_excel(filepath, sheet_name=None, engine="openpyxl") \
            if suffix.endswith(".xlsx") else pd.read_excel(filepath, sheet_name=None)
        for i, (sheet_name, df) in enumerate(sheets.items()):
            body = _dataframe_to_text(df)
            text = f"[Sheet: {sheet_name}]\n{body}" if body else ""
            pages.append(ParsedPage(page_number=i + 1, text=text))

    full_text = "\n\n".join(p.text for p in pages if p.text.strip())

    if len(full_text.strip()) < 10:
        raise ValueError(
            f"{filepath}: extracted almost no data from this spreadsheet. "
            f"Check it isn't empty or header-only."
        )

    return ParsedDocument(
        filename=str(filepath),
        page_count=len(pages),
        full_text=full_text,
        pages=pages,
        extractor_used="pandas",
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.ingestion.spreadsheet_parser <path-to-spreadsheet>")
        sys.exit(1)

    parsed = parse_spreadsheet(sys.argv[1])
    print(f"Extractor used : {parsed.extractor_used}")
    print(f"Sheets/pages   : {parsed.page_count}")
    print(f"Total chars    : {len(parsed.full_text)}")
    print("\n--- First 500 characters ---\n")
    print(parsed.full_text[:500])
