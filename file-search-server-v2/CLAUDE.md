# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) File Search Server V2 that provides document search capabilities for local user files using Full-Text Search (FTS). The system is now at **Ground Zero** - a stable, working baseline for ongoing development.

## Architecture

### Core Components

- **server.py**: Minimal FastMCP-based server with two search tools
- **mcp_client_terminal.py**: Terminal client using Ollama llama3.2 with proper Llama 3.2 function calling
- **system_prompt.txt**: Llama 3.2 compatible system prompt for function calling
- **SPECIFICATION.md**: Technical specification for future extensions
- **tests/**: Directory containing keyword extraction and prompt testing utilities

### Database Structure

The system uses SQLite with these key tables:
- `documents`: Main table with 88 indexed documents containing rich metadata
- `documents_fts_extended`: FTS5 virtual table for full-text search
- `persons_fuzzy`, `places_fuzzy`: Fuzzy matching tables (implemented but not currently used)

Database location: `/Users/aaron/Projects/Simple_MCP_DB/filebrowser.db`

## Current Status (Ground Zero)

### ✅ Implemented and Working
- **FTS Search**: Returns up to 5 results using exact SQL query
- **Keyword Extraction**: LLM extracts search terms from German queries with 100% success rate
- **Llama 3.2 Function Calling**: Proper format `[getData(search_terms=['Ihring'])]`
- **MCP Communication**: Stable client-server communication 
- **Real Data**: Returns actual database content when found

### 🔧 Currently Active Tools
1. `getData(search_terms)` - FTS search returning up to 5 results
2. `get_database_stats()` - Database statistics

## Development Commands

### Running the System
```bash
# Start terminal client (auto-starts server)
python mcp_client_terminal.py
```

### Testing
```bash
# Test keyword extraction with different prompts
python tests/test_keyword_extraction.py
python tests/test_refined_prompts.py
```

### Dependencies
- **Ollama**: localhost:11434 with llama3.2:latest 
- **Python**: mcp.server.fastmcp, sqlite3, requests
- **SQLite**: FTS5 extensions enabled

## Code Architecture

### Search Flow
```
German Query → LLM Keyword Extraction → MCP getData() → SQLite FTS → Results
```

### Function Calling Format
```python
# LLM Response Format (Llama 3.2)
[getData(search_terms=['Ihring', 'BMW'])]

# Server Implementation  
@mcp.tool()
async def getData(search_terms: List[str]) -> List[Dict[str, Any]]:
    # Returns up to 5 results from FTS search
```

## Keyword Extraction

Uses proven prompt achieving 100% success rate:
```
"Bitte liste alle Dateien auf, die das Wort Ihring beinhalten" → Ihring
"Finde Dateien über BMW" → BMW  
"Suche nach Dokumenten mit Anke oder Familie" → Anke, Familie
```

## Next Development Phases

1. **Dynamic Search Terms**: ✅ Completed - uses extracted keywords instead of hardcoded 'Ihring'
2. **Fuzzy Search Integration**: Re-enable existing fuzzy tables for person/place matching
3. **Vector Search**: Add semantic search capabilities
4. **Advanced Features**: Multi-mode search ranking, filters, etc.

## Testing Strategy

Test files in `tests/` directory verify:
- Keyword extraction accuracy across different German sentence patterns
- Function calling format compliance
- LLM prompt effectiveness

## Important Notes

- **German Language**: System optimized for German queries and responses
- **Local Files**: Searches user's local document collection only
- **Minimal Core**: Current implementation is intentionally minimal and stable
- **Debug Output**: Extensive logging for development and troubleshooting
- **Data Integrity**: Returns real database content when found; may hallucinate when no results found (minor issue for future improvement)

This is the stable foundation for all future development.