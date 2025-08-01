# SPECIFICATION.md - Local Research Agent for Document Corpus

**Version:** 2.1  
**Target:** Llama3.2:3B via custom `catalog-browser` model  
**Language:** German input/content, English system instructions  
**Database:** `/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db` (READ-ONLY)

## Overview
Technical specification for catalog-client, a comprehensive document research assistant with specialized search tools.
The client must be a graphical client, preferred is webkit.
The results must be presented in a HTML-Interface. Following Data must be available: creation date, filename, file path, first 300 chars from markdown content. These informations must be arranged in a table like the following example:

| creation date | filename  |
|---------------------------|
|      file path            |
|---------------------------|
| truncated markdown content|

That means in the first	row we have two columns, in the second and third row we have one column.

Allow user to chat with the system in natural language, but the system's main purpose is to find data in database. The system should communicate in natural language, either by answering a simple question or if something went wrong. The system should support the user by providing search hints if a search doesn't return a result. The system must be able to keep search results in his chat memory as long as the user keeps the session open, so it will support the user to refine existing search results, allowing a drill down to a specific file with a specific pattern.
The GUI should allow to sort the results, either by name, date, relevance. Default should be relevance.

The goal of this client is to run on MacOS. Ideally the application integrates with MacOS as an app or at least as a web app. We have python, go/golang, node, installed on the system. Swift applications also work on this system. You can also use react, type script, CSS, HTML, as long as it will fit and allows us to bundle the application into a MacOS-App.

The underlying LLM is a Llama3.2:3B. It uses a customized Modelfile, this is why you find it in ollama service as catalog-browser:latest. Use the name catalog-browser:latest for local Ollama LLM Service. When you write functions for your tools always keep in mind that we use only a smaller Model and sqlite allows only one SQL-Statement at a time. So you need to find a way how you like to handle intermediate results from steps during processing a tool-chain.


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
Read details in `Database-Administration-Handbook.md`:

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

Use sqlite to confirm the database access and the database schema, before you start coding.

## Reqired search capabilities:

Name				Description
semantic_expression_search	Searches documents based on semantic expression in natural language (German).
fuzzy_search_person		Finds documents mentioning person with phonetically similar names (German input).
fuzzy_search_place		Finds documents mentioning places with similar sounding names (German input).
search_by_date_range		Finds documents created between two dates (YYYY-MM-DD).
search_creation_date		Finds documents created on specific date (YYYY-MM-DD).
search_date_in_document		Finds documents mentioning specific date in content (DD-MM-YYYY).
find_duplicates			Returns list of files with identical content (based on MD5 hash).
get_document_content_by_id	Returns full markdown content of document by ID.
rank_documents_by_relevance	Ranks list of documents based on relevance to query.


### German Language Optimization
- Write all prompts, comments, documentations in English. But all data input and output will be in German, the documents stored in database are in German as well. If you like to describe examples, then use examples in German.
- Tell the LLM ist should always internally translate the users requests into English to double check the request was understood properly.
- Tell the LLM to xxtract German keywords accurately.
- Handle German grammar patterns (e.g., "Herrn Müller", "von 2023")
- Use Fuzzy for names or place with umlaut.
- Use Fuzzy and semantic if you can't get a perfect match for search request.
- Provide German error messages for missing parameters
- Support German date formats and place names
- Names, Places, Words in documents can be wrong due to OCR misinterpretation.

## Implementation Requirements

### Database Access
- **READ-ONLY** operations only
- Use existing schema without modifications
- Reference `Database-Administration-Handbook.md` for table structures
- Handle NULL values gracefully in queries

### Model Integration
- Use local running ollama model named `catalog-browser`
- Support tool chaining through session management
- Maintain JSON response format consistency

### Client Compatibility
- Add German language support for error handling
- Add copy and paste functionality
- Implement progressive search refinement, like sorting the result for date oor relevance

## Performance Targets
- **Search Response Time:** < 2 seconds per tool
- **Tool Chaining:** Support up to 5 tools per query
- **Result Accuracy:** > 90% relevant results for German queries
- **Memory Usage:** < 500MB for client + server

## Enhancements
- **Vector Search:** Add semantic similarity using embedding vectors
- **Advanced Ranking:** Machine learning-based relevance scoring
- **Real-time Updates:** update search index every time the program got started, after start do all 10 minutes an index update and trigger updating fts5
- **Export and Import Functions:** Save search results to files or external systems, allow pasting text into the search field.

## Testing Scenarios

### German Query Patterns
test_queries = [
    "Finde Dokumente über den BMW von Herrn Ihring",
    "Suche nach Middleware-Dokumenten aus München",
    "Zeige mir alle Dateien aus 2023 über Hausbegehungen",
    "Welche Duplikate gibt es in der Datenbank?",
    "Zeige den Inhalt von Dokument <filename>"
]


### Tool Chaining Tests
complex_scenarios = [
    "Multi-step search with person, place, and date filters",
    "Progressive refinement across multiple conversation turns", 
    "Error recovery when some tools return no results",
    "Session state persistence during long conversations"
]


## Error Handling
- **Missing Parameters:** German error messages requesting required information
- **No Results Found:** Suggest alternative search terms or broader criteria
- **Database Errors:** Graceful fallback to simpler queries
- **Tool Chaining Failures:** Continue with partial results, report issues



