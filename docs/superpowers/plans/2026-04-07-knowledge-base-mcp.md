# Knowledge Base MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend mcp-obsidian with 9 new tools that enable LLM-orchestrated knowledge base management — URL fetching, PDF extraction, vault analysis, atomic note creation, MOC management, and binary file handling.

**Architecture:** Thin MCP approach — 4 new Python modules (`fetcher.py`, `pdf_extractor.py`, `vault_utils.py`, `kb_tools.py`) provide focused building-block tools. The calling LLM orchestrates the Zettelkasten pipeline. Existing tools remain untouched.

**Tech Stack:** Python 3.11+, trafilatura (HTML extraction), pymupdf (PDF), markdownify (HTML→MD), requests, mcp SDK

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/mcp_obsidian/fetcher.py` | Create | Web page fetching and HTML→markdown cleaning |
| `src/mcp_obsidian/pdf_extractor.py` | Create | PDF text extraction via pymupdf |
| `src/mcp_obsidian/vault_utils.py` | Create | Vault tree building, frontmatter assembly, MOC operations, related notes aggregation |
| `src/mcp_obsidian/kb_tools.py` | Create | 9 new MCP tool handlers |
| `src/mcp_obsidian/obsidian.py` | Modify | Add `get_file_contents_raw()` for binary data |
| `src/mcp_obsidian/server.py` | Modify | Register 9 new KB tool handlers |
| `pyproject.toml` | Modify | Add 3 new dependencies + pytest dev dep |
| `tests/test_fetcher.py` | Create | Unit tests for fetcher |
| `tests/test_pdf_extractor.py` | Create | Unit tests for PDF extractor |
| `tests/test_vault_utils.py` | Create | Unit tests for vault utilities |
| `tests/test_kb_tools.py` | Create | Unit tests for KB tool handlers |
| `tests/__init__.py` | Create | Empty init |

---

### Task 1: Project setup — dependencies and test infrastructure

**Files:**
- Modify: `pyproject.toml:7-11` (dependencies), `pyproject.toml:20-23` (dev deps)
- Create: `tests/__init__.py`

- [ ] **Step 1: Add dependencies to pyproject.toml**

```toml
dependencies = [
 "mcp>=1.1.0",
 "python-dotenv>=1.0.1",
 "requests>=2.32.3",
 "trafilatura>=2.0.0",
 "pymupdf>=1.25.0",
 "markdownify>=0.14.1",
]
```

And add pytest to dev dependencies:

```toml
[dependency-groups]
dev = [
    "pyright>=1.1.389",
    "pytest>=8.0.0",
]
```

- [ ] **Step 2: Create tests directory**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 3: Install dependencies**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv sync`
Expected: All dependencies install successfully, including trafilatura, pymupdf, markdownify, pytest.

- [ ] **Step 4: Verify imports work**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run python -c "import trafilatura; import fitz; import markdownify; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock tests/__init__.py
git commit -m "feat: add KB dependencies (trafilatura, pymupdf, markdownify) and test infra"
```

---

### Task 2: Web page fetcher (`fetcher.py`)

**Files:**
- Create: `src/mcp_obsidian/fetcher.py`
- Create: `tests/test_fetcher.py`

- [ ] **Step 1: Write failing tests for fetcher**

Create `tests/test_fetcher.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from mcp_obsidian.fetcher import fetch_url, FetchResult

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_fetcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_obsidian.fetcher'`

- [ ] **Step 3: Implement fetcher.py**

Create `src/mcp_obsidian/fetcher.py`:

```python
from dataclasses import dataclass, field
import requests
import trafilatura
import markdownify

MAX_PAGE_SIZE = 5 * 1024 * 1024  # 5 MB
FETCH_TIMEOUT = 30


@dataclass
class FetchResult:
    content: str = ""
    title: str | None = None
    author: str | None = None
    date: str | None = None
    source_url: str = ""
    is_pdf: bool = False
    warning: str | None = None


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
    metadata = trafilatura.extract(
        html,
        output_format="txt",
        include_comments=False,
        include_tables=True,
        with_metadata=True,
    )

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

    # Fallback to markdownify if trafilatura returns nothing
    if not content:
        content = markdownify.markdownify(
            html.decode("utf-8", errors="replace"),
            heading_style="ATX",
            strip=["script", "style", "nav", "footer", "header"],
        )
        warning = "Content extracted via fallback method, may contain noise"
    else:
        warning = None

    return FetchResult(
        content=content,
        title=title,
        author=author,
        date=date,
        source_url=response.url,
        warning=warning,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_fetcher.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_obsidian/fetcher.py tests/test_fetcher.py
git commit -m "feat: add web page fetcher with trafilatura extraction"
```

---

### Task 3: PDF extractor (`pdf_extractor.py`)

**Files:**
- Create: `src/mcp_obsidian/pdf_extractor.py`
- Create: `tests/test_pdf_extractor.py`

- [ ] **Step 1: Write failing tests for PDF extractor**

Create `tests/test_pdf_extractor.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from mcp_obsidian.pdf_extractor import extract_pdf_text

class TestExtractPdfText:
    def test_extract_returns_text(self):
        # Create a minimal valid PDF with pymupdf
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_pdf_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_obsidian.pdf_extractor'`

