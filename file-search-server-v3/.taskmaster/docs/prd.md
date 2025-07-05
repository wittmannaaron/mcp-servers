# Product Requirements Document: Semantic Search Implementation

## 1. Introduction & Goal

The current system successfully ingests and catalogs documents, enabling metadata and full-text search. The next major step is to enhance the system with semantic search capabilities. This will allow users to find documents based on meaning and context, not just keywords.

The goal is to implement a complete pipeline for chunking, embedding, and storing document content to enable efficient vector-based similarity search.

## 2. Key Features

### 2.1. Database Schema Extension
- **Chunks Table:** A new table `chunks` will be created to store text chunks derived from the `markdown_content` of each document.
    - `id`: INTEGER, PRIMARY KEY
    - `document_id`: INTEGER, FOREIGN KEY to `documents.id`
    - `chunk_index`: INTEGER, position of the chunk within the document
    - `content`: TEXT, the actual chunk text
    - `char_count`: INTEGER
- **Vector Storage:** A new virtual table `chunk_vectors` will be created using the `sqlite-vss` extension for efficient vector similarity search.
    - `rowid`: Corresponds to `chunks.id`
    - `embedding`: BLOB, the vector embedding of the chunk

### 2.2. Context-Aware Chunking Service
- A new service, `src/core/chunking_service.py`, will be created.
- It will implement a context-sensitive chunking strategy for Markdown content.
- It must be able to split text based on semantic boundaries like headers, paragraphs, lists, and code blocks.
- It will expose a function `chunk_text(markdown_text: str) -> List[str]`.

### 2.3. Embedding Service
- A new service, `src/core/embedding_service.py`, will be created.
- It will encapsulate all interactions with the local embedding model.
- It must support batch processing to efficiently create embeddings for multiple text chunks at once.
- It will expose a function `create_embeddings(texts: List[str]) -> List[List[float]]`.

### 2.4. Ingestion Pipeline Integration
- The main ingestion logic in `src/core/ingestion.py` will be modified.
- After a document is successfully stored and its `document_id` is retrieved, the new chunking and embedding process will be triggered.
- The workflow will be:
    1. Get `markdown_content` from the newly stored document.
    2. Pass content to the `Chunking Service`.
    3. Pass the resulting chunks to the `Embedding Service`.
    4. Store each chunk and its corresponding vector embedding in the new database tables.

### 2.5. Semantic Search API
- A new method `search_semantic(query_text: str, limit: int)` will be added to the `DocumentStore` class.
- This method will:
    1. Generate an embedding for the `query_text`.
    2. Perform a vector similarity search against the `chunk_vectors` table.
    3. Return a list of the most relevant documents or chunks.

## 3. Non-Functional Requirements
- **Performance:** The embedding process should be optimized for performance, utilizing batching where possible. Vector search should be fast enough for a responsive user experience.
- **Modularity:** The new services (Chunking, Embedding) must be modular and decoupled from the main ingestion logic to ensure maintainability.
- **Testability:** All new components must be accompanied by unit tests.

## 4. Assumptions
- A local embedding model is available and accessible.
- The `sqlite-vss` extension can be integrated into our SQLite environment. If not, we will need to re-evaluate the vector storage strategy.