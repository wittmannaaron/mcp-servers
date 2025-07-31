# SPECIFICATION.md - Local Research Agent for Document Corpus

## Overview
Technical specification for upgrading MCP file search server to comprehensive document research assistant with 9 specialized search tools.

**Version:** 2.0  
**Target:** Llama3.2:3B via custom `catalog-browser` model  
**Language:** German input/content, English system instructions  
**Database:** `/Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db` (READ-ONLY)

## Core Capabilities

| Feature | Description |
|---------|-------------|
| Natural Language Queries | German queries with intelligent keyword extraction |
| Multi-Step Search | Tool chaining for complex searches |
| Fuzzy Matching | OCR error correction for names and places |
| Semantic Search | Expression-based content matching |
| Date Filtering | Creation dates and mentioned dates |
| Duplicate Detection | MD5 hash-based duplicate finding |
| Result Ranking | Relevance-based result ordering |
| Session Memory | Progressive search refinement across turns |

## Database Schema (Existing)

### Core Tables
Based on `Database-Administration-Handbook.md`:

```sql
-- Main document table
documents (
    id, uuid, file_path, filename, extension, size, mime_type, md5_hash,
    original_text, markdown_content, summary, document_type, categories,
    entities, persons, places, mentioned_dates, file_references,
    created_at, updated_at, indexed_at
)

-- Document chunks for semantic search
chunks (
    id, document_id, chunk_index, content, char_count
)

-- Embedding vectors for semantic matching
chunk_vectors (
    id, chunk_id, embedding_json
)

-- Fuzzy matching tables
persons_fuzzy (
    id, document_id, original_name, soundex_code, normalized_name
)

places_fuzzy (
    id, document_id, original_place, soundex_code, normalized_place
)

-- FTS5 full-text search
documents_fts (virtual table with FTS5 tokenization)
```

## MCP Tool Specifications

### 1. semantic_expression_search
```json
{
  "name": "semantic_expression_search",
  "description": "Searches documents based on semantic expression in natural language (German).",
  "parameters": {
    "query": {
      "type": "string",
      "description": "Natural language expression or topic, e.g. 'Fusion Middleware Architektur'"
    }
  }
}
```
**Implementation:** FTS5 search across `original_text`, `markdown_content`, `summary` fields.

### 2. fuzzy_search_person
```json
{
  "name": "fuzzy_search_person", 
  "description": "Finds documents mentioning person with phonetically similar names (German input).",
  "parameters": {
    "name": {
      "type": "string",
      "description": "Person name, possibly with OCR errors (e.g. 'Muller' for 'Müller')"
    }
  }
}
```
**Implementation:** Query `persons_fuzzy` table using soundex codes and normalized names.

### 3. fuzzy_search_place
```json
{
  "name": "fuzzy_search_place",
  "description": "Finds documents mentioning places with similar sounding names (German input).",
  "parameters": {
    "place": {
      "type": "string", 
      "description": "Place name with possible spelling variation (e.g. 'Munchen' for 'München')"
    }
  }
}
```
**Implementation:** Query `places_fuzzy` table using soundex codes and normalized places.

### 4. search_by_date_range
```json
{
  "name": "search_by_date_range",
  "description": "Finds documents created between two dates (YYYY-MM-DD).",
  "parameters": {
    "start": {
      "type": "string",
      "format": "date",
      "description": "Start date of range"
    },
    "end": {
      "type": "string", 
      "format": "date",
      "description": "End date of range"
    }
  }
}
```
**Implementation:** Filter `documents.created_at` between start and end dates.

### 5. search_creation_date
```json
{
  "name": "search_creation_date",
  "description": "Finds documents created on specific date (YYYY-MM-DD).",
  "parameters": {
    "created": {
      "type": "string",
      "format": "date", 
      "description": "Date when document was created"
    }
  }
}
```
**Implementation:** Exact match on `documents.created_at` date component.

### 6. search_date_in_document
```json
{
  "name": "search_date_in_document",
  "description": "Finds documents mentioning specific date in content (YYYY-MM-DD).",
  "parameters": {
    "date": {
      "type": "string",
      "format": "date",
      "description": "Specific date mentioned in document content"
    }
  }
}
```
**Implementation:** Search `mentioned_dates` JSON field and content for date references.

### 7. find_duplicates
```json
{
  "name": "find_duplicates",
  "description": "Returns list of files with identical content (based on MD5 hash).",
  "parameters": {}
}
```
**Implementation:** Group by `md5_hash` where count > 1.