- [ ] **Step 3: Implement pdf_extractor.py**

Create `src/mcp_obsidian/pdf_extractor.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_pdf_extractor.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_obsidian/pdf_extractor.py tests/test_pdf_extractor.py
git commit -m "feat: add PDF text extractor with pymupdf"
```

---

### Task 4: Vault utilities (`vault_utils.py`)

**Files:**
- Create: `src/mcp_obsidian/vault_utils.py`
- Create: `tests/test_vault_utils.py`

- [ ] **Step 1: Write failing tests for vault utils**

Create `tests/test_vault_utils.py`:

```python
import pytest
from mcp_obsidian.vault_utils import (
    build_vault_tree,
    build_frontmatter,
    build_atomic_note,
    build_moc_entry,
    build_new_moc,
    append_to_moc,
    build_binary_wrapper,
    aggregate_search_results,
)

class TestBuildVaultTree:
    def test_empty_list(self):
        assert build_vault_tree([]) == {}

    def test_flat_files(self):
        files = ["note1.md", "note2.md"]
        tree = build_vault_tree(files)
        assert tree == {"_count": 2}

    def test_nested_folders(self):
        files = [
            "Программирование/Python/intro.md",
            "Программирование/Python/advanced.md",
            "Программирование/Go/basics.md",
            "Финансы/budget.md",
        ]
        tree = build_vault_tree(files)
        assert tree["Программирование"]["_count"] == 0
        assert tree["Программирование"]["Python"]["_count"] == 2
        assert tree["Программирование"]["Go"]["_count"] == 1
        assert tree["Финансы"]["_count"] == 1

    def test_mixed_root_and_nested(self):
        files = ["root.md", "folder/nested.md"]
        tree = build_vault_tree(files)
        assert tree["_count"] == 1
        assert tree["folder"]["_count"] == 1


class TestBuildFrontmatter:
    def test_minimal(self):
        result = build_frontmatter(title="Test", tags=["tag1"])
        assert "title: \"Test\"" in result
        assert "tags:" in result
        assert "tag1" in result
        assert result.startswith("---\n")
        assert result.endswith("---\n")

    def test_full(self):
        result = build_frontmatter(
            title="Full Note",
            tags=["a", "b"],
            aliases=["alias1"],
            source="https://example.com",
            source_type="url",
            related=["Note A", "Note B"],
            moc="MOC Test",
        )
        assert "source: \"https://example.com\"" in result
        assert "source_type: \"url\"" in result
        assert "\"[[Note A]]\"" in result
        assert "\"[[Note B]]\"" in result
        assert "moc: \"[[MOC Test]]\"" in result
        assert "aliases:" in result

    def test_created_date_is_today(self):
        from datetime import date
        result = build_frontmatter(title="T", tags=["t"])
        assert f"created: \"{date.today().isoformat()}\"" in result


class TestBuildAtomicNote:
    def test_without_related(self):
        note = build_atomic_note(
            title="Test",
            content="Body text here.",
            tags=["tag"],
        )
        assert "---" in note
        assert "Body text here." in note
        assert "## Related" not in note  # no related section if no related notes

    def test_with_related(self):
        note = build_atomic_note(
            title="Test",
            content="Body.",
            tags=["tag"],
            related=["Note A", "Note B"],
        )
        assert "## Related" in note  # renamed from "Связанные"
        assert "[[Note A]]" in note
        assert "[[Note B]]" in note


class TestMocOperations:
    def test_build_moc_entry(self):
        entry = build_moc_entry(title="My Note", path="folder/my-note.md", description="A note")
        assert entry == "- [[folder/my-note.md|My Note]] — A note"

    def test_build_new_moc(self):
        moc = build_new_moc(
            title="MOC Programming",
            entries=[{"title": "Note 1", "path": "p/n1.md", "description": "desc1"}],
        )
        assert "title: \"MOC Programming\"" in moc
        assert "tags:" in moc
        assert "moc" in moc
        assert "[[p/n1.md|Note 1]]" in moc

    def test_append_to_moc_adds_entries(self):
        existing = """---
title: "MOC Test"
tags: [moc]
---
# Test

- [[old.md|Old Note]] — old desc
"""
        result = append_to_moc(
            existing_content=existing,
            entries=[{"title": "New Note", "path": "new.md", "description": "new desc"}],
        )
        assert "[[new.md|New Note]]" in result
        assert "[[old.md|Old Note]]" in result

    def test_append_to_moc_deduplicates(self):
        existing = """---
title: "MOC Test"
tags: [moc]
---
# Test

- [[old.md|Old Note]] — old desc
"""
        result = append_to_moc(
            existing_content=existing,
            entries=[{"title": "Old Note Updated", "path": "old.md", "description": "new desc"}],
        )
        # Should not add duplicate
        assert result.count("old.md") == 1


class TestBuildBinaryWrapper:
    def test_wrapper_content(self):
        result = build_binary_wrapper(
            title="Screenshot",
            attachment_path="_attachments/screen.png",
            description="UI mockup",
            tags=["screenshot"],
        )
        assert "title: \"Screenshot\"" in result
        assert "source_type: \"binary\"" in result
        assert "![[_attachments/screen.png]]" in result
        assert "UI mockup" in result
        assert "screenshot" in result


class TestAggregateSearchResults:
    def test_deduplicates_and_ranks(self):
        results_per_keyword = [
            [
                {"filename": "a.md", "score": 10, "matches": [{"context": "ctx a1"}]},
                {"filename": "b.md", "score": 5, "matches": [{"context": "ctx b1"}]},
            ],
            [
                {"filename": "a.md", "score": 8, "matches": [{"context": "ctx a2"}]},
                {"filename": "c.md", "score": 3, "matches": [{"context": "ctx c1"}]},
            ],
        ]
        result = aggregate_search_results(results_per_keyword, limit=10)
        # a.md should be first (highest cumulative score 18)
        assert result[0]["path"] == "a.md"
        assert result[0]["score"] == 18
        assert len(result) == 3

    def test_respects_limit(self):
        results_per_keyword = [
            [{"filename": f"{i}.md", "score": i, "matches": [{"context": "c"}]} for i in range(10)],
        ]
        result = aggregate_search_results(results_per_keyword, limit=3)
        assert len(result) == 3

    def test_empty_input(self):
        assert aggregate_search_results([], limit=10) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_vault_utils.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_obsidian.vault_utils'`

