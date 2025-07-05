# FileBrowser Server Components - Extracted

This directory contains the **server-only components** extracted from the FileBrowser project at `/Users/aaron/Projects/filebrowser`.

## What was copied from where

### Root Files
```
FROM: /Users/aaron/Projects/filebrowser/
TO:   /Users/aaron/Projects/mcp-servers/file-search-server-v3/

✅ main.py                    → main.py
✅ requirements.txt           → requirements.txt  
✅ .env.example              → .env.example
✅ .gitignore                → .gitignore
```

### Server Source Code
```
FROM: /Users/aaron/Projects/filebrowser/src/
TO:   /Users/aaron/Projects/mcp-servers/file-search-server-v3/src/

✅ __init__.py               → src/__init__.py
✅ api/                      → src/api/          (FastAPI server + MCP server)
✅ core/                     → src/core/         (File watcher, ingestion, config)
✅ database/                 → src/database/     (SQLite database layer)
✅ extractors/               → src/extractors/   (Text extraction with Docling)
✅ utils/                    → src/utils/        (Utilities, AppleScript converter)
```

### Created Directories
```
✅ config/                   (Empty - for configuration files)
✅ logs/                     (Empty - for log files)  
✅ data/                     (Empty - for database files)
```

## What was NOT copied (Frontend)

The following frontend components were deliberately **NOT copied** and remain in the original project:

```
❌ src/streamlit_mcp_client/  (Streamlit UI - Frontend)
❌ src/frontend/              (UI components - Frontend)
```

## Architecture Overview

This extracted server contains:

| Component | Purpose | Technology |
|-----------|---------|------------|
| **File Watcher** | Monitors filesystem changes | Python + watchdog (FSEvents/inotify) |
| **Text Extractor** | Extracts text from files | Docling + AppleScript for Pages |
| **Ingestion Engine** | Processes and stores documents | Python + SQLite |
| **MCP API Server** | AI metadata generation | FastAPI + MCP Protocol |
| **Search API** | Handles search queries | SQLite FTS5 |
| **Database Layer** | Document storage | SQLite with FTS5 search |

## Setup Instructions

1. **Create virtual environment:**
   ```bash
   cd /Users/aaron/Projects/mcp-servers/file-search-server-v3
   python -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run the server:**
   ```bash
   python main.py
   ```

## Key Server Modules

- **main.py** - Application entry point, starts file watcher and ingestion
- **src/api/main.py** - FastAPI server for search API
- **src/core/file_watcher.py** - Filesystem monitoring
- **src/core/ingestion.py** - Document processing pipeline with hidden file filtering
- **src/database/database.py** - MCP-compliant database operations
- **src/extractors/docling_extractor.py** - Text extraction engine
- **src/extractors/zip_extractor.py** - ZIP archive processing with system file filtering
- **src/extractors/email_extractor.py** - EML email processing with attachment filtering

## Testing Framework

- **full_ingestion_test.py** - Comprehensive ingestion test with automatic error detection
- **eml_ingestion_test.py** - Specialized EML file processing tests
- **zip_ingestion_test_robust.py** - ZIP file processing validation

## Recent Improvements

### Hidden File Filtering System
The ingestion pipeline now includes comprehensive filtering of system files:
- **macOS**: `.DS_Store`, `._*` files, `__MACOSX/` directories
- **Windows**: `Thumbs.db`, `desktop.ini`
- **Version Control**: `.git/`, `.svn/` directories
- **Generic**: All dot files and hidden directories

### Robust Testing
- Automatic test termination on WARNING/ERROR severity logs
- Comprehensive file type detection and statistics
- Hidden file filtering validation
- Detailed processing reports

See [HIDDEN_FILE_FILTERING_IMPLEMENTATION.md](HIDDEN_FILE_FILTERING_IMPLEMENTATION.md) for detailed technical documentation.

## Integration with MCP Servers

This server is designed to work with MCP (Model Context Protocol) servers in the parent directory structure:

```
mcp-servers/
├── file-search-server-v3/     ← This extracted server
├── src/                       ← Other MCP servers (sqlite, etc.)
└── ...
```

The server communicates with external LLM services via MCP protocol for AI-powered metadata generation.

---

**Note:** This is a clean separation of server components from the original FileBrowser project. The Streamlit frontend remains in the original location and can connect to this server via API calls.
