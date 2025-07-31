# File Search Server V2 - Local Research Agent

A comprehensive document corpus research assistant using MCP (Model Context Protocol) with advanced search capabilities for German documents.

## Overview

This system enables natural language searches across local document collections using a hybrid approach combining full-text search, fuzzy matching, and semantic analysis. Optimized for German language queries and documents.

## Features

- **9 Specialized Search Tools** - Semantic search, fuzzy matching, date filtering, duplicate detection
- **German Language Optimized** - Handles German queries, names, and places with OCR error correction
- **Tool Chaining** - Complex multi-step searches with progressive refinement
- **Multiple Interfaces** - Terminal client and native macOS WebKit GUI
- **Session Memory** - Maintains search context across conversation turns

## Quick Start

### Prerequisites

- Python 3.13+
- Ollama with `catalog-browser` model
- SQLite database with FTS5 support

### Installation

```bash
# Clone and setup
cd /Users/aaron/Projects/mcp-servers/file-search-server-v2

# Install dependencies
pip install -r requirements.txt

# Create catalog-browser model (see Modelfile-catalog-browser)
ollama create catalog-browser -f ./Modelfile-catalog-browser
```

### Database Setup

The system uses an existing SQLite database at:
```
/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db
```

See `Database-Administration-Handbook.md` for complete schema documentation.

### Running the Application

**Terminal Client:**
```bash
python mcp_client_terminal.py
```

**WebKit GUI Client:**
```bash
python webkit_real_client.py
```

## Architecture

```
German Query → LLM (catalog-browser) → MCP Tools → SQLite Database → Results
     ↓              ↓                      ↓           ↓
  Keywords    Tool Selection         SQL Queries   Document Data
```

### Core Components

- **`server.py`** - MCP server with 9 search tools
- **`mcp_client_terminal.py`** - Terminal interface
- **`webkit_real_client.py`** - Native macOS GUI  
- **`system_prompt.txt`** - LLM prompt with dynamic tool injection
- **`catalog-browser`** - Custom Ollama model for German document search

## Search Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `semantic_expression_search` | Natural language content search | "Middleware Architektur" |
| `fuzzy_search_person` | Person name matching with OCR errors | "Muller" → "Müller" |
| `fuzzy_search_place` | Place name matching with variations | "Munchen" → "München" |
| `search_by_date_range` | Filter by creation date range | 2023-01-01 to 2023-12-31 |
| `search_creation_date` | Exact creation date match | 2024-03-15 |
| `search_date_in_document` | Find dates mentioned in content | References to specific dates |
| `find_duplicates` | Identify duplicate files by MD5 | Duplicate content detection |
| `get_document_content_by_id` | Retrieve full document content | Complete document text |
| `rank_documents_by_relevance` | Sort results by relevance | Relevance-based ranking |

## Usage Examples

**Simple Search:**
```
User: "Finde BMW Dokumente"
→ semantic_expression_search("BMW")
```

**Complex Multi-Tool Search:**
```
User: "Suche Middleware-Dokumente aus München von Herrn Müller aus 2023"
→ semantic_expression_search("Middleware")
→ fuzzy_search_place("München")  
→ fuzzy_search_person("Müller")
→ search_by_date_range("2023-01-01", "2023-12-31")
→ rank_documents_by_relevance(query, doc_ids)
```

## Configuration

### Environment Dependencies

The system requires specific Python packages that may have platform-specific issues:

```txt
requests>=2.31.0
fastmcp>=2.9.0
mcp>=1.9.4
webview  # Note: May require compilation on macOS
```

**WebView Issue:** If `webview` installation fails on macOS, use the working environment from:
```bash
source ~/Projects/mcp-servers/file-search-server/venv/bin/activate
```

### Model Configuration

The system uses a custom `catalog-browser` model based on Llama3.2:3B with optimized German language processing. See `Modelfile-catalog-browser` for complete configuration.

## Development

### Adding New Search Tools

1. Define tool in `server.py` using `@mcp.tool()` decorator
2. Add JSON specification to `SPECIFICATION.md`
3. Update `system_prompt.txt` dynamic tool list
4. Test with both terminal and webkit clients

### Database Schema

All database operations are **READ-ONLY**. The system uses existing tables:

- `documents` - Main document metadata
- `chunks` - Document chunks for semantic search
- `persons_fuzzy` / `places_fuzzy` - Fuzzy matching tables  
- `documents_fts` - Full-text search index

See `Database-Administration-Handbook.md` for complete schema reference.

## Troubleshooting

**Common Issues:**

- **webview compilation errors**: Use existing working venv or install platform-specific binaries  
- **Ollama connection fails**: Ensure Ollama is running on localhost:11434
- **catalog-browser model not found**: Create model using provided Modelfile
- **Database locked**: Ensure no other processes are accessing the SQLite file

## Documentation

- **`CLAUDE.md`** - Development task specifications
- **`SPECIFICATION.md`** - Complete technical specification  
- **`Database-Administration-Handbook.md`** - Database schema and SQL reference
- **`system_prompt.txt`** - LLM system prompt with tool integration

## Status

**Current Version:** 2.0 (In Development)  
**Previous Version:** 1.0 (WebKit client completed)  
**Target:** Advanced multi-tool search with German language optimization

---

*For detailed development instructions and task specifications, see `CLAUDE.md`*