- [ ] **Step 3: Implement vault_utils.py**

Create `src/mcp_obsidian/vault_utils.py`:

```python
from datetime import date


def build_vault_tree(file_list: list[str]) -> dict:
    """Build a folder tree with file counts from a flat list of file paths."""
    if not file_list:
        return {}

    tree: dict = {}

    for filepath in file_list:
        parts = filepath.split("/")
        if len(parts) == 1:
            # Root-level file
            tree["_count"] = tree.get("_count", 0) + 1
        else:
            # Nested file — walk/create folder nodes
            current = tree
            for folder in parts[:-1]:
                if folder not in current:
                    current[folder] = {"_count": 0}
                current = current[folder]
            current["_count"] = current.get("_count", 0) + 1

    return tree


def build_frontmatter(
    title: str,
    tags: list[str],
    aliases: list[str] | None = None,
    source: str | None = None,
    source_type: str | None = None,
    related: list[str] | None = None,
    moc: str | None = None,
) -> str:
    """Build YAML frontmatter string for an atomic note."""
    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f"tags: [{', '.join(tags)}]")

    if aliases:
        aliases_str = ", ".join(f'"{a}"' for a in aliases)
        lines.append(f"aliases: [{aliases_str}]")

    if source:
        lines.append(f'source: "{source}"')

    if source_type:
        lines.append(f'source_type: "{source_type}"')

    lines.append(f'created: "{date.today().isoformat()}"')

    if related:
        related_str = ", ".join(f'"[[{r}]]"' for r in related)
        lines.append(f"related: [{related_str}]")

    if moc:
        lines.append(f'moc: "[[{moc}]]"')

    lines.append("---")
    return "\n".join(lines) + "\n"


def build_atomic_note(
    title: str,
    content: str,
    tags: list[str],
    aliases: list[str] | None = None,
    source: str | None = None,
    source_type: str | None = None,
    related: list[str] | None = None,
    moc: str | None = None,
) -> str:
    """Build a complete atomic note with frontmatter and content."""
    frontmatter = build_frontmatter(
        title=title,
        tags=tags,
        aliases=aliases,
        source=source,
        source_type=source_type,
        related=related,
        moc=moc,
    )

    parts = [frontmatter, "", content]

    if related:
        parts.append("")
        parts.append("## Related")
        for r in related:
            parts.append(f"- [[{r}]]")

    return "\n".join(parts) + "\n"


def build_moc_entry(title: str, path: str, description: str) -> str:
    """Build a single MOC entry line."""
    return f"- [[{path}|{title}]] \u2014 {description}"


def build_new_moc(title: str, entries: list[dict]) -> str:
    """Build a complete new MOC note.

    Args:
        title: MOC title
        entries: List of dicts with keys: title, path, description
    """
    frontmatter = build_frontmatter(title=title, tags=["moc"])

    lines = [frontmatter, f"# {title.removeprefix('MOC ')}", ""]

    for entry in entries:
        lines.append(build_moc_entry(entry["title"], entry["path"], entry["description"]))

    return "\n".join(lines) + "\n"


def append_to_moc(existing_content: str, entries: list[dict]) -> str:
    """Append new entries to an existing MOC, deduplicating by path.

    Args:
        existing_content: Current MOC file content
        entries: List of dicts with keys: title, path, description
    """
    new_entries = []
    for entry in entries:
        # Check if path already exists in MOC
        if entry["path"] not in existing_content:
            new_entries.append(
                build_moc_entry(entry["title"], entry["path"], entry["description"])
            )

    if not new_entries:
        return existing_content

    result = existing_content.rstrip("\n")
    result += "\n" + "\n".join(new_entries) + "\n"
    return result


def build_binary_wrapper(
    title: str,
    attachment_path: str,
    description: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Build a wrapper note for a binary file.

    Args:
        title: Note title
        attachment_path: Relative path to the attachment in vault
        description: Optional description
        tags: Optional tags (added to [attachment, ...])
    """
    all_tags = ["attachment"] + (tags or [])
    frontmatter = build_frontmatter(title=title, tags=all_tags, source_type="binary")
    # Inject file field into frontmatter (before closing ---)
    frontmatter_lines = frontmatter.split("\n")
    # Insert before last "---"
    insert_idx = len(frontmatter_lines) - 2  # before closing ---
    frontmatter_lines.insert(insert_idx, f'file: "[[{attachment_path}]]"')
    frontmatter = "\n".join(frontmatter_lines)

    parts = [frontmatter, f"# {title}", "", f"![[{attachment_path}]]"]
    if description:
        parts.append("")
        parts.append(description)

    return "\n".join(parts) + "\n"


def aggregate_search_results(
    results_per_keyword: list[list[dict]], limit: int = 20
) -> list[dict]:
    """Aggregate and rank search results from multiple keyword searches.

    Args:
        results_per_keyword: List of search result lists (one per keyword)
        limit: Maximum results to return

    Returns:
        Deduplicated, ranked list of {path, title, score, snippet}
    """
    scores: dict[str, float] = {}
    snippets: dict[str, str] = {}

    for results in results_per_keyword:
        for item in results:
            path = item["filename"]
            score = item.get("score", 0)
            scores[path] = scores.get(path, 0) + score

            # Keep first snippet found
            if path not in snippets:
                matches = item.get("matches", [])
                if matches:
                    ctx = matches[0].get("context", "") if isinstance(matches[0], dict) else ""
                    snippets[path] = ctx

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    return [
        {
            "path": path,
            "title": path.rsplit("/", 1)[-1].removesuffix(".md"),
            "score": score,
            "snippet": snippets.get(path, ""),
        }
        for path, score in ranked
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_vault_utils.py -v`
Expected: All 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_obsidian/vault_utils.py tests/test_vault_utils.py
git commit -m "feat: add vault utilities (tree building, frontmatter, MOC ops, search aggregation)"
```

---

### Task 5: Add `get_file_contents_raw()` to obsidian.py

**Files:**
- Modify: `src/mcp_obsidian/obsidian.py` (add method after `get_file_contents` at ~line 79)

- [ ] **Step 1: Add get_file_contents_raw method**

Add after `get_file_contents()` method (after line 79 in `obsidian.py`):

```python
    def get_file_contents_raw(self, filepath: str) -> bytes:
        """Get raw binary contents of a file in the vault.

        Args:
            filepath: Path to file relative to vault root

        Returns:
            Raw file bytes
        """
        url = f"{self.get_base_url()}/vault/{urllib.parse.quote(filepath, safe='/')}"

        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return response.content

        return self._safe_call(call_fn)
