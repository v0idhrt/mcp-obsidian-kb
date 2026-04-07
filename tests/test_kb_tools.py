import pytest
import json
from unittest.mock import patch, MagicMock
from mcp_obsidian.kb_tools import (
    FetchUrlToolHandler,
    ExtractPdfToolHandler,
    GetVaultStructureToolHandler,
    GetTaxonomyToolHandler,
    FindRelatedNotesToolHandler,
    SaveAtomicNoteToolHandler,
    UpdateMocToolHandler,
    SaveBinaryToolHandler,
    ListMocsToolHandler,
    MoveNoteToolHandler,
    GetNoteSectionsToolHandler,
    GetBacklinksToolHandler,
    SaveNotesBatchToolHandler,
    SearchByTagToolHandler,
    MergeNotesToolHandler,
    GetOrphansToolHandler,
)


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
    def test_returns_content_with_metadata(self, mock_fetch):
        from mcp_obsidian.fetcher import FetchResult, ContentSection
        mock_fetch.return_value = FetchResult(
            content="# Article\n\nSome text with several words here",
            title="Article",
            author="Author",
            date="2026-01-01",
            source_url="https://example.com",
            word_count=8,
            size_category="small",
            sections=[ContentSection(heading="# Article", word_count=7)],
        )
        result = self.handler.run_tool({"url": "https://example.com"})
        data = json.loads(result[0].text)
        assert data["title"] == "Article"
        assert data["content"] == "# Article\n\nSome text with several words here"
        assert data["source_url"] == "https://example.com"
        assert data["word_count"] == 8
        assert data["size_category"] == "small"
        assert len(data["sections"]) == 1
        assert data["sections"][0]["heading"] == "# Article"

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

    @patch("mcp_obsidian.kb_tools._get_api")
    @patch("mcp_obsidian.kb_tools.extract_pdf_text")
    def test_extracts_text(self, mock_extract, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents_raw.return_value = b"fake pdf bytes"
        mock_get_api.return_value = mock_api
        mock_extract.return_value = "Extracted PDF text"

        result = self.handler.run_tool({"filepath": "docs/paper.pdf"})
        assert "Extracted PDF text" in result[0].text


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


class TestSaveAtomicNoteToolHandler:
    def setup_method(self):
        self.handler = SaveAtomicNoteToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_save_atomic_note"

    def test_missing_required_raises(self):
        with pytest.raises(RuntimeError):
            self.handler.run_tool({"filepath": "test.md"})

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_creates_note(self, mock_get_api):
        mock_api = MagicMock()
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
        existing_moc = "---\ntitle: \"MOC Test\"\ntags: [moc]\n---\n# Test\n\n- [[old.md|Old]] \u2014 old\n"
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
            self.handler.run_tool({"source_path": "/tmp/file.png"})

    @patch("mcp_obsidian.kb_tools._get_api")
    @patch("builtins.open", create=True)
    def test_saves_file_and_wrapper(self, mock_open, mock_get_api):
        mock_file = MagicMock()
        mock_file.read.return_value = b"binary data"
        mock_open.return_value.__enter__ = lambda s: mock_file
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


class TestMoveNoteToolHandler:
    def setup_method(self):
        self.handler = MoveNoteToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_move_note"

    def test_tool_description_exists(self):
        desc = self.handler.get_tool_description()
        assert desc.name == "kb_move_note"
        assert "moves" in desc.inputSchema["properties"]

    def test_missing_moves_raises(self):
        with pytest.raises(RuntimeError, match="moves"):
            self.handler.run_tool({})

    def test_empty_moves_raises(self):
        with pytest.raises(RuntimeError, match="empty"):
            self.handler.run_tool({"moves": []})

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_single_move(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = [
            "# Note content",  # reading source
            Exception("404"),  # checking destination doesn't exist
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"moves": [
            {"source_path": "Inbox/Заметка.md", "destination_path": "Программирование/Заметка.md"},
        ]})
        data = json.loads(result[0].text)

        assert len(data) == 1
        assert data[0]["status"] == "moved"
        mock_api.put_content.assert_called_once_with("Программирование/Заметка.md", "# Note content")
        mock_api.delete_file.assert_called_once_with("Inbox/Заметка.md")

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_multiple_moves(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = [
            "content A", Exception("404"),  # first move
            "content B", Exception("404"),  # second move
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"moves": [
            {"source_path": "Inbox/A.md", "destination_path": "Docs/A.md"},
            {"source_path": "Inbox/B.md", "destination_path": "Docs/B.md"},
        ]})
        data = json.loads(result[0].text)

        assert len(data) == 2
        assert data[0]["status"] == "moved"
        assert data[1]["status"] == "moved"
        assert mock_api.put_content.call_count == 2
        assert mock_api.delete_file.call_count == 2

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_destination_exists_reports_error(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = [
            "# Source",        # reading source
            "# Already here",  # destination exists
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"moves": [
            {"source_path": "A/note.md", "destination_path": "B/note.md"},
        ]})
        data = json.loads(result[0].text)

        assert data[0]["status"] == "error"
        assert "already exists" in data[0]["error"]
        mock_api.put_content.assert_not_called()

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_same_path_reports_error(self, mock_get_api):
        mock_get_api.return_value = MagicMock()

        result = self.handler.run_tool({"moves": [
            {"source_path": "A/note.md", "destination_path": "A/note.md"},
        ]})
        data = json.loads(result[0].text)

        assert data[0]["status"] == "error"
        assert "same" in data[0]["error"]

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_partial_failure(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = [
            "content A", Exception("404"),  # first move ok
            Exception("source not found"),   # second move fails on read
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"moves": [
            {"source_path": "Inbox/A.md", "destination_path": "Docs/A.md"},
            {"source_path": "Inbox/gone.md", "destination_path": "Docs/gone.md"},
        ]})
        data = json.loads(result[0].text)

        assert data[0]["status"] == "moved"
        assert data[1]["status"] == "error"


class TestGetNoteSectionsToolHandler:
    def setup_method(self):
        self.handler = GetNoteSectionsToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_get_note_sections"

    def test_tool_description_exists(self):
        desc = self.handler.get_tool_description()
        assert desc.name == "kb_get_note_sections"
        assert "filepath" in desc.inputSchema["properties"]

    def test_missing_filepath_raises(self):
        with pytest.raises(RuntimeError, match="filepath"):
            self.handler.run_tool({})

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_parses_sections(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.return_value = (
            "---\ntitle: Test\ntags: [test]\n---\n\n# Title\n\nIntro text\n\n## Section A\n\nContent A\n\n## Section B\n\nContent B\n"
        )
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"filepath": "test.md"})
        data = json.loads(result[0].text)

        headings = [s["heading"] for s in data]
        assert "frontmatter" in headings
        assert "# Title" in headings
        assert "## Section A" in headings
        assert "## Section B" in headings

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_frontmatter_content(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.return_value = "---\ntitle: Hello\n---\n\nBody text\n"
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"filepath": "note.md"})
        data = json.loads(result[0].text)

        fm = [s for s in data if s["heading"] == "frontmatter"][0]
        assert "title: Hello" in fm["content"]
        assert fm["level"] == 0

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_no_frontmatter(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.return_value = "# Just a heading\n\nSome text\n"
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"filepath": "note.md"})
        data = json.loads(result[0].text)

        assert data[0]["heading"] == "# Just a heading"
        assert data[0]["level"] == 1


