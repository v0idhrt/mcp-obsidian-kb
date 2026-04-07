from dataclasses import dataclass, field
import re
import requests
import trafilatura
import markdownify

MAX_PAGE_SIZE = 5 * 1024 * 1024  # 5 MB
FETCH_TIMEOUT = 30

SMALL_THRESHOLD = 3000   # words
LARGE_THRESHOLD = 10000  # words


@dataclass
class ContentSection:
    heading: str
    word_count: int


@dataclass
class FetchResult:
    content: str = ""
    title: str | None = None
    author: str | None = None
    date: str | None = None
    source_url: str = ""
    is_pdf: bool = False
    warning: str | None = None
    word_count: int = 0
    size_category: str = "small"  # small / medium / large
    sections: list[ContentSection] = field(default_factory=list)


def _count_words(text: str) -> int:
    return len(text.split())


def _classify_size(word_count: int) -> str:
    if word_count >= LARGE_THRESHOLD:
        return "large"
    if word_count >= SMALL_THRESHOLD:
        return "medium"
    return "small"


def _extract_sections(text: str) -> list[ContentSection]:
    """Split text into sections by markdown headings (h1-h3)."""
    heading_re = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_re.finditer(text))

    if not matches:
        wc = _count_words(text)
        if wc > 0:
            return [ContentSection(heading="(no headings)", word_count=wc)]
        return []

    sections: list[ContentSection] = []

    # Text before first heading
    pre = text[:matches[0].start()]
    pre_wc = _count_words(pre)
    if pre_wc > 0:
        sections.append(ContentSection(heading="(intro)", word_count=pre_wc))

    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end]
        sections.append(ContentSection(
            heading=m.group(0).strip(),
            word_count=_count_words(section_text),
        ))

    return sections


def fetch_url(url: str) -> FetchResult:
    """Fetch a web page, clean it, and return markdown content with metadata."""
    response = requests.get(
        url,
        timeout=FETCH_TIMEOUT,
        headers={"User-Agent": "Mozilla/5.0 (compatible; mcp-obsidian-kb/1.0)"},
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    content_length = response.headers.get("Content-Length")

    if content_length and int(content_length) > MAX_PAGE_SIZE:
        raise Exception(f"Page size {content_length} exceeds maximum {MAX_PAGE_SIZE} bytes")

    # PDF detection
    if "application/pdf" in content_type:
        return FetchResult(
            source_url=response.url,
            is_pdf=True,
        )

    # HTML extraction
    html = response.content

    if len(html) > MAX_PAGE_SIZE:
        raise Exception(f"Page size {len(html)} exceeds maximum {MAX_PAGE_SIZE} bytes")

    # Try trafilatura first
    extracted = trafilatura.extract(
        html,
        output_format="txt",
        include_comments=False,
        include_tables=True,
    )

    # Parse metadata from trafilatura
    meta = trafilatura.metadata.extract_metadata(html)
    title = meta.title if meta else None
    author = meta.author if meta else None
    date = meta.date if meta else None

    content = extracted or ""
    warning = None

    # Fallback to markdownify if trafilatura returns nothing
    if not content:
        content = markdownify.markdownify(
            html.decode("utf-8", errors="replace"),
            heading_style="ATX",
            strip=["script", "style", "nav", "footer", "header"],
        )
        warning = "Content extracted via fallback method, may contain noise"

    word_count = _count_words(content)

    return FetchResult(
        content=content,
        title=title,
        author=author,
        date=date,
        source_url=response.url,
        warning=warning,
        word_count=word_count,
        size_category=_classify_size(word_count),
        sections=_extract_sections(content),
    )