```

- [ ] **Step 2: Verify the module still imports cleanly**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run python -c "from mcp_obsidian.obsidian import Obsidian; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/mcp_obsidian/obsidian.py
git commit -m "feat: add get_file_contents_raw() for binary file access"
```

---

### Task 6: KB tool handlers — content fetching tools (`kb_tools.py` part 1)

**Files:**
- Create: `src/mcp_obsidian/kb_tools.py`
- Create: `tests/test_kb_tools.py`

- [ ] **Step 1: Write failing tests for FetchUrlToolHandler and ExtractPdfToolHandler**

Create `tests/test_kb_tools.py`:

```python
import pytest
import json
from unittest.mock import patch, MagicMock
from mcp_obsidian.kb_tools import FetchUrlToolHandler, ExtractPdfToolHandler


class TestFetchUrlToolHandler:
    def setup_method(self):
        self.handler = FetchUrlToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_fetch_url"

    def test_tool_description_exists(self):
        desc = self.handler.get_tool_description()
        assert desc.name == "kb_fetch_url"
        assert "url" in desc.inputSchema["properties"]

    def test_missing_url_raises(self):
        with pytest.raises(RuntimeError, match="url"):
            self.handler.run_tool({})

    @patch("mcp_obsidian.kb_tools.fetch_url")
    def test_returns_content(self, mock_fetch):
        from mcp_obsidian.fetcher import FetchResult
        mock_fetch.return_value = FetchResult(
            content="# Article\n\nSome text",
            title="Article",
            author="Author",
            date="2026-01-01",
            source_url="https://example.com",
        )
        result = self.handler.run_tool({"url": "https://example.com"})
        data = json.loads(result[0].text)
        assert data["title"] == "Article"
        assert data["content"] == "# Article\n\nSome text"
        assert data["source_url"] == "https://example.com"

    @patch("mcp_obsidian.kb_tools.fetch_url")
    def test_pdf_detected(self, mock_fetch):
        from mcp_obsidian.fetcher import FetchResult
        mock_fetch.return_value = FetchResult(
            source_url="https://example.com/paper.pdf",
            is_pdf=True,
        )
        result = self.handler.run_tool({"url": "https://example.com/paper.pdf"})
        data = json.loads(result[0].text)
        assert data["is_pdf"] is True


class TestExtractPdfToolHandler:
    def setup_method(self):
        self.handler = ExtractPdfToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_extract_pdf"

    def test_missing_filepath_raises(self):
        with pytest.raises(RuntimeError, match="filepath"):
            self.handler.run_tool({})

    @patch("mcp_obsidian.kb_tools.obsidian.Obsidian")
    @patch("mcp_obsidian.kb_tools.extract_pdf_text")
    def test_extracts_text(self, mock_extract, mock_obsidian_cls):
        mock_api = MagicMock()
        mock_api.get_file_contents_raw.return_value = b"fake pdf bytes"
        mock_obsidian_cls.return_value = mock_api
        mock_extract.return_value = "Extracted PDF text"

        result = self.handler.run_tool({"filepath": "docs/paper.pdf"})
        assert "Extracted PDF text" in result[0].text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_kb_tools.py::TestFetchUrlToolHandler tests/test_kb_tools.py::TestExtractPdfToolHandler -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_obsidian.kb_tools'`

