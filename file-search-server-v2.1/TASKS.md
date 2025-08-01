# TASKS.md - Implementation Tasks for Document Research Agent

## Status: Phase 1 Complete ✅
- [x] Basic chat functionality with LLM keyword extraction
- [x] FTS5 search integration 
- [x] Flask backend with CORS
- [x] React frontend basic structure

## Phase 2: Enhanced UI/UX 🔄

### 2.1 Table Layout Implementation (Priority: HIGH)
- [ ] **Replace current result display with HTML table format specified:**
  ```
  | creation date | filename  |
  |---------------------------|
  |      file path            |  
  |---------------------------|
  | truncated markdown content|
  ```
- [ ] Format creation dates properly (DD.MM.YYYY)
- [ ] Truncate markdown content to 300 characters
- [ ] Add CSS styling for professional table appearance
- [ ] Make table responsive for different screen sizes

### 2.2 Sorting and Filtering
- [ ] **Implement sorting options:**
  - [ ] By relevance (default)
  - [ ] By name (alphabetical)
  - [ ] By date (chronological)
- [ ] Add sort controls to UI
- [ ] Maintain sort state during session
- [ ] Update backend to support different sort orders

## Phase 3: Advanced Search Tools 🔧

### 3.1 Database Schema Verification
- [ ] **Read and analyze Database-Administration-Handbook.md**
- [ ] **Connect to database and verify all required tables exist:**
  - [ ] documents table with all fields
  - [ ] chunks table for semantic search
  - [ ] chunk_vectors table for embeddings
  - [ ] persons_fuzzy table for fuzzy person matching
  - [ ] places_fuzzy table for fuzzy place matching
  - [ ] documents_fts virtual table

### 3.2 Implement Required Search Functions
- [ ] **semantic_expression_search**
  - [ ] Use chunk_vectors table for semantic matching
  - [ ] Implement embedding-based similarity search
  - [ ] Support German language semantic queries

- [ ] **fuzzy_search_person**
  - [ ] Use persons_fuzzy table with soundex matching
  - [ ] Handle German names and umlauts
  - [ ] Support variations like "Herrn Müller" vs "Herr Müller"

- [ ] **fuzzy_search_place**
  - [ ] Use places_fuzzy table with soundex matching
  - [ ] Handle German place names and variations
  - [ ] Support OCR error correction

- [ ] **search_by_date_range**
  - [ ] Parse German date formats
  - [ ] Query created_at field with date range
  - [ ] Validate date inputs

- [ ] **search_creation_date**
  - [ ] Find documents created on specific date
  - [ ] Support multiple date format inputs

- [ ] **search_date_in_document**
  - [ ] Search mentioned_dates field
  - [ ] Parse German date formats in content
  - [ ] Handle DD-MM-YYYY format

- [ ] **find_duplicates**
  - [ ] Group by md5_hash to find identical content
  - [ ] Return duplicate groups with metadata

- [ ] **get_document_content_by_id**
  - [ ] Return full markdown_content by document ID
  - [ ] Handle missing documents gracefully

- [ ] **rank_documents_by_relevance**
  - [ ] Implement relevance scoring algorithm
  - [ ] Consider keyword matches, recency, document type

### 3.3 Multi-Step Search Integration
- [ ] **Tool chaining system:**
  - [ ] Allow combining multiple search functions
  - [ ] Maintain intermediate results in session
  - [ ] Support up to 5 tools per query
  - [ ] Handle tool failures gracefully

- [ ] **Session memory:**
  - [ ] Store search results across conversation turns
  - [ ] Allow refinement of previous searches
  - [ ] Implement drill-down capabilities

## Phase 4: German Language Optimization 🇩🇪

### 4.1 Enhanced LLM Integration  
- [ ] **Improve keyword extraction:**
  - [ ] Better handling of German grammar patterns
  - [ ] Extract persons, places, dates accurately
  - [ ] Translate user requests to English internally for LLM

- [ ] **Error messages in German:**
  - [ ] Missing parameters
  - [ ] No results found with suggestions
  - [ ] Database connection issues

### 4.2 Fuzzy Matching for OCR Errors
- [ ] **Name variations:**
  - [ ] Handle umlauts (ü, ö, ä, ß)
  - [ ] OCR misinterpretations (rn->m, cl->d)
  - [ ] Title variations (Herr/Herrn)

- [ ] **Place name variations:**
  - [ ] German city name alternatives
  - [ ] Regional spelling differences
  - [ ] OCR common errors

## Phase 5: Performance and UX Enhancements ⚡

### 5.1 Performance Optimization
- [ ] **Response time targets:**
  - [ ] < 2 seconds per search tool
  - [ ] Optimize database queries
  - [ ] Add query result caching

- [ ] **Memory management:**
  - [ ] Keep total usage < 500MB
  - [ ] Efficient session storage
  - [ ] Cleanup old search results

### 5.2 Advanced UI Features
- [ ] **Copy/paste functionality:**
  - [ ] Copy search results to clipboard
  - [ ] Paste text into search field
  - [ ] Export results to files

- [ ] **Progressive search refinement:**
  - [ ] Filter existing results
  - [ ] Combine search criteria
  - [ ] Save/load search sessions

### 5.3 Real-time Updates
- [ ] **Index management:**
  - [ ] Update search index on startup
  - [ ] Periodic FTS5 updates (every 10 minutes)
  - [ ] Background index refresh

## Phase 6: Testing and Validation 🧪

### 6.1 Test Query Implementation
- [ ] **Implement test scenarios:**
  - [ ] "Finde Dokumente über den BMW von Herrn Ihring"
  - [ ] "Suche nach Middleware-Dokumenten aus München"  
  - [ ] "Zeige mir alle Dateien aus 2023 über Hausbegehungen"
  - [ ] "Welche Duplikate gibt es in der Datenbank?"
  - [ ] "Zeige den Inhalt von Dokument <filename>"

### 6.2 Tool Chaining Tests
- [ ] **Complex scenarios:**
  - [ ] Multi-step search with person, place, and date filters
  - [ ] Progressive refinement across conversation turns
  - [ ] Error recovery when tools return no results
  - [ ] Session state persistence

### 6.3 Performance Testing
- [ ] **Measure and optimize:**
  - [ ] Search response times
  - [ ] Memory usage monitoring
  - [ ] Result accuracy validation (>90% relevant)

## Phase 7: Deployment and Packaging 📦

### 7.1 MacOS Integration
- [ ] **Choose deployment strategy:**
  - [ ] Web app with local server
  - [ ] Electron app wrapper
  - [ ] Native Swift application
  - [ ] Progressive Web App (PWA)

### 7.2 Application Bundling
- [ ] **Package for MacOS:**
  - [ ] Include all dependencies
  - [ ] Create application icon
  - [ ] Setup installer/DMG
  - [ ] Test on clean MacOS system

---

## Current Priority: Phase 2.1 - Table Layout Implementation

**Next Task:** Implement the specified HTML table format for search results display with proper styling and responsive design.