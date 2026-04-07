import pytest
from mcp_obsidian.pdf_extractor import extract_pdf_text

class TestExtractPdfText:
    def test_extract_returns_text(self):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Hello PDF World")
        pdf_bytes = doc.tobytes()
        doc.close()

        result = extract_pdf_text(pdf_bytes)
        assert "Hello PDF World" in result

    def test_extract_empty_pdf(self):
        import fitz
        doc = fitz.open()
        doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()

        result = extract_pdf_text(pdf_bytes)
        assert result == ""

    def test_extract_invalid_data_raises(self):
        with pytest.raises(Exception, match="Failed to extract"):
            extract_pdf_text(b"not a pdf at all")

    def test_extract_too_large_raises(self):
        with pytest.raises(Exception, match="exceeds maximum"):
            extract_pdf_text(b"x" * (51 * 1024 * 1024))