- [ ] **Step 3: Implement content fetching tool handlers**

Create `src/mcp_obsidian/kb_tools.py`:

```python
import json
import os
from collections.abc import Sequence
from datetime import date

from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from . import obsidian
from .tools import ToolHandler
from .fetcher import fetch_url, FetchResult
from .pdf_extractor import extract_pdf_text
from .vault_utils import (
    build_vault_tree,
    build_atomic_note,
    build_new_moc,
    append_to_moc,
    build_binary_wrapper,
    build_moc_entry,
    aggregate_search_results,
)

api_key = os.getenv("OBSIDIAN_API_KEY", "")
obsidian_host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")


def _get_api() -> obsidian.Obsidian:
    return obsidian.Obsidian(api_key=api_key, host=obsidian_host)


class FetchUrlToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_fetch_url")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Fetch a web page by URL, clean it from ads/navigation, and return "
                "clean markdown text with metadata (title, author, date). "
                "After fetching, use kb_get_taxonomy and kb_get_vault_structure to "
                "determine where to place notes, then kb_find_related_notes to "
                "discover connections."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the web page to fetch",
                    }
                },
                "required": ["url"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "url" not in args:
            raise RuntimeError("url argument missing")

        result = fetch_url(args["url"])

        output = {
            "content": result.content,
            "title": result.title,
            "author": result.author,
            "date": result.date,
            "source_url": result.source_url,
            "is_pdf": result.is_pdf,
        }
        if result.warning:
            output["warning"] = result.warning

        return [TextContent(type="text", text=json.dumps(output, ensure_ascii=False, indent=2))]


class ExtractPdfToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_extract_pdf")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Extract text from a PDF file already present in the vault. "
                "Returns plain text extracted from all pages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the PDF file in vault (relative to vault root)",
                        "format": "path",
                    }
                },
                "required": ["filepath"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing")

        api = _get_api()
        raw_bytes = api.get_file_contents_raw(args["filepath"])
        text = extract_pdf_text(raw_bytes)

        return [TextContent(type="text", text=text)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_kb_tools.py::TestFetchUrlToolHandler tests/test_kb_tools.py::TestExtractPdfToolHandler -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_obsidian/kb_tools.py tests/test_kb_tools.py
git commit -m "feat: add kb_fetch_url and kb_extract_pdf tool handlers"
```

---

### Task 7: KB tool handlers — vault analysis tools (`kb_tools.py` part 2)

**Files:**
- Modify: `src/mcp_obsidian/kb_tools.py` (append classes)
- Modify: `tests/test_kb_tools.py` (append test classes)

- [ ] **Step 1: Write failing tests for vault analysis tools**

Append to `tests/test_kb_tools.py`:

```python
from mcp_obsidian.kb_tools import (
    GetVaultStructureToolHandler,
    GetTaxonomyToolHandler,
    FindRelatedNotesToolHandler,
)


class TestGetVaultStructureToolHandler:
    def setup_method(self):
        self.handler = GetVaultStructureToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_get_vault_structure"

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_returns_tree(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.list_files_in_vault.return_value = [
            "Программирование/Python/intro.md",
            "Финансы/budget.md",
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({})
        data = json.loads(result[0].text)
        assert "Программирование" in data
        assert data["Финансы"]["_count"] == 1


class TestGetTaxonomyToolHandler:
    def setup_method(self):
        self.handler = GetTaxonomyToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_get_taxonomy"

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_returns_content(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.return_value = "# Таксономия\n\n## Папки\n- Тест/"
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({})
        assert "Таксономия" in result[0].text

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_missing_taxonomy_returns_message(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = Exception("Not found")
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({})
        assert "not configured" in result[0].text.lower() or "не настроена" in result[0].text.lower()


class TestFindRelatedNotesToolHandler:
    def setup_method(self):
        self.handler = FindRelatedNotesToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_find_related_notes"

    def test_missing_keywords_raises(self):
        with pytest.raises(RuntimeError, match="keywords"):
            self.handler.run_tool({})

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_returns_aggregated_results(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.search.return_value = [
            {"filename": "note1.md", "score": 10, "matches": [{"context": "some context"}]},
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"keywords": ["python"]})
        data = json.loads(result[0].text)
        assert len(data) == 1
        assert data[0]["path"] == "note1.md"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_kb_tools.py::TestGetVaultStructureToolHandler tests/test_kb_tools.py::TestGetTaxonomyToolHandler tests/test_kb_tools.py::TestFindRelatedNotesToolHandler -v`
Expected: FAIL — `ImportError: cannot import name 'GetVaultStructureToolHandler'`

