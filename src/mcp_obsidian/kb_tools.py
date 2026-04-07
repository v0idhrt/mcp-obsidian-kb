import json
import os
from collections.abc import Sequence

from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from .tools import ToolHandler
from .fetcher import fetch_url, FetchResult
from .pdf_extractor import extract_pdf_text
from . import obsidian
from .vault_utils import (
    build_vault_tree,
    build_atomic_note,
    build_new_moc,
    append_to_moc,
    build_binary_wrapper,
    aggregate_search_results,
    parse_note_sections,
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
            "word_count": result.word_count,
            "size_category": result.size_category,
            "sections": [
                {"heading": s.heading, "word_count": s.word_count}
                for s in result.sections
            ],
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

        with open(source_path, "rb") as f:
            file_bytes = f.read()

        api = _get_api()

        api.put_content(attachment_vault_path, file_bytes.decode("latin-1"))

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


class MoveNoteToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_move_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Move one or more notes between folders in the vault. "
                "Reads each file, writes to the new path, and deletes the original. "
                "Use kb_get_vault_structure first to verify source and destination folders."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "moves": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_path": {
                                    "type": "string",
                                    "description": "Current path to the note in vault",
                                },
                                "destination_path": {
                                    "type": "string",
                                    "description": "New path for the note in vault",
                                },
                            },
                            "required": ["source_path", "destination_path"],
                        },
                        "description": "List of moves, each with source_path and destination_path",
                    },
                },
                "required": ["moves"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "moves" not in args:
            raise RuntimeError("moves argument missing")

        moves = args["moves"]
        if not moves:
            raise RuntimeError("moves list is empty")

        api = _get_api()
        results = []

        for i, move in enumerate(moves):
            source = move.get("source_path")
            destination = move.get("destination_path")

            if not source or not destination:
                results.append({"source": source, "destination": destination, "status": "error", "error": "missing source_path or destination_path"})
                continue

            if source == destination:
                results.append({"source": source, "destination": destination, "status": "error", "error": "source and destination are the same"})
                continue

            try:
                content = api.get_file_contents(source)

                # Check destination doesn't exist
                try:
                    api.get_file_contents(destination)
                    results.append({"source": source, "destination": destination, "status": "error", "error": "destination already exists"})
                    continue
                except RuntimeError:
                    raise
                except Exception:
                    pass

                api.put_content(destination, content)
                api.delete_file(source)
                results.append({"source": source, "destination": destination, "status": "moved"})
            except Exception as e:
                results.append({"source": source, "destination": destination, "status": "error", "error": str(e)})

        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]


class GetNoteSectionsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_get_note_sections")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Parse a note into sections by headings. Returns frontmatter, preamble, "
                "and each heading section with its content. Use this to understand note "
                "structure before editing a specific section with obsidian_patch_content."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the note in vault (e.g. 'Программирование/Python/Генераторы.md')",
                        "format": "path",
                    },
                },
                "required": ["filepath"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing")

        api = _get_api()
        content = api.get_file_contents(args["filepath"])
        sections = parse_note_sections(content)

        return [TextContent(type="text", text=json.dumps(sections, ensure_ascii=False, indent=2))]


class GetBacklinksToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_get_backlinks")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Find all notes that link to a given note via [[wikilinks]]. "
                "Use before moving, renaming, or deleting a note to understand its connections."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the note in vault (e.g. 'AI/Трансформеры.md')",
                        "format": "path",
                    },
                },
                "required": ["filepath"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing")

        filepath = args["filepath"]
        note_name = filepath.rsplit("/", 1)[-1].removesuffix(".md")

        api = _get_api()
        results = api.search(f"[[{note_name}]]", context_length=100)

        backlinks = []
        for item in results:
            source = item.get("filename", "")
            if source == filepath:
                continue
            backlinks.append({
                "path": source,
                "title": source.rsplit("/", 1)[-1].removesuffix(".md"),
                "context": item.get("matches", [{}])[0].get("context", "") if item.get("matches") else "",
            })

        return [TextContent(type="text", text=json.dumps(backlinks, ensure_ascii=False, indent=2))]


class SaveNotesBatchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_save_notes_batch")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Create multiple atomic Zettelkasten notes in one call. "
                "Use when decomposing an article into several ideas. "
                "Each note gets full frontmatter. Errors on individual notes don't block others."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "notes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "filepath": {"type": "string", "description": "Target path in vault"},
                                "title": {"type": "string"},
                                "content": {"type": "string", "description": "Markdown body"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "related": {"type": "array", "items": {"type": "string"}},
                                "source": {"type": "string"},
                                "source_type": {"type": "string", "enum": ["url", "pdf", "manual"]},
                                "aliases": {"type": "array", "items": {"type": "string"}},
                                "moc": {"type": "string"},
                            },
                            "required": ["filepath", "title", "content", "tags"],
                        },
                        "description": "Array of notes to create",
                    },
                },
                "required": ["notes"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "notes" not in args:
            raise RuntimeError("notes argument missing")

        notes = args["notes"]
        if not notes:
            raise RuntimeError("notes list is empty")

        api = _get_api()
        results = []

        for note in notes:
            filepath = note.get("filepath", "")
            try:
                # Check if file already exists
                try:
                    api.get_file_contents(filepath)
                    results.append({"filepath": filepath, "status": "error", "error": "file already exists"})
                    continue
                except RuntimeError:
                    raise
                except Exception:
                    pass

                note_content = build_atomic_note(
                    title=note["title"],
                    content=note["content"],
                    tags=note["tags"],
                    aliases=note.get("aliases"),
                    source=note.get("source"),
                    source_type=note.get("source_type"),
                    related=note.get("related"),
                    moc=note.get("moc"),
                )
                api.put_content(filepath, note_content)
                results.append({"filepath": filepath, "status": "created"})
            except Exception as e:
                results.append({"filepath": filepath, "status": "error", "error": str(e)})

        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]


class SearchByTagToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_search_by_tag")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Find notes with a specific tag using Dataview DQL. "
                "Supports hierarchical tags (e.g. 'программирование/python'). "
                "Requires Dataview plugin in Obsidian."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Tag to search for, without # (e.g. 'ai/llm', 'концепция')",
                    },
                },
                "required": ["tag"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "tag" not in args:
            raise RuntimeError("tag argument missing")

        tag = args["tag"]
        api = _get_api()
        results = api.search_dql(f'LIST FROM #{tag}')

        notes = []
        for item in results:
            path = item.get("filename", "")
            notes.append({
                "path": path,
                "title": path.rsplit("/", 1)[-1].removesuffix(".md"),
            })

        return [TextContent(type="text", text=json.dumps(notes, ensure_ascii=False, indent=2))]


class MergeNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_merge_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Merge two duplicate notes into one. Content from source is appended to target "
                "under a separator. Source note is deleted after merge. "
                "Use kb_get_note_sections on both notes first to review their structure."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "Note to merge FROM (will be deleted)",
                        "format": "path",
                    },
                    "target_path": {
                        "type": "string",
                        "description": "Note to merge INTO (will be kept and extended)",
                        "format": "path",
                    },
                },
                "required": ["source_path", "target_path"],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        for field in ["source_path", "target_path"]:
            if field not in args:
                raise RuntimeError(f"{field} argument missing")

        source = args["source_path"]
        target = args["target_path"]

        if source == target:
            raise RuntimeError("source and target are the same note")

        api = _get_api()
        source_content = api.get_file_contents(source)
        target_content = api.get_file_contents(target)

        # Extract source body (skip frontmatter)
        source_sections = parse_note_sections(source_content)
        source_body_parts = []
        for section in source_sections:
            if section["heading"] == "frontmatter":
                continue
            if section["heading"] in ("preamble",):
                source_body_parts.append(section["content"])
            else:
                source_body_parts.append(section["heading"] + "\n" + section["content"])

        source_body = "\n\n".join(part for part in source_body_parts if part)
        source_name = source.rsplit("/", 1)[-1].removesuffix(".md")

        merged = target_content.rstrip("\n") + f"\n\n---\n\n> [!note] Объединено из [[{source_name}]]\n\n" + source_body + "\n"

        api.put_content(target, merged)
        api.delete_file(source)

        return [TextContent(type="text", text=f"Merged '{source}' into '{target}'")]


class GetOrphansToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("kb_get_orphans")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description=(
                "Find notes with no incoming links (no other note links to them). "
                "Useful for vault maintenance — orphan notes may need linking or cleanup. "
                "Checks .md files only, skips MOCs and _taxonomy.md."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Folder to scan (e.g. 'Программирование'). Empty for entire vault.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max notes to check (default: 50, to avoid timeout)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = _get_api()
        folder = args.get("folder")
        limit = args.get("limit", 50)

        if folder:
            files = api.list_files_in_dir(folder)
        else:
            files = api.list_files_in_vault()

        md_files = [f for f in files if f.endswith(".md") and not f.endswith("_taxonomy.md")]
        md_files = md_files[:limit]

        orphans = []
        for filepath in md_files:
            note_name = filepath.rsplit("/", 1)[-1].removesuffix(".md")
            if note_name.startswith("MOC "):
                continue

            try:
                results = api.search(f"[[{note_name}]]", context_length=10)
                # Filter out self-references
                backlinks = [r for r in results if r.get("filename") != filepath]
                if not backlinks:
                    orphans.append({
                        "path": filepath,
                        "title": note_name,
                    })
            except Exception:
                continue

        return [TextContent(type="text", text=json.dumps(orphans, ensure_ascii=False, indent=2))]
