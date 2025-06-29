# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a **file search MCP server** written in Python using the FastMCP framework. It provides intelligent file search capabilities by connecting to a SQLite database containing indexed document metadata.

### Core Components

- **server.py**: Main MCP server implementation with 9 search tools
- **Database**: SQLite database at `/Users/aaron/Projects/Simple_MCP_DB/filebrowser.db` containing document metadata
- **FastMCP Framework**: Modern MCP server framework for Python
- **Search Functions**: Multiple specialized search tools for different query types

### Database Schema

The server connects to a `documents` table with these key fields:
- Basic file metadata: `id`, `filename`, `file_path`, `extension`, `size`, `created_at`
- Content analysis: `summary`, `categories`, `entities`, `persons`, `places`
- Full text: `markdown_content`
- Additional metadata: `document_type`, `mentioned_dates`, `file_references`

## Available Tools

The server provides 9 MCP tools for file search:

1. **search_file_content** - General content search across summary, categories, entities, persons, places
2. **search_by_category** - Filter by document categories (Familie, Bewerbung, etc.)
3. **search_by_person** - Find documents mentioning specific people
4. **search_files_by_date** - Date range filtering
5. **find_duplicate_files** - Identify potential duplicates by file size
6. **search_by_filename** - Pattern matching on filenames
7. **search_by_extension** - Filter by file type
8. **get_file_details** - Retrieve full metadata for specific file ID
9. **get_database_stats** - Database overview and statistics

## Development Setup

### Environment
- Python 3.13.5 (uses virtual environment at `.venv/`)
- Dependencies managed through pip (see `pip list` output)
- Key dependencies: `fastmcp`, `sqlite3`, `mcp`

### Running the Server
```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# Run the MCP server
python server.py
```

### Testing
- No formal test suite is currently implemented
- Manual testing can be done by running the server and connecting via MCP client
- Database connectivity can be verified by checking the database path exists

## Key Implementation Details

### Database Connection
- Uses `/Users/aaron/Projects/Simple_MCP_DB/filebrowser.db`
- Connection is established per function call with proper cleanup
- All database operations include error handling and connection closing

### Search Patterns
- Case-insensitive searches using `COLLATE NOCASE`
- Wildcard support with `%` patterns
- Multiple column searches with OR conditions
- Results ordered by `created_at DESC`
- Configurable result limits (defaults: 20-50 depending on function)

### Error Handling
- All tools return error dictionaries on failure
- Database connection failures are caught and reported
- Invalid input parameters are handled gracefully

## Integration Notes

This server is part of a larger MCP servers collection. The parent directory contains:
- Multiple MCP server implementations (TypeScript and Python)
- Configuration files for various MCP clients (Claude Desktop, Cline, etc.)
- Shared resources and documentation

The server is designed to be used with Claude Desktop or other MCP-compatible clients for intelligent file search and document management.