- [ ] **Step 3: Implement vault analysis tool handlers**

Append to `src/mcp_obsidian/kb_tools.py`:

```python
class GetVaultStructureToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_get_vault_structure")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Get the folder tree structure of the vault with file counts per folder. "
                "Use this to understand existing organization before placing new notes."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = _get_api()
        files = api.list_files_in_vault()
        tree = build_vault_tree(files)

        return [TextContent(type="text", text=json.dumps(tree, ensure_ascii=False, indent=2))]


class GetTaxonomyToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_get_taxonomy")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Read the _taxonomy.md control note from the vault root. "
                "This file contains folder organization rules and naming conventions. "
                "Use together with kb_get_vault_structure to decide where to place new notes."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = _get_api()
        try:
            content = api.get_file_contents("_taxonomy.md")
        except Exception:
            content = "Taxonomy not configured. No _taxonomy.md found in vault root."

        return [TextContent(type="text", text=content)]


class FindRelatedNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_find_related_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Search for notes related by keywords. Returns ranked results with snippets. "
                "Use this after analyzing content to discover existing notes that should be linked."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Search terms to find related notes",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["keywords"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "keywords" not in args:
            raise RuntimeError("keywords argument missing")

        api = _get_api()
        limit = args.get("limit", 20)

        results_per_keyword = []
        for keyword in args["keywords"]:
            try:
                results = api.search(keyword, context_length=150)
                results_per_keyword.append(results)
            except Exception:
                continue

        aggregated = aggregate_search_results(results_per_keyword, limit=limit)

        return [TextContent(type="text", text=json.dumps(aggregated, ensure_ascii=False, indent=2))]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_kb_tools.py::TestGetVaultStructureToolHandler tests/test_kb_tools.py::TestGetTaxonomyToolHandler tests/test_kb_tools.py::TestFindRelatedNotesToolHandler -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_obsidian/kb_tools.py tests/test_kb_tools.py
git commit -m "feat: add kb_get_vault_structure, kb_get_taxonomy, kb_find_related_notes tools"
```

---

### Task 8: KB tool handlers — creation and update tools (`kb_tools.py` part 3)

**Files:**
- Modify: `src/mcp_obsidian/kb_tools.py` (append classes)
- Modify: `tests/test_kb_tools.py` (append test classes)

- [ ] **Step 1: Write failing tests for creation/update tools**

Append to `tests/test_kb_tools.py`:

```python
from mcp_obsidian.kb_tools import (
    SaveAtomicNoteToolHandler,
    UpdateMocToolHandler,
    SaveBinaryToolHandler,
    ListMocsToolHandler,
)


class TestSaveAtomicNoteToolHandler:
    def setup_method(self):
        self.handler = SaveAtomicNoteToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_save_atomic_note"

    def test_missing_required_raises(self):
        with pytest.raises(RuntimeError):
            self.handler.run_tool({"filepath": "test.md"})  # missing title, content, tags

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_creates_note(self, mock_get_api):
        mock_api = MagicMock()
        # get_file_contents raises to indicate file doesn't exist
        mock_api.get_file_contents.side_effect = Exception("Not found")
        mock_api.put_content.return_value = None
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({
            "filepath": "Тест/заметка.md",
            "title": "Тестовая заметка",
            "content": "Содержимое заметки",
            "tags": ["тест", "пример"],
            "related": ["Другая заметка"],
            "source": "https://example.com",
            "source_type": "url",
        })

        mock_api.put_content.assert_called_once()
        call_args = mock_api.put_content.call_args
        written_content = call_args[0][1]
        assert "Тестовая заметка" in written_content
        assert "[[Другая заметка]]" in written_content
        assert "Successfully" in result[0].text

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_existing_file_raises(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.return_value = "existing content"
        mock_get_api.return_value = mock_api

        with pytest.raises(RuntimeError, match="already exists"):
            self.handler.run_tool({
                "filepath": "existing.md",
                "title": "T",
                "content": "C",
                "tags": ["t"],
            })


class TestUpdateMocToolHandler:
    def setup_method(self):
        self.handler = UpdateMocToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_update_moc"

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_creates_new_moc(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = Exception("Not found")
        mock_api.put_content.return_value = None
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({
            "moc_path": "MOC Test.md",
            "entries": [{"title": "Note 1", "path": "n1.md", "description": "desc"}],
        })

        mock_api.put_content.assert_called_once()
        written = mock_api.put_content.call_args[0][1]
        assert "MOC Test" in written
        assert "[[n1.md|Note 1]]" in written

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_appends_to_existing_moc(self, mock_get_api):
        existing_moc = "---\ntitle: \"MOC Test\"\ntags: [moc]\n---\n# Test\n\n- [[old.md|Old]] — old\n"
        mock_api = MagicMock()
        mock_api.get_file_contents.return_value = existing_moc
        mock_api.put_content.return_value = None
        mock_get_api.return_value = mock_api

        self.handler.run_tool({
            "moc_path": "MOC Test.md",
            "entries": [{"title": "New", "path": "new.md", "description": "new desc"}],
        })

        written = mock_api.put_content.call_args[0][1]
        assert "[[new.md|New]]" in written
        assert "[[old.md|Old]]" in written


class TestSaveBinaryToolHandler:
    def setup_method(self):
        self.handler = SaveBinaryToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_save_binary"

    def test_missing_required_raises(self):
        with pytest.raises(RuntimeError):
            self.handler.run_tool({"source_path": "/tmp/file.png"})  # missing vault_dir

    @patch("mcp_obsidian.kb_tools._get_api")
    @patch("builtins.open", create=True)
    def test_saves_file_and_wrapper(self, mock_open, mock_get_api):
        mock_open.return_value.__enter__ = lambda s: MagicMock(read=lambda: b"binary data")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        mock_api = MagicMock()
        mock_api.put_content.return_value = None
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({
            "source_path": "/tmp/screenshot.png",
            "vault_dir": "Тест",
            "description": "UI mockup",
            "tags": ["скриншот"],
        })

        data = json.loads(result[0].text)
        assert "file_path" in data
        assert "wrapper_path" in data
        assert "_attachments" in data["file_path"]


class TestListMocsToolHandler:
    def setup_method(self):
        self.handler = ListMocsToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_list_mocs"

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_returns_moc_list(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.search.return_value = [
            {"filename": "MOC Programming.md", "score": 10, "matches": [{"context": "tags: [moc]"}]},
            {"filename": "MOC Finance.md", "score": 8, "matches": [{"context": "tags: [moc]"}]},
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({})
        data = json.loads(result[0].text)
        assert len(data) == 2
        assert data[0]["path"] == "MOC Programming.md"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_kb_tools.py::TestSaveAtomicNoteToolHandler tests/test_kb_tools.py::TestUpdateMocToolHandler tests/test_kb_tools.py::TestSaveBinaryToolHandler tests/test_kb_tools.py::TestListMocsToolHandler -v`
