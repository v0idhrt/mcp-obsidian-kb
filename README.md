# mcp-obsidian-kb

MCP server for Obsidian with a Zettelkasten knowledge base toolkit. Connects to Obsidian via the Local REST API plugin and provides 29 tools for automated note creation, decomposition, linking, and vault maintenance.

<a href="https://glama.ai/mcp/servers/3wko1bhuek"><img width="380" height="200" src="https://glama.ai/mcp/servers/3wko1bhuek/badge" alt="server for Obsidian MCP server" /></a>

## Tools

### Core Obsidian tools

| Tool | Description |
|------|-------------|
| `obsidian_list_files_in_vault` | List all files and directories in the vault root |
| `obsidian_list_files_in_dir` | List files in a specific directory |
| `obsidian_get_file_contents` | Read content of a single file |
| `obsidian_get_batch_file_contents` | Read multiple files at once |
| `obsidian_put_content` | Create or overwrite a file |
| `obsidian_append_content` | Append content to a file |
| `obsidian_patch_content` | Edit a specific section by heading, block reference, or frontmatter key |
| `obsidian_delete_file` | Delete a file or directory |
| `obsidian_simple_search` | Full-text search across the vault |
| `obsidian_complex_search` | Search using JsonLogic queries |
| `obsidian_get_periodic_note` | Get current daily/weekly/monthly note |
| `obsidian_recent_periodic_notes` | Get recent periodic notes |
| `obsidian_recent_changes` | Get recently modified files (requires Dataview plugin) |

### Knowledge base tools

Tools for Zettelkasten-style knowledge management with automated decomposition, linking, and maintenance.

| Tool | Description |
|------|-------------|
| `kb_fetch_url` | Fetch and clean a web page, extract text/metadata |
| `kb_extract_pdf` | Extract text from a PDF file in the vault |
| `kb_get_vault_structure` | Get folder tree with file counts |
| `kb_get_taxonomy` | Read the `_taxonomy.md` control file with organization rules |
| `kb_find_related_notes` | Search for related notes by keywords, ranked by relevance |
| `kb_save_atomic_note` | Create a single atomic note with frontmatter |
| `kb_save_notes_batch` | Create multiple atomic notes in one call (for article decomposition) |
| `kb_update_moc` | Add entries to a Map of Content, creates MOC if needed |
| `kb_list_mocs` | List all MOC notes in the vault |
| `kb_save_binary` | Save a binary file with a wrapper note |
| `kb_move_note` | Move one or more notes between folders |
| `kb_get_note_sections` | Parse a note into sections by headings |
| `kb_get_backlinks` | Find all notes linking to a given note |
| `kb_search_by_tag` | Find notes by tag via Dataview DQL |
| `kb_merge_notes` | Merge two duplicate notes into one |
| `kb_get_orphans` | Find notes with no incoming links |

### Taxonomy

The `_taxonomy.md` file controls how the knowledge base is organized: folder structure, tagging conventions, note style, decomposition rules, and maintenance procedures. Place it at the vault root. The model reads it via `kb_get_taxonomy` before creating or organizing notes.

## Example prompts

First instruct Claude to use Obsidian, then it will call the tools automatically.

- "Read this article and create notes in my vault: https://example.com/article"
- "Find all notes about transformers and check if any are orphaned"
- "Move all notes from Inbox/ to their proper folders based on the taxonomy"
- "Merge these two duplicate notes about gradient descent"
- "Search for all notes tagged ai/llm and update the AI MOC"
- "Get the contents of the last architecture call note and summarize them"

## Configuration

### Prerequisites

1. Install the [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) community plugin in Obsidian
2. Enable it and copy the API key from plugin settings
3. (Optional) Install the [Dataview](https://github.com/blacksmithgu/obsidian-dataview) plugin for `kb_search_by_tag` and `obsidian_recent_changes`

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_API_KEY` | (required) | API key from the Local REST API plugin |
| `OBSIDIAN_HOST` | `127.0.0.1` | Obsidian REST API host |
| `OBSIDIAN_PORT` | `27124` | Obsidian REST API port |
| `OBSIDIAN_PROTOCOL` | `https` | Protocol (`http` or `https`) |

### Claude Desktop

Config file locations:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

<details>
  <summary>Development (local clone)</summary>

```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-obsidian",
        "run",
        "mcp-obsidian"
      ],
      "env": {
        "OBSIDIAN_API_KEY": "<your_api_key>"
      }
    }
  }
}
```
</details>

<details>
  <summary>Published (via uvx)</summary>

```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "uvx",
      "args": [
        "mcp-obsidian"
      ],
      "env": {
        "OBSIDIAN_API_KEY": "<your_api_key>"
      }
    }
  }
}
```
</details>

If Claude can't find `uv`/`uvx`, use the full path from `which uvx`.

## Development

### Setup

```bash
uv sync
```

### Running tests

```bash
OBSIDIAN_API_KEY=test uv run pytest tests/ -v
```

### Debugging

MCP servers communicate over stdio. Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) for debugging:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-obsidian run mcp-obsidian
```

Server logs (macOS):
```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp-server-mcp-obsidian.log
```
