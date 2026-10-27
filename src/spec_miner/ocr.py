"""
OCR helpers for image-based / scanned PDF datasheet tables.

Requires the optional ``ocr`` extra:

    pip install "spec-miner[ocr]"

System packages also needed:

    # Debian / Ubuntu
    sudo apt-get install -y tesseract-ocr poppler-utils

    # macOS
    brew install tesseract poppler
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def is_ocr_available() -> bool:
    """Return True when both pdf2image and pytesseract can be imported."""
    try:
        import pdf2image  # noqa: F401
        import pytesseract  # noqa: F401
        return True
    except ImportError:
        return False


def ocr_pdf_pages(
    pdf_path: str | Path,
    *,
    dpi: int = 300,
    max_pages: Optional[int] = None,
    lang: str = "eng",
) -> Tuple[str, List[str]]:
    """
    Convert PDF pages to images and run Tesseract OCR.

    Returns
    -------
    full_text : str
        Concatenated OCR text from all processed pages.
    page_texts : list[str]
        Per-page OCR text (same order as PDF pages).
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as exp:
        raise ImportError(
            "OCR dependencies missing. Install with:\n"
            '  pip install "spec-miner[ocr]"\n'
            "and ensure system packages are present:\n"
            "  tesseract-ocr  and  poppler-utils (or brew equivalents)."
        ) from exp

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found for OCR: {path}")

    logger.info("Running OCR on %s (dpi=%d)", path.name, dpi)

    kwargs = {"dpi": dpi}
    if max_pages is not None:
        kwargs["last_page"] = max_pages

    try:
        images = convert_from_path(str(path), **kwargs)
    except Exception as exp:
        raise RuntimeError(
            f"pdf2image failed to rasterize {path.name}. "
            "Is poppler-utils installed?"
        ) from exp

    page_texts: List[str] = []
    for idx, image in enumerate(images):
        # PSM 6 = assume a single uniform block of text (good for datasheet tables)
        config = "--psm 6 --oem 3"
        try:
            text = pytesseract.image_to_string(image, lang=lang, config=config)
        except Exception as exp:
            logger.warning("Tesseract failed on page %d: %s", idx + 1, exp)
            text = ""
        page_texts.append(text or "")

    full_text = "\n\n".join(page_texts)
    logger.info(
        "OCR complete: %d pages, %d characters extracted",
        len(page_texts),
        len(full_text),
    )
    return full_text, page_texts


def should_fallback_to_ocr(
    pages_text: List[str],
    extracted_tables: List,
    *,
    min_chars: int = 400,
    min_tables: int = 1,
) -> bool:
    """
    Heuristic: decide whether native text/table extraction looks insufficient.

    Triggers OCR when the PDF yields almost no text **or** very few tables
    (typical of scanned / image-only datasheets).
    """
    total_chars = sum(len(t.strip()) for t in pages_text)
    if total_chars < min_chars:
        return True
    if len(extracted_tables) < min_tables and total_chars < 2000:
        return True
    return False