Expected: FAIL — `ImportError: cannot import name 'SaveAtomicNoteToolHandler'`

- [ ] **Step 3: Implement creation/update tool handlers**

Append to `src/mcp_obsidian/kb_tools.py`:

```python
class SaveAtomicNoteToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_save_atomic_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Create an atomic Zettelkasten note with full frontmatter (tags, related, source, MOC link). "
                "Returns error if file already exists — decide whether to update or choose a different name."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Target path in vault (e.g. 'Программирование/Python/Генераторы.md')",
                        "format": "path",
                    },
                    "title": {"type": "string", "description": "Note title"},
                    "content": {"type": "string", "description": "Markdown body of the note"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags in Russian, format тема/подтема",
                    },
                    "related": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of related notes for [[wikilinks]]",
                    },
                    "source": {"type": "string", "description": "Source URL or file path"},
                    "source_type": {
                        "type": "string",
                        "enum": ["url", "pdf", "manual"],
                        "description": "Type of source",
                    },
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Alternative names for the note",
                    },
                    "moc": {"type": "string", "description": "MOC this note belongs to"},
                },
                "required": ["filepath", "title", "content", "tags"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        for field in ["filepath", "title", "content", "tags"]:
            if field not in args:
                raise RuntimeError(f"{field} argument missing")

        api = _get_api()

        # Check if file already exists
        try:
            api.get_file_contents(args["filepath"])
            raise RuntimeError(f"File already exists: {args['filepath']}. Choose a different name or update the existing file.")
        except RuntimeError:
            raise
        except Exception:
            pass  # File doesn't exist — good

        note_content = build_atomic_note(
            title=args["title"],
            content=args["content"],
            tags=args["tags"],
            aliases=args.get("aliases"),
            source=args.get("source"),
            source_type=args.get("source_type"),
            related=args.get("related"),
            moc=args.get("moc"),
        )

        api.put_content(args["filepath"], note_content)

        return [TextContent(type="text", text=f"Successfully created note: {args['filepath']}")]


class UpdateMocToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_update_moc")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Add entries to a Map of Content (MOC) note. Creates the MOC if it doesn't exist. "
                "Deduplicates entries by path. Use after creating atomic notes to update relevant MOCs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "moc_path": {
                        "type": "string",
                        "description": "Path to MOC file in vault",
                        "format": "path",
                    },
                    "entries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "path": {"type": "string"},
                                "description": {"type": "string"},
                            },
                            "required": ["title", "path", "description"],
                        },
                        "description": "Entries to add to the MOC",
                    },
                },
                "required": ["moc_path", "entries"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        for field in ["moc_path", "entries"]:
            if field not in args:
                raise RuntimeError(f"{field} argument missing")

        api = _get_api()

        try:
            existing = api.get_file_contents(args["moc_path"])
            updated = append_to_moc(existing, args["entries"])
        except Exception:
            # MOC doesn't exist — create new
            moc_title = args["moc_path"].rsplit("/", 1)[-1].removesuffix(".md")
            updated = build_new_moc(title=moc_title, entries=args["entries"])

        api.put_content(args["moc_path"], updated)

        return [TextContent(type="text", text=f"Successfully updated MOC: {args['moc_path']}")]


class SaveBinaryToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_save_binary")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Save a binary file (screenshot, document, image) to the vault and create a wrapper note. "
                "The file is saved to _attachments/ subfolder, and a markdown wrapper is created alongside."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "Absolute path to the file on disk",
                    },
                    "vault_dir": {
                        "type": "string",
                        "description": "Target folder in vault (e.g. 'Проект/Дизайн')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the file content",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for the wrapper note",
                    },
                },
                "required": ["source_path", "vault_dir"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        for field in ["source_path", "vault_dir"]:
            if field not in args:
                raise RuntimeError(f"{field} argument missing")

        source_path = args["source_path"]
        vault_dir = args["vault_dir"]
        filename = os.path.basename(source_path)
        filename_no_ext = os.path.splitext(filename)[0]

        attachment_vault_path = f"{vault_dir}/_attachments/{filename}"
        wrapper_vault_path = f"{vault_dir}/{filename_no_ext}.md"

        # Read the binary file
        with open(source_path, "rb") as f:
            file_bytes = f.read()

        api = _get_api()

        # Save binary to vault via put_content (raw bytes)
        api.put_content(attachment_vault_path, file_bytes.decode("latin-1"))

        # Build and save wrapper note
        wrapper_content = build_binary_wrapper(
            title=filename_no_ext,
            attachment_path=f"_attachments/{filename}",
            description=args.get("description"),
            tags=args.get("tags"),
        )
        api.put_content(wrapper_vault_path, wrapper_content)

        result = {
            "file_path": attachment_vault_path,
            "wrapper_path": wrapper_vault_path,
        }

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


class ListMocsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_list_mocs")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "List all Map of Content (MOC) notes in the vault. "
                "Use this to understand the existing MOC landscape before creating or updating MOCs."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = _get_api()

        try:
            results = api.search("tags: [moc]", context_length=50)
        except Exception:
            results = []

        mocs = []
        for item in results:
            path = item.get("filename", "")
            title = path.rsplit("/", 1)[-1].removesuffix(".md")
            mocs.append({"path": path, "title": title})

        return [TextContent(type="text", text=json.dumps(mocs, ensure_ascii=False, indent=2))]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/test_kb_tools.py -v`
