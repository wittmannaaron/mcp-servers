# CLAUDE.md - Development Tasks

## Project Overview
Upgrade MCP file search server from basic `getData` functionality to comprehensive document corpus research assistant with advanced search capabilities. Switch from `llama3.2` to custom `catalog-browser` model.

## Current Database Location
**Database Path:** `/Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db`

## ⚠️ CRITICAL DATABASE ISSUES FOUND

### **Priority 1: Database Schema Inconsistencies**
- [ ] **FTS5 table missing**: Verify which FTS table exists (`documents_fts` vs `documents_fts_extended`)
- [ ] **Fuzzy tables missing**: `persons_fuzzy` and `places_fuzzy` tables don't exist
- [ ] **Add database initialization**: Server must check/create missing tables on startup
- [ ] **Data migration required**: Populate fuzzy tables from existing 88 documents in `documents.persons` and `documents.places` JSON fields

### **Database Schema Check Required:**
```sql
-- Check actual table existence:
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

-- Check FTS table structure:
PRAGMA table_info(documents_fts);  -- or documents_fts_extended?

-- Verify data population:
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM persons_fuzzy;  -- Likely 0
SELECT COUNT(*) FROM places_fuzzy;   -- Likely 0
```

## Task List

### 1. Model Migration
**Priority: HIGH**
- [ ] Replace all `llama3.2` references with `catalog-browser` across entire codebase
- [ ] Update `mcp_client_terminal.py` model references
- [ ] Update `webkit_real_client.py` model references  
- [ ] Update system prompts and configuration files
- [ ] Test model loading and functionality

### 2. Database Schema Fix (NEW - CRITICAL)
**Priority: URGENT**
- [ ] **Verify existing database schema** against `Database-Administration-Handbook.md`
- [ ] **Create missing fuzzy tables** (`persons_fuzzy`, `places_fuzzy`) with proper structure
- [ ] **Create missing FTS5 table** if not present
- [ ] **Add database initialization function** to `server.py` startup
- [ ] **Implement data migration** to populate fuzzy tables from existing JSON fields
- [ ] **Add proper indexes** for performance (soundex, normalized names)

### 3. MCP Server Enhancement  
**Priority: HIGH** (After database fix)
- [ ] **Fix fuzzy search tools** to work with properly created tables
- [ ] Implement remaining search functions in `server.py` per SPECIFICATION.md:
  - ✅ `semantic_expression_search(query: string)` - Already implemented (needs FTS fix)
  - ✅ `fuzzy_search_person(name: string)` - Implemented but needs table creation
  - ✅ `fuzzy_search_place(place: string)` - Implemented but needs table creation
  - ✅ `search_by_date_range(start: date, end: date)` - Already implemented
  - ✅ `search_creation_date(created: date)` - Already implemented
  - ✅ `search_date_in_document(date: date)` - Already implemented
  - ✅ `find_duplicates()` - Already implemented
  - ✅ `get_document_content_by_id(id: integer)` - Already implemented
  - ✅ `rank_documents_by_relevance(query: string, doc_ids: array)` - Already implemented
- [ ] Use existing database schema (READ-ONLY access)
- [ ] Reference `Database-Administration-Handbook.md` for SQL implementations
- [ ] Implement tool chaining support for complex searches

### 4. Client Updates
**Priority: MEDIUM**
- [ ] Update `mcp_client_terminal.py` to support new search functions
- [ ] Update `webkit_real_client.py` to support new search functions
- [ ] Maintain existing presentation layer in webkit client (NO UI changes)
- [ ] Implement session state management for progressive search refinement
- [ ] Add German language support for error messages

### 5. System Prompt Enhancement
**Priority: HIGH**
- [ ] Inject available tools into `{DYNAMIC_TOOL_LIST}` placeholder in `system_prompt.txt`
- [ ] Implement runtime tool discovery and prompt injection
- [ ] Test tool chaining scenarios with German queries
- [ ] Validate JSON response format consistency

### 6. Environment & Dependencies
**Priority: MEDIUM**
- [ ] Fix webview installation issue (compilation error on macOS)
- [ ] Update `requirements.txt` to include missing webview dependency
- [ ] Test environment compatibility between different venv setups
- [ ] Verify Python 3.13 compatibility

### 7. Documentation Updates
**Priority: LOW**
- [ ] Replace/update old `CLAUDE.md` with task-focused version
- [ ] Create comprehensive `README.md` with setup instructions
- [ ] Remove redundant `WEBKIT_DEVELOPMENT_GUIDE.md` content
- [ ] Integrate useful webkit information into main documentation

## Implementation Constraints

### Critical Requirements
- **NO database schema changes allowed** - READ-ONLY access only
- **Exception: Create missing tables** - fuzzy tables don't exist yet, must be created
- **Preserve webkit client presentation layer** - only modify MCP logic
- **German language priority** - optimize for German document corpus
- **Existing database schema** - use tables as documented in `Database-Administration-Handbook.md`

### Database Initialization Strategy
```python
# Add to server.py startup:
def initialize_database():
    """Create missing tables and populate from existing data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Check if fuzzy tables exist
    # 2. Create missing tables with proper structure
    # 3. Migrate data from documents.persons/places JSON fields
    # 4. Create indexes for performance
    # 5. Verify FTS5 table exists and is populated
```

### Success Criteria
- All 9 search tools implemented and functional
- Fuzzy tables properly created and populated
- FTS5 search working correctly
- Tool chaining works for complex German queries
- `catalog-browser` model replaces `llama3.2` completely
- Webkit client maintains full functionality with enhanced search
- No breaking changes to existing working features

## Debugging Commands

### Database Schema Verification
```bash
# Check actual database structure
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

# Check fuzzy tables exist
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT COUNT(*) FROM persons_fuzzy;"

# Check FTS table
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT COUNT(*) FROM documents_fts;"

# Sample data from documents.persons field
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT id, filename, persons FROM documents WHERE persons IS NOT NULL LIMIT 5;"
```

## References
- **Database Schema:** `Database-Administration-Handbook.md`
- **Technical Specs:** `SPECIFICATION.md` 
- **Product Requirements:** Document specifications in project root