class TestGetBacklinksToolHandler:
    def setup_method(self):
        self.handler = GetBacklinksToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_get_backlinks"

    def test_missing_filepath_raises(self):
        with pytest.raises(RuntimeError, match="filepath"):
            self.handler.run_tool({})

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_returns_backlinks_excluding_self(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.search.return_value = [
            {"filename": "AI/Трансформеры.md", "matches": [{"context": "self ref"}]},
            {"filename": "AI/Attention.md", "matches": [{"context": "see [[Трансформеры]]"}]},
            {"filename": "AI/MOC AI.md", "matches": [{"context": "- [[Трансформеры]]"}]},
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"filepath": "AI/Трансформеры.md"})
        data = json.loads(result[0].text)

        assert len(data) == 2
        paths = [d["path"] for d in data]
        assert "AI/Трансформеры.md" not in paths
        assert "AI/Attention.md" in paths

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_no_backlinks(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.search.return_value = []
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"filepath": "Orphan/note.md"})
        data = json.loads(result[0].text)
        assert data == []


class TestSaveNotesBatchToolHandler:
    def setup_method(self):
        self.handler = SaveNotesBatchToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_save_notes_batch"

    def test_missing_notes_raises(self):
        with pytest.raises(RuntimeError, match="notes"):
            self.handler.run_tool({})

    def test_empty_notes_raises(self):
        with pytest.raises(RuntimeError, match="empty"):
            self.handler.run_tool({"notes": []})

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_creates_multiple_notes(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = Exception("404")
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"notes": [
            {"filepath": "AI/Note1.md", "title": "Note 1", "content": "Body 1", "tags": ["ai"]},
            {"filepath": "AI/Note2.md", "title": "Note 2", "content": "Body 2", "tags": ["ai"]},
        ]})
        data = json.loads(result[0].text)

        assert len(data) == 2
        assert data[0]["status"] == "created"
        assert data[1]["status"] == "created"
        assert mock_api.put_content.call_count == 2

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_existing_file_reports_error(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = [
            "existing content",  # first note exists
            Exception("404"),    # second doesn't
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"notes": [
            {"filepath": "AI/Exists.md", "title": "Exists", "content": "Body", "tags": ["ai"]},
            {"filepath": "AI/New.md", "title": "New", "content": "Body", "tags": ["ai"]},
        ]})
        data = json.loads(result[0].text)

        assert data[0]["status"] == "error"
        assert "already exists" in data[0]["error"]
        assert data[1]["status"] == "created"