Expected: All tests PASS (total ~18 tests across all test classes).

- [ ] **Step 5: Commit**

```bash
git add src/mcp_obsidian/kb_tools.py tests/test_kb_tools.py
git commit -m "feat: add kb_save_atomic_note, kb_update_moc, kb_save_binary, kb_list_mocs tools"
```

---

### Task 9: Register KB tools in server.py

**Files:**
- Modify: `src/mcp_obsidian/server.py:18` (add import), `server.py:44-56` (add registrations)

- [ ] **Step 1: Add import and registrations**

In `server.py`, add import after line 18 (`from . import tools`):

```python
from . import kb_tools
```

After line 56 (last `add_tool_handler` call), add:

```python
add_tool_handler(kb_tools.FetchUrlToolHandler())
add_tool_handler(kb_tools.ExtractPdfToolHandler())
add_tool_handler(kb_tools.GetVaultStructureToolHandler())
add_tool_handler(kb_tools.GetTaxonomyToolHandler())
add_tool_handler(kb_tools.FindRelatedNotesToolHandler())
add_tool_handler(kb_tools.SaveAtomicNoteToolHandler())
add_tool_handler(kb_tools.UpdateMocToolHandler())
add_tool_handler(kb_tools.SaveBinaryToolHandler())
add_tool_handler(kb_tools.ListMocsToolHandler())
```

- [ ] **Step 2: Verify server imports cleanly**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && OBSIDIAN_API_KEY=test uv run python -c "from mcp_obsidian import server; print(f'{len(server.tool_handlers)} tools registered')"`
Expected: `22 tools registered` (13 existing + 9 new)

- [ ] **Step 3: Commit**

```bash
git add src/mcp_obsidian/server.py
git commit -m "feat: register 9 KB tool handlers in MCP server"
```

---

### Task 10: Run full test suite and verify

**Files:** none (verification only)

- [ ] **Step 1: Run all tests**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 2: Verify tool listing works end-to-end**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && OBSIDIAN_API_KEY=test uv run python -c "
from mcp_obsidian import server
for name in sorted(server.tool_handlers.keys()):
    print(name)
"`

Expected output includes all 22 tools:
```
kb_extract_pdf
kb_fetch_url
kb_find_related_notes
kb_get_taxonomy
kb_get_vault_structure
kb_list_mocs
kb_save_atomic_note
kb_save_binary
kb_update_moc
obsidian_append_content
obsidian_batch_get_file_contents
obsidian_complex_search
obsidian_delete_file
obsidian_get_file_contents
obsidian_get_periodic_note
obsidian_get_recent_changes
obsidian_get_recent_periodic_notes
obsidian_list_files_in_dir
obsidian_list_files_in_vault
obsidian_patch_content
obsidian_put_content
obsidian_simple_search
```

- [ ] **Step 3: Type check**

Run: `cd /home/v0idhrt/Documents/projects/forks/mcp-obsidian && uv run pyright src/mcp_obsidian/kb_tools.py src/mcp_obsidian/vault_utils.py src/mcp_obsidian/fetcher.py src/mcp_obsidian/pdf_extractor.py`
Expected: No errors (warnings acceptable).

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address any issues found during full verification"
```

Only run this step if fixes were made. If all passed cleanly, skip.
