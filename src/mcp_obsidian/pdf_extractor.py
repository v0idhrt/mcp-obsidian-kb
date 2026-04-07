import fitz

MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text content from PDF bytes.

    Args:
        pdf_bytes: Raw PDF file bytes

    Returns:
        Extracted text as a single string with pages separated by newlines
    """
    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise Exception(f"PDF size {len(pdf_bytes)} exceeds maximum {MAX_PDF_SIZE} bytes")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        raise Exception("Failed to extract text: invalid or corrupted PDF")

    pages = []
    for page in doc:
        text = page.get_text().strip()
        if text:
            pages.append(text)

    doc.close()
    return "\n\n".join(pages)
