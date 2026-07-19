"""
Scanned PDF text extraction — Phase 3 (OCR slice).

Pipeline per page: rasterize (pdf2image) → preprocess (OpenCV: grayscale,
denoise, deskew, adaptive threshold) → OCR (pytesseract).

This is the path intake.py's is_scanned_pdf() routes files into — pdf_parser.py
(PyMuPDF/pdfplumber) is for born-digital PDFs only and will raise on a real
scan; this module is specifically for image-based pages with no text layer.

Returns the same ParsedDocument/ParsedPage shape as pdf_parser.py so
pipeline.py can treat both extraction paths identically downstream.
"""

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path

from app.ingestion.pdf_parser import ParsedDocument, ParsedPage
from app.config import POPPLER_PATH, TESSERACT_CMD

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# 300 DPI is the standard sweet spot for OCR accuracy vs. processing time —
# lower loses fine text detail, much higher rarely improves accuracy further.
OCR_DPI = 300


def _pil_to_cv2_gray(pil_image) -> np.ndarray:
    """Converts a PIL image (as returned by pdf2image) to an OpenCV grayscale array."""
    rgb = np.array(pil_image)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def _denoise(gray: np.ndarray) -> np.ndarray:
    """Removes scan speckle/noise while preserving text edges."""
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Detects and corrects page rotation from a bad scan angle.

    Uses the minimum-area bounding rectangle of all non-background (text)
    pixels to estimate skew angle, then rotates the image to straighten it.
    A page that's already straight passes through with a near-zero-degree
    rotation, so this is safe to always apply.
    """
    # Invert + threshold so text pixels are white/foreground for contour detection.
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))

    if coords.shape[0] < 10:
        # Not enough foreground pixels to reliably estimate skew (e.g. a
        # near-blank page) — return unrotated rather than guessing.
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    # cv2.minAreaRect returns angles in [-90, 0); normalize to a small
    # correction rather than a near-90-degree "correction" that would flip
    # the page sideways.
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.1:
        return gray  # not worth rotating for sub-0.1-degree skew

    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def _adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """Binarizes the image so Tesseract sees crisp black text on white,
    robust to uneven scan lighting (which a single global threshold isn't)."""
    return cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        blockSize=31, C=15,
    )


def preprocess_page_image(pil_image) -> np.ndarray:
    """Full preprocessing chain for one rasterized page, in the order that
    matters: grayscale → denoise → deskew → threshold. Deskewing before
    thresholding gives cv2.minAreaRect real grayscale gradients to work with;
    thresholding first would make skew detection less reliable."""
    gray = _pil_to_cv2_gray(pil_image)
    denoised = _denoise(gray)
    deskewed = _deskew(denoised)
    binarized = _adaptive_threshold(deskewed)
    return binarized


def parse_scanned_pdf(filepath, dpi: int = OCR_DPI) -> ParsedDocument:
    """Runs the full OCR pipeline over every page of a scanned PDF.
    Raises ValueError if OCR produces almost no text — same signal as
    pdf_parser.parse_pdf(), so pipeline.py can handle both failure cases
    identically."""
    page_images = convert_from_path(str(filepath), dpi=dpi, poppler_path=POPPLER_PATH)

    pages = []
    for i, pil_image in enumerate(page_images):
        processed = preprocess_page_image(pil_image)
        text = pytesseract.image_to_string(processed)
        pages.append(ParsedPage(page_number=i + 1, text=text))

    full_text = "\n\n".join(p.text for p in pages)

    if len(full_text.strip()) < 20:
        raise ValueError(
            f"{filepath}: OCR produced almost no text even after preprocessing. "
            f"The scan quality may be too poor, or this isn't actually a "
            f"document with recognizable text (e.g. a pure line drawing)."
        )

    return ParsedDocument(
        filename=str(filepath),
        page_count=len(pages),
        full_text=full_text,
        pages=pages,
        extractor_used="tesseract_ocr",
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m app.ingestion.ocr_parser <path-to-scanned-pdf>")
        sys.exit(1)

    parsed = parse_scanned_pdf(sys.argv[1])
    print(f"Extractor used : {parsed.extractor_used}")
    print(f"Page count     : {parsed.page_count}")
    print(f"Total chars    : {len(parsed.full_text)}")
    print("\n--- First 500 characters ---\n")
    print(parsed.full_text[:500])
