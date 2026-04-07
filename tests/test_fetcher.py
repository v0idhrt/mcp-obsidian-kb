import pytest
from unittest.mock import patch, MagicMock
from mcp_obsidian.fetcher import (
    fetch_url, FetchResult,
    _count_words, _classify_size, _extract_sections,
)

class TestFetchUrl:
    def test_fetch_returns_result_object(self):
        html = """
        <html><head><title>Test Article</title></head>
        <body>
        <article>
        <h1>Test Article</h1>
        <p>This is the main content of the test article with enough text to be extracted properly by trafilatura.</p>
        <p>It needs multiple paragraphs to work reliably with content extraction libraries.</p>
        <p>Adding more content here to ensure the extraction threshold is met for trafilatura processing.</p>
        </article>
        </body></html>
        """
        with patch("mcp_obsidian.fetcher.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            mock_resp.content = html.encode("utf-8")
            mock_resp.url = "https://example.com/article"
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            result = fetch_url("https://example.com/article")

            assert isinstance(result, FetchResult)
            assert result.source_url == "https://example.com/article"
            assert result.title is not None
            assert len(result.content) > 0

    def test_fetch_pdf_content_type_returns_hint(self):
        with patch("mcp_obsidian.fetcher.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.headers = {"Content-Type": "application/pdf"}
            mock_resp.content = b"%PDF-1.4 fake content"
            mock_resp.url = "https://example.com/paper.pdf"
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            result = fetch_url("https://example.com/paper.pdf")

            assert result.is_pdf is True
            assert result.content == ""

    def test_fetch_timeout_raises(self):
        with patch("mcp_obsidian.fetcher.requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection timed out")

            with pytest.raises(Exception, match="Connection timed out"):
                fetch_url("https://example.com/slow")

    def test_fetch_too_large_raises(self):
        with patch("mcp_obsidian.fetcher.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.headers = {"Content-Type": "text/html", "Content-Length": "10000000"}
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            with pytest.raises(Exception, match="exceeds maximum"):
                fetch_url("https://example.com/huge")


class TestCountWords:
    def test_simple(self):
        assert _count_words("one two three") == 3

    def test_empty(self):
        assert _count_words("") == 0

    def test_multiline(self):
        assert _count_words("one two\nthree four\nfive") == 5


class TestClassifySize:
    def test_small(self):
        assert _classify_size(500) == "small"
        assert _classify_size(2999) == "small"

    def test_medium(self):
        assert _classify_size(3000) == "medium"
        assert _classify_size(9999) == "medium"

    def test_large(self):
        assert _classify_size(10000) == "large"
        assert _classify_size(20000) == "large"


class TestExtractSections:
    def test_with_headings(self):
        text = "Intro text here\n\n# First\n\nContent one\n\n## Second\n\nContent two\n\n### Third\n\nContent three"
        sections = _extract_sections(text)

        assert sections[0].heading == "(intro)"
        assert sections[1].heading == "# First"
        assert sections[2].heading == "## Second"
        assert sections[3].heading == "### Third"
        assert len(sections) == 4

    def test_no_headings(self):
        text = "Just plain text without any headings at all"
        sections = _extract_sections(text)
        assert len(sections) == 1
        assert sections[0].heading == "(no headings)"
        assert sections[0].word_count == 8

    def test_empty(self):
        assert _extract_sections("") == []

    def test_no_intro(self):
        text = "# Heading\n\nContent here"
        sections = _extract_sections(text)
        assert sections[0].heading == "# Heading"
        assert len(sections) == 1

    def test_word_counts(self):
        text = "# Section A\n\none two three\n\n# Section B\n\nfour five"
        sections = _extract_sections(text)
        assert sections[0].heading == "# Section A"
        assert sections[0].word_count == 3
        assert sections[1].heading == "# Section B"
        assert sections[1].word_count == 2

    def test_h4_ignored(self):
        text = "# Main\n\nContent\n\n#### Deep heading\n\nMore content"
        sections = _extract_sections(text)
        # h4 is not matched (only h1-h3), so it stays as body text
        assert len(sections) == 1
        assert sections[0].heading == "# Main"


class TestFetchUrlMetadata:
    def test_result_has_size_fields(self):
        html = """
        <html><head><title>Test</title></head>
        <body><article>
        <h1>Test Article</h1>
        <p>This is content with enough words to be extracted by trafilatura properly.</p>
        <p>Adding more paragraphs to ensure reliable extraction by the library.</p>
        <p>Third paragraph for good measure with additional text content here.</p>
        </article></body></html>
        """
        with patch("mcp_obsidian.fetcher.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
            mock_resp.content = html.encode("utf-8")
            mock_resp.url = "https://example.com/article"
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            result = fetch_url("https://example.com/article")

            assert result.word_count > 0
            assert result.size_category == "small"
            assert isinstance(result.sections, list)
