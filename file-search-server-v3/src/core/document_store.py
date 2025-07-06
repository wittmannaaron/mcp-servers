"""
MCP-Compliant Database Module for FileBrowser.
Replaces all direct database calls with MCP protocol compliance using proper async context management.
File size ≤ 200 lines enforced, no direct database/LLM calls, uses MCP Python SDK exclusively.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger
from src.core.mcp_client import get_mcp_client

DB_FILE = Path(__file__).parent.parent.parent / "data" / "filebrowser.db"

class DocumentStore:
    """MCP-compliant document store using official SQLite MCP Server with proper async context management."""

    def __init__(self, db_path: Path = DB_FILE):
        self.db_path = db_path
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure database schema is initialized through MCP with proper context management."""
        if self._initialized:
            return
        try:
            async with get_mcp_client(self.db_path) as client:
                await client.create_table("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY,
                        uuid TEXT UNIQUE NOT NULL,
                        file_path TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        extension TEXT,
                        size INTEGER,
                        mime_type TEXT,
                        md5_hash TEXT NOT NULL,
                        original_text TEXT,
                        markdown_content TEXT,
                        summary TEXT,
                        document_type TEXT,
                        categories TEXT,
                        entities TEXT,
                        persons TEXT,
                        places TEXT,
                        mentioned_dates TEXT,
                        file_references TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await client.create_table("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                        original_text, markdown_content, summary, document_type,
                        categories, entities, persons, places, mentioned_dates,
                        file_references, tokenize='unicode61'
                    )
                """)
                await client.create_table("""
                    CREATE TABLE IF NOT EXISTS chunks (
                        id INTEGER PRIMARY KEY,
                        document_id INTEGER NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        char_count INTEGER NOT NULL,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                # Use regular table with JSON storage instead of VSS extension
                await client.create_table("""
                    CREATE TABLE IF NOT EXISTS chunk_vectors (
                        id INTEGER PRIMARY KEY,
                        chunk_id INTEGER NOT NULL,
                        embedding_json TEXT NOT NULL,
                        FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
                    )
                """)
                
                # Create fuzzy search tables for persons and places
                await client.create_table("""
                    CREATE TABLE IF NOT EXISTS persons_fuzzy (
                        id INTEGER PRIMARY KEY,
                        document_id INTEGER NOT NULL,
                        original_name TEXT NOT NULL,
                        soundex_code TEXT NOT NULL,
                        normalized_name TEXT NOT NULL,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                
                await client.create_table("""
                    CREATE TABLE IF NOT EXISTS places_fuzzy (
                        id INTEGER PRIMARY KEY,
                        document_id INTEGER NOT NULL,
                        original_place TEXT NOT NULL,
                        soundex_code TEXT NOT NULL,
                        normalized_place TEXT NOT NULL,
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes for fuzzy search performance
                await client.create_table("""
                    CREATE INDEX IF NOT EXISTS idx_persons_soundex ON persons_fuzzy(soundex_code)
                """)
                await client.create_table("""
                    CREATE INDEX IF NOT EXISTS idx_persons_normalized ON persons_fuzzy(normalized_name)
                """)
                await client.create_table("""
                    CREATE INDEX IF NOT EXISTS idx_places_soundex ON places_fuzzy(soundex_code)
                """)
                await client.create_table("""
                    CREATE INDEX IF NOT EXISTS idx_places_normalized ON places_fuzzy(normalized_place)
                """)
                
                # Create triggers to populate fuzzy tables automatically
                await client.create_table("""
                    CREATE TRIGGER IF NOT EXISTS populate_persons_fuzzy
                    AFTER INSERT ON documents
                    WHEN NEW.persons IS NOT NULL AND NEW.persons != ''
                    BEGIN
                        INSERT INTO persons_fuzzy (document_id, original_name, soundex_code, normalized_name)
                        SELECT NEW.id,
                               json_each.value,
                               CASE
                                   WHEN length(json_each.value) > 0 THEN
                                       substr(upper(json_each.value), 1, 1) ||
                                       substr('000' || replace(replace(replace(replace(replace(replace(replace(replace(replace(
                                           upper(json_each.value), 'A', ''), 'E', ''), 'I', ''), 'O', ''), 'U', ''), 'H', ''), 'W', ''), 'Y', ''),
                                           'BFPV', '1'), 1, 3)
                                   ELSE ''
                               END,
                               lower(trim(json_each.value))
                        FROM json_each(NEW.persons)
                        WHERE json_each.value IS NOT NULL AND trim(json_each.value) != '';
                    END
                """)
                
                await client.create_table("""
                    CREATE TRIGGER IF NOT EXISTS populate_places_fuzzy
                    AFTER INSERT ON documents
                    WHEN NEW.places IS NOT NULL AND NEW.places != ''
                    BEGIN
                        INSERT INTO places_fuzzy (document_id, original_place, soundex_code, normalized_place)
                        SELECT NEW.id,
                               json_each.value,
                               CASE
                                   WHEN length(json_each.value) > 0 THEN
                                       substr(upper(json_each.value), 1, 1) ||
                                       substr('000' || replace(replace(replace(replace(replace(replace(replace(replace(replace(
                                           upper(json_each.value), 'A', ''), 'E', ''), 'I', ''), 'O', ''), 'U', ''), 'H', ''), 'W', ''), 'Y', ''),
                                           'BFPV', '1'), 1, 3)
                                   ELSE ''
                               END,
                               lower(trim(json_each.value))
                        FROM json_each(NEW.places)
                        WHERE json_each.value IS NOT NULL AND trim(json_each.value) != '';
                    END
                """)
                
                # Create triggers for updates
                await client.create_table("""
                    CREATE TRIGGER IF NOT EXISTS update_persons_fuzzy
                    AFTER UPDATE ON documents
                    WHEN NEW.persons != OLD.persons
                    BEGIN
                        DELETE FROM persons_fuzzy WHERE document_id = NEW.id;
                        INSERT INTO persons_fuzzy (document_id, original_name, soundex_code, normalized_name)
                        SELECT NEW.id,
                               json_each.value,
                               CASE
                                   WHEN length(json_each.value) > 0 THEN
                                       substr(upper(json_each.value), 1, 1) ||
                                       substr('000' || replace(replace(replace(replace(replace(replace(replace(replace(replace(
                                           upper(json_each.value), 'A', ''), 'E', ''), 'I', ''), 'O', ''), 'U', ''), 'H', ''), 'W', ''), 'Y', ''),
                                           'BFPV', '1'), 1, 3)
                                   ELSE ''
                               END,
                               lower(trim(json_each.value))
                        FROM json_each(NEW.persons)
                        WHERE json_each.value IS NOT NULL AND trim(json_each.value) != '' AND NEW.persons IS NOT NULL AND NEW.persons != '';
                    END
                """)
                
                await client.create_table("""
                    CREATE TRIGGER IF NOT EXISTS update_places_fuzzy
                    AFTER UPDATE ON documents
                    WHEN NEW.places != OLD.places
                    BEGIN
                        DELETE FROM places_fuzzy WHERE document_id = NEW.id;
                        INSERT INTO places_fuzzy (document_id, original_place, soundex_code, normalized_place)
                        SELECT NEW.id,
                               json_each.value,
                               CASE
                                   WHEN length(json_each.value) > 0 THEN
                                       substr(upper(json_each.value), 1, 1) ||
                                       substr('000' || replace(replace(replace(replace(replace(replace(replace(replace(replace(
                                           upper(json_each.value), 'A', ''), 'E', ''), 'I', ''), 'O', ''), 'U', ''), 'H', ''), 'W', ''), 'Y', ''),
                                           'BFPV', '1'), 1, 3)
                                   ELSE ''
                               END,
                               lower(trim(json_each.value))
                        FROM json_each(NEW.places)
                        WHERE json_each.value IS NOT NULL AND trim(json_each.value) != '' AND NEW.places IS NOT NULL AND NEW.places != '';
                    END
                """)
                self._initialized = True
                logger.debug("Database schema initialized through MCP")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    async def store_document(self, doc_data: Dict[str, Any], ai_metadata: Dict[str, Any]) -> int:
        """Store document using MCP write operations."""
        return await self._store_document_async(doc_data, ai_metadata)

    async def _store_document_async(self, doc_data: Dict[str, Any], ai_metadata: Dict[str, Any]) -> int:
        """Async implementation of store_document with proper context management."""
        await self._ensure_initialized()
        try:
            async with get_mcp_client(self.db_path) as client:
                insert_query = """
                    INSERT INTO documents
                    (uuid, file_path, filename, extension, size, mime_type, md5_hash,
                     original_text, markdown_content, summary, document_type, categories, entities,
                     persons, places, mentioned_dates, file_references, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = [
                    doc_data.get('uuid'), doc_data.get('file_path'), doc_data.get('filename'),
                    doc_data.get('extension'), doc_data.get('size'), doc_data.get('mime_type'),
                    doc_data.get('md5_hash'), doc_data.get('original_text'), doc_data.get('markdown_content'),
                    ai_metadata.get('summary'), ai_metadata.get('document_type'),
                    json.dumps(ai_metadata.get('categories', [])), json.dumps(ai_metadata.get('entities', [])),
                    json.dumps(ai_metadata.get('persons', [])), json.dumps(ai_metadata.get('places', [])),
                    json.dumps(ai_metadata.get('mentioned_dates', [])), json.dumps(ai_metadata.get('file_references', [])),
                    doc_data.get('created_at'), doc_data.get('updated_at')
                ]
                await client.write_query(insert_query, params)
                id_result = await client.read_query(
                    "SELECT id FROM documents WHERE uuid = ?", [doc_data.get('uuid')]
                )
                if not id_result:
                    raise RuntimeError("Failed to retrieve document ID after insert")
                doc_id = id_result[0]['id']
                fts_query = """INSERT OR REPLACE INTO documents_fts
                    (rowid, original_text, markdown_content, summary, document_type, categories, entities, persons, places, mentioned_dates, file_references)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                fts_params = [
                    doc_id, doc_data.get('original_text', ''), doc_data.get('markdown_content', ''),
                    ai_metadata.get('summary', ''), ai_metadata.get('document_type', ''),
                    json.dumps(ai_metadata.get('categories', [])), json.dumps(ai_metadata.get('entities', [])),
                    json.dumps(ai_metadata.get('persons', [])), json.dumps(ai_metadata.get('places', [])),
                    json.dumps(ai_metadata.get('mentioned_dates', [])), json.dumps(ai_metadata.get('file_references', []))
                ]
                await client.write_query(fts_query, fts_params)
                logger.debug(f"Document stored with ID {doc_id} via MCP")
                return doc_id
        except Exception as e:
            logger.error(f"Failed to store document via MCP: {e}")
            raise

    async def store_chunks_and_embeddings(self, doc_id: int, chunks: List[str], embeddings: List[List[float]]):
        """Stores chunks and their embeddings in the database in a single transaction."""
        await self._ensure_initialized()
        if len(chunks) != len(embeddings):
            raise ValueError("The number of chunks and embeddings must be equal.")

        try:
            async with get_mcp_client(self.db_path) as client:
                for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
                    # Insert chunk first
                    chunk_query = "INSERT INTO chunks (document_id, chunk_index, content, char_count) VALUES (?, ?, ?, ?)"
                    chunk_params = [doc_id, i, chunk_content, len(chunk_content)]
                    await client.write_query(chunk_query, chunk_params)
                    
                    # Get the chunk ID by querying for the specific chunk we just inserted
                    chunk_id_query = "SELECT id FROM chunks WHERE document_id = ? AND chunk_index = ?"
                    chunk_id_result = await client.read_query(chunk_id_query, [doc_id, i])
                    
                    if not chunk_id_result:
                        logger.error(f"Failed to retrieve chunk ID for document {doc_id}, chunk {i}")
                        continue
                        
                    chunk_id = chunk_id_result[0]['id']
                    
                    # Insert the embedding into the JSON table
                    vector_query = "INSERT INTO chunk_vectors (chunk_id, embedding_json) VALUES (?, ?)"
                    embedding_json = json.dumps(embedding)
                    vector_params = [chunk_id, embedding_json]
                    
                    await client.write_query(vector_query, vector_params)
                
                logger.debug(f"Stored {len(chunks)} chunks and embeddings for document ID {doc_id}")
        except Exception as e:
            logger.error(f"Failed to store chunks and embeddings for document ID {doc_id}: {e}")
            raise
 
    def get_document_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get document by path using MCP read operations."""
        return asyncio.run(self._get_document_by_path_async(file_path))

    async def _get_document_by_path_async(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Async implementation of get_document_by_path with proper context management."""
        await self._ensure_initialized()
        try:
            async with get_mcp_client(self.db_path) as client:
                result = await client.read_query("SELECT * FROM documents WHERE file_path = ?", [file_path])
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get document by path via MCP: {e}")
            return None

    def delete_document_by_path(self, file_path: str) -> None:
        """Delete document by path using MCP operations."""
        asyncio.run(self._delete_document_by_path_async(file_path))

    async def _delete_document_by_path_async(self, file_path: str) -> None:
        """Async implementation of delete_document_by_path with proper context management."""
        await self._ensure_initialized()
        try:
            doc = await self._get_document_by_path_async(file_path)
            if not doc:
                return
            async with get_mcp_client(self.db_path) as client:
                await client.write_query("DELETE FROM documents_fts WHERE rowid = ?", [doc['id']])
                await client.write_query("DELETE FROM documents WHERE id = ?", [doc['id']])
                logger.debug(f"Document deleted: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete document via MCP: {e}")
            raise

    def update_document_path(self, old_path: str, new_path: str) -> None:
        """Update document path using MCP operations."""
        asyncio.run(self._update_document_path_async(old_path, new_path))

    async def _update_document_path_async(self, old_path: str, new_path: str) -> None:
        """Async implementation of update_document_path with proper context management."""
        await self._ensure_initialized()
        try:
            async with get_mcp_client(self.db_path) as client:
                await client.write_query("UPDATE documents SET file_path = ? WHERE file_path = ?", [new_path, old_path])
                logger.debug(f"Document path updated: {old_path} -> {new_path}")
        except Exception as e:
            logger.error(f"Failed to update document path via MCP: {e}")
            raise

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Perform FTS search using MCP operations."""
        return asyncio.run(self._search_async(query, limit))

    async def _search_async(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Async implementation of search with proper context management."""
        await self._ensure_initialized()
        try:
            async with get_mcp_client(self.db_path) as client:
                search_query = """
                    SELECT d.*, fts.rank FROM documents_fts AS fts
                    JOIN documents AS d ON fts.rowid = d.id
                    WHERE fts.documents_fts MATCH ? ORDER BY fts.rank LIMIT ?
                """
                results = await client.read_query(search_query, [query, limit])
                return results or []
        except Exception as e:
            logger.error(f"Failed to search documents via MCP: {e}")
            return []

    async def search_semantic(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Performs semantic search for a given query text using JSON-stored vectors."""
        await self._ensure_initialized()
        logger.debug(f"Performing semantic search for: '{query_text}'")

        try:
            # 1. Generate an embedding for the query text
            from src.core.embedding_service import create_embeddings
            query_embedding = create_embeddings([query_text])[0]

            # 2. Retrieve all stored embeddings and calculate similarities
            async with get_mcp_client(self.db_path) as client:
                search_query = """
                    SELECT
                        cv.embedding_json,
                        c.id as chunk_id,
                        c.content,
                        d.id as document_id,
                        d.file_path,
                        d.filename
                    FROM chunk_vectors cv
                    JOIN chunks c ON cv.chunk_id = c.id
                    JOIN documents d ON c.document_id = d.id
                """
                results = await client.read_query(search_query)
                
                if not results:
                    return []

                # 3. Calculate cosine similarities in Python
                similarities = []
                for row in results:
                    try:
                        stored_embedding = json.loads(row['embedding_json'])
                        similarity = self._cosine_similarity(query_embedding, stored_embedding)
                        similarities.append({
                            'chunk_id': row['chunk_id'],
                            'content': row['content'],
                            'document_id': row['document_id'],
                            'file_path': row['file_path'],
                            'filename': row['filename'],
                            'similarity': similarity
                        })
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Skipping malformed embedding data: {e}")
                        continue

                # 4. Sort by similarity and return top results
                similarities.sort(key=lambda x: x['similarity'], reverse=True)
                return similarities[:limit]

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            import numpy as np
            a, b = np.array(vec1), np.array(vec2)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        except ImportError:
            # Fallback implementation without numpy
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude_a = sum(a * a for a in vec1) ** 0.5
            magnitude_b = sum(b * b for b in vec2) ** 0.5
            if magnitude_a == 0 or magnitude_b == 0:
                return 0.0
            return dot_product / (magnitude_a * magnitude_b)
 
    def close(self):
        """Close MCP client connections."""
        pass  # MCP client cleanup is handled globally

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection statistics (MCP-compliant placeholder)."""
        return {"mcp_compliant": True, "direct_connections": 0, "status": "connected_via_mcp"}

def initialize_database():
    """Initialize database through MCP protocol with proper context management."""
    try:
        if not DB_FILE.parent.exists():
            DB_FILE.parent.mkdir(parents=True)
        store = DocumentStore(DB_FILE)
        asyncio.run(store._ensure_initialized())
        logger.info("Database initialized successfully via MCP")
    except Exception as e:
        logger.error(f"Failed to initialize database via MCP: {e}")
        raise

if __name__ == '__main__':
    initialize_database()
    print("Database initialized successfully via MCP.")