### 8. get_document_content_by_id
```json
{
  "name": "get_document_content_by_id",
  "description": "Returns full markdown content of document by ID.",
  "parameters": {
    "id": {
      "type": "integer",
      "description": "Internal document ID"
    }
  }
}
```
**Implementation:** Direct SELECT from `documents` table by ID.

### 9. rank_documents_by_relevance
```json
{
  "name": "rank_documents_by_relevance", 
  "description": "Ranks list of documents based on relevance to query.",
  "parameters": {
    "query": {
      "type": "string",
      "description": "Search query for relevance ranking"
    },
    "doc_ids": {
      "type": "array",
      "items": {"type": "integer"},
      "description": "List of document IDs to rank"
    }
  }
}
```
**Implementation:** FTS5 ranking or embedding similarity scoring.

## Tool Chaining Patterns

### Progressive Search Refinement
```
User: "Ich suche etwas über Middleware in München mit Herrn Müller von 2023."

Tool Chain:
1. semantic_expression_search("Middleware") → get initial matches
2. fuzzy_search_place("München") → filter by location  
3. fuzzy_search_person("Müller") → filter by person
4. search_by_date_range("2023-01-01", "2023-12-31") → apply date filter
5. rank_documents_by_relevance("Middleware München Müller", doc_ids) → final ranking
```

### Session State Management
Track filters across conversation turns:
```json
{
  "active_filters": {
    "persons": ["Müller"],
    "places": ["München"], 
    "date_range": ["2023-01-01", "2023-12-31"],
    "keywords": ["Middleware"]
  },
  "last_result_ids": [12, 17, 19]
}
```

## System Prompt Integration

### Dynamic Tool List Injection
Replace `{DYNAMIC_TOOL_LIST}` in `system_prompt.txt` with runtime tool discovery:

```python
def inject_tools_into_prompt(system_prompt: str, available_tools: list) -> str:
    tool_descriptions = []
    for tool in available_tools:
        tool_descriptions.append(f"- {tool['name']}: {tool['description']}")
    
    tools_text = "\n".join(tool_descriptions)
    return system_prompt.replace("{DYNAMIC_TOOL_LIST}", tools_text)
```

### German Language Optimization
- Extract German keywords accurately
- Handle German grammar patterns (e.g., "Herrn Müller", "von 2023")
- Provide German error messages for missing parameters
- Support German date formats and place names

## Implementation Requirements

### Database Access
- **READ-ONLY** operations only
- Use existing schema without modifications
- Reference `Database-Administration-Handbook.md` for table structures
- Handle NULL values gracefully in queries

### Model Integration
- Replace all `llama3.2` references with `catalog-browser`
- Use custom modelfile with German language optimization
- Support tool chaining through session management
- Maintain JSON response format consistency

### Client Compatibility
- Support both terminal (`mcp_client_terminal.py`) and webkit (`webkit_real_client.py`) clients
- Preserve existing webkit UI/UX
- Add German language support for error handling
- Implement progressive search refinement

## Performance Targets

- **Search Response Time:** < 2 seconds per tool
- **Tool Chaining:** Support up to 5 tools per query
- **Result Accuracy:** > 90% relevant results for German queries
- **Memory Usage:** < 500MB for client + server
- **Concurrent Users:** Support 10+ simultaneous sessions

## Testing Scenarios

### German Query Patterns
```python
test_queries = [
    "Finde Dokumente über BMW von Herrn Ihring",
    "Suche nach Middleware-Dokumenten aus München",
    "Zeige mir alle Dateien aus 2023 über Hausbegehungen",
    "Welche Duplikate gibt es in der Datenbank?",
    "Lade den vollständigen Inhalt von Dokument 15"
]
```

### Tool Chaining Tests
```python
complex_scenarios = [
    "Multi-step search with person, place, and date filters",
    "Progressive refinement across multiple conversation turns", 
    "Error recovery when some tools return no results",
    "Session state persistence during long conversations"
]
```

## Error Handling

- **Missing Parameters:** German error messages requesting required information
- **No Results Found:** Suggest alternative search terms or broader criteria
- **Database Errors:** Graceful fallback to simpler queries
- **Tool Chaining Failures:** Continue with partial results, report issues

## Future Enhancements

- **Vector Search:** Add semantic similarity using embedding vectors
- **Advanced Ranking:** Machine learning-based relevance scoring
- **Real-time Updates:** Watch for new documents and update search index
- **Export Functions:** Save search results to files or external systems
