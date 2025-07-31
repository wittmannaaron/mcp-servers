# CLAUDE.md - Development Tasks

## Project Overview
Upgrade MCP file search server from basic `getData` functionality to comprehensive document corpus research assistant with advanced search capabilities. Switch from `llama3.2` to custom `catalog-browser` model.

## Current Database Location
**Database Path:** `/Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db`

## Task List

### 1. Model Migration
**Priority: HIGH**
- [ ] Replace all `llama3.2` references with `catalog-browser` across entire codebase
- [ ] Update `mcp_client_terminal.py` model references
- [ ] Update `webkit_real_client.py` model references  
- [ ] Update system prompts and configuration files
- [ ] Test model loading and functionality

### 2. MCP Server Enhancement  
**Priority: HIGH**
- [ ] Implement new search functions in `server.py` per SPECIFICATION.md:
  - `semantic_expression_search(query: string)` - Natural language search
  - `fuzzy_search_person(name: string)` - Person name fuzzy matching
  - `fuzzy_search_place(place: string)` - Place name fuzzy matching  
  - `search_by_date_range(start: date, end: date)` - Date range filtering
  - `search_creation_date(created: date)` - Exact creation date search
  - `search_date_in_document(date: date)` - Date mentioned in content
  - `find_duplicates()` - MD5 hash duplicate detection
  - `get_document_content_by_id(id: integer)` - Full document content retrieval
  - `rank_documents_by_relevance(query: string, doc_ids: array)` - Result ranking
- [ ] Use existing database schema (READ-ONLY access)
- [ ] Reference `Database-Administration-Handbook.md` for SQL implementations
- [ ] Implement tool chaining support for complex searches

### 3. Client Updates
**Priority: MEDIUM**
- [ ] Update `mcp_client_terminal.py` to support new search functions
- [ ] Update `webkit_real_client.py` to support new search functions
- [ ] Maintain existing presentation layer in webkit client (NO UI changes)
- [ ] Implement session state management for progressive search refinement
- [ ] Add German language support for error messages

### 4. System Prompt Enhancement
**Priority: HIGH**
- [ ] Inject available tools into `{DYNAMIC_TOOL_LIST}` placeholder in `system_prompt.txt`
- [ ] Implement runtime tool discovery and prompt injection
- [ ] Test tool chaining scenarios with German queries
- [ ] Validate JSON response format consistency

### 5. Environment & Dependencies
**Priority: MEDIUM**
- [ ] Fix webview installation issue (compilation error on macOS)
- [ ] Update `requirements.txt` to include missing webview dependency
- [ ] Test environment compatibility between different venv setups
- [ ] Verify Python 3.13 compatibility

### 6. Documentation Updates
**Priority: LOW**
- [ ] Replace/update old `CLAUDE.md` with task-focused version
- [ ] Create comprehensive `README.md` with setup instructions
- [ ] Remove redundant `WEBKIT_DEVELOPMENT_GUIDE.md` content
- [ ] Integrate useful webkit information into main documentation

## Implementation Constraints

### Critical Requirements
- **NO database schema changes allowed** - READ-ONLY access only
- **Preserve webkit client presentation layer** - only modify MCP logic
- **German language priority** - optimize for German document corpus
- **Existing database schema** - use tables as documented in `Database-Administration-Handbook.md`

### Success Criteria
- All 9 new search tools implemented and functional
- Tool chaining works for complex German queries
- `catalog-browser` model replaces `llama3.2` completely
- Webkit client maintains full functionality with enhanced search
- No breaking changes to existing working features

## References
- **Database Schema:** `Database-Administration-Handbook.md`
- **Technical Specs:** `SPECIFICATION.md` 
- **Product Requirements:** Document specifications in project root