class TestSearchByTagToolHandler:
    def setup_method(self):
        self.handler = SearchByTagToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_search_by_tag"

    def test_missing_tag_raises(self):
        with pytest.raises(RuntimeError, match="tag"):
            self.handler.run_tool({})

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_returns_notes(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.search_dql.return_value = [
            {"filename": "AI/Трансформеры.md"},
            {"filename": "AI/GPT.md"},
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"tag": "ai/llm"})
        data = json.loads(result[0].text)

        assert len(data) == 2
        assert data[0]["path"] == "AI/Трансформеры.md"
        mock_api.search_dql.assert_called_once_with("LIST FROM #ai/llm")

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_empty_results(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.search_dql.return_value = []
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"tag": "несуществующий"})
        data = json.loads(result[0].text)
        assert data == []


class TestMergeNotesToolHandler:
    def setup_method(self):
        self.handler = MergeNotesToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_merge_notes"

    def test_missing_fields_raises(self):
        with pytest.raises(RuntimeError, match="source_path"):
            self.handler.run_tool({"target_path": "b.md"})
        with pytest.raises(RuntimeError, match="target_path"):
            self.handler.run_tool({"source_path": "a.md"})

    def test_same_note_raises(self):
        with pytest.raises(RuntimeError, match="same"):
            self.handler.run_tool({"source_path": "a.md", "target_path": "a.md"})

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_merges_notes(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.get_file_contents.side_effect = [
            "---\ntitle: Source\ntags: [ai]\n---\n\n# Source\n\nSource body\n",  # source
            "---\ntitle: Target\ntags: [ai]\n---\n\n# Target\n\nTarget body\n",  # target
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({
            "source_path": "AI/Дубликат.md",
            "target_path": "AI/Оригинал.md",
        })

        assert "Merged" in result[0].text
        # Check target was updated with merged content
        written_content = mock_api.put_content.call_args[0][1]
        assert "Target body" in written_content
        assert "Source body" in written_content
        assert "Объединено из" in written_content
        # Source was deleted
        mock_api.delete_file.assert_called_once_with("AI/Дубликат.md")


class TestGetOrphansToolHandler:
    def setup_method(self):
        self.handler = GetOrphansToolHandler()

    def test_tool_name(self):
        assert self.handler.name == "kb_get_orphans"

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_finds_orphans(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.list_files_in_vault.return_value = [
            "AI/Connected.md",
            "AI/Orphan.md",
            "AI/MOC AI.md",
        ]
        mock_api.search.side_effect = [
            [{"filename": "AI/MOC AI.md"}],  # Connected has a backlink
            [],                                # Orphan has none
        ]
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({})
        data = json.loads(result[0].text)

        assert len(data) == 1
        assert data[0]["path"] == "AI/Orphan.md"

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_skips_mocs_and_taxonomy(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.list_files_in_vault.return_value = [
            "AI/MOC AI.md",
            "_taxonomy.md",
            "AI/Note.md",
        ]
        mock_api.search.return_value = []
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({})
        data = json.loads(result[0].text)

        # Only Note.md checked, MOC and taxonomy skipped
        assert len(data) == 1
        assert data[0]["title"] == "Note"

    @patch("mcp_obsidian.kb_tools._get_api")
    def test_folder_filter(self, mock_get_api):
        mock_api = MagicMock()
        mock_api.list_files_in_dir.return_value = ["Inbox/note.md"]
        mock_api.search.return_value = []
        mock_get_api.return_value = mock_api

        result = self.handler.run_tool({"folder": "Inbox"})
        data = json.loads(result[0].text)

        mock_api.list_files_in_dir.assert_called_once_with("Inbox")
        assert len(data) == 1
