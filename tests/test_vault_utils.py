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
    parse_note_sections,
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
        assert "## Related" not in note

    def test_with_related(self):
        note = build_atomic_note(
            title="Test",
            content="Body.",
            tags=["tag"],
            related=["Note A", "Note B"],
        )
        assert "## Related" in note
        assert "[[Note A]]" in note
        assert "[[Note B]]" in note


class TestMocOperations:
    def test_build_moc_entry(self):
        entry = build_moc_entry(title="My Note", path="folder/my-note.md", description="A note")
        assert entry == "- [[folder/my-note.md|My Note]] \u2014 A note"

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
        existing = "---\ntitle: \"MOC Test\"\ntags: [moc]\n---\n# Test\n\n- [[old.md|Old Note]] \u2014 old desc\n"
        result = append_to_moc(
            existing_content=existing,
            entries=[{"title": "New Note", "path": "new.md", "description": "new desc"}],
        )
        assert "[[new.md|New Note]]" in result
        assert "[[old.md|Old Note]]" in result

    def test_append_to_moc_deduplicates(self):
        existing = "---\ntitle: \"MOC Test\"\ntags: [moc]\n---\n# Test\n\n- [[old.md|Old Note]] \u2014 old desc\n"
        result = append_to_moc(
            existing_content=existing,
            entries=[{"title": "Old Note Updated", "path": "old.md", "description": "new desc"}],
        )
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


class TestParseNoteSections:
    def test_full_note(self):
        content = "---\ntitle: Test\ntags: [a]\n---\n\n# Heading 1\n\nIntro\n\n## Sub A\n\nContent A\n\n## Sub B\n\nContent B\n"
        sections = parse_note_sections(content)

        assert sections[0]["heading"] == "frontmatter"
        assert sections[0]["level"] == 0
        assert "title: Test" in sections[0]["content"]

        assert sections[1]["heading"] == "# Heading 1"
        assert sections[1]["level"] == 1
        assert "Intro" in sections[1]["content"]

        assert sections[2]["heading"] == "## Sub A"
        assert sections[2]["level"] == 2
        assert "Content A" in sections[2]["content"]

        assert sections[3]["heading"] == "## Sub B"
        assert "Content B" in sections[3]["content"]

    def test_no_frontmatter(self):
        content = "# Title\n\nBody here\n"
        sections = parse_note_sections(content)
        assert sections[0]["heading"] == "# Title"
        assert "Body here" in sections[0]["content"]

    def test_only_frontmatter(self):
        content = "---\ntitle: Empty\n---\n"
        sections = parse_note_sections(content)
        assert len(sections) == 1
        assert sections[0]["heading"] == "frontmatter"

    def test_preamble_before_heading(self):
        content = "Some text before any heading\n\n# First\n\nAfter heading\n"
        sections = parse_note_sections(content)
        assert sections[0]["heading"] == "preamble"
        assert "Some text before any heading" in sections[0]["content"]
        assert sections[1]["heading"] == "# First"

    def test_empty_content(self):
        sections = parse_note_sections("")
        assert sections == []

    def test_cyrillic_headings(self):
        content = "# Заголовок\n\nТекст\n\n## Подраздел\n\nЕщё текст\n"
        sections = parse_note_sections(content)
        assert sections[0]["heading"] == "# Заголовок"
        assert sections[1]["heading"] == "## Подраздел"
        assert "Ещё текст" in sections[1]["content"]
