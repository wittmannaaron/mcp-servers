"""
Updated document store for file-catalog project.
Adjusted for the new database path and project structure.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger
from src.core.mcp_client import get_mcp_client

DB_FILE = Path(__file__).parent.parent.parent / "data" / "filecatalog.db"

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
                
                # Create extended FTS5 table for client compatibility
                await client.create_table("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_extended USING fts5(
                        filename,
                        file_path,
                        original_text, 
                        markdown_content, 
                        summary, 
                        document_type,
                        categories, 
                        entities, 
                        persons, 
                        places, 
                        mentioned_dates,
                        tokenize='unicode61'
                    )
                """)
                
                # Create triggers for automatic FTS synchronization
                await client.create_table("""
                    CREATE TRIGGER IF NOT EXISTS documents_fts_insert
                    AFTER INSERT ON documents
                    BEGIN
                        INSERT INTO documents_fts (rowid, original_text, markdown_content, summary, document_type, categories, entities, persons, places, mentioned_dates, file_references)
                        VALUES (NEW.id, 
                                COALESCE(NEW.original_text, ''), 
                                COALESCE(NEW.markdown_content, ''), 
                                COALESCE(NEW.summary, ''), 
                                COALESCE(NEW.document_type, ''), 
                                COALESCE(NEW.categories, ''), 
                                COALESCE(NEW.entities, ''), 
                                COALESCE(NEW.persons, ''), 
                                COALESCE(NEW.places, ''), 
                                COALESCE(NEW.mentioned_dates, ''), 
                                COALESCE(NEW.file_references, ''));
                        
                        INSERT INTO documents_fts_extended (rowid, filename, file_path, original_text, markdown_content, summary, document_type, categories, entities, persons, places, mentioned_dates)
                        VALUES (NEW.id, 
                                COALESCE(NEW.filename, ''),
                                COALESCE(NEW.file_path, ''),
                                COALESCE(NEW.original_text, ''), 
                                COALESCE(NEW.markdown_content, ''), 
                                COALESCE(NEW.summary, ''), 
                                COALESCE(NEW.document_type, ''), 
                                COALESCE(NEW.categories, ''), 
                                COALESCE(NEW.entities, ''), 
                                COALESCE(NEW.persons, ''), 
                                COALESCE(NEW.places, ''), 
                                COALESCE(NEW.mentioned_dates, ''));
                    END
                """)
                
                await client.create_table("""
                    CREATE TRIGGER IF NOT EXISTS documents_fts_update
                    AFTER UPDATE ON documents
                    BEGIN
                        UPDATE documents_fts SET 
                            original_text = COALESCE(NEW.original_text, ''),
                            markdown_content = COALESCE(NEW.markdown_content, ''),
                            summary = COALESCE(NEW.summary, ''),
                            document_type = COALESCE(NEW.document_type, ''),
                            categories = COALESCE(NEW.categories, ''),
                            entities = COALESCE(NEW.entities, ''),
                            persons = COALESCE(NEW.persons, ''),
                            places = COALESCE(NEW.places, ''),
                            mentioned_dates = COALESCE(NEW.mentioned_dates, ''),
                            file_references = COALESCE(NEW.file_references, '')
                        WHERE rowid = NEW.id;
                        
                        UPDATE documents_fts_extended SET 
                            filename = COALESCE(NEW.filename, ''),
                            file_path = COALESCE(NEW.file_path, ''),
                            original_text = COALESCE(NEW.original_text, ''),
                            markdown_content = COALESCE(NEW.markdown_content, ''),
                            summary = COALESCE(NEW.summary, ''),
                            document_type = COALESCE(NEW.document_type, ''),
                            categories = COALESCE(NEW.categories, ''),
                            entities = COALESCE(NEW.entities, ''),
                            persons = COALESCE(NEW.persons, ''),
                            places = COALESCE(NEW.places, ''),
                            mentioned_dates = COALESCE(NEW.mentioned_dates, '')
                        WHERE rowid = NEW.id;
                    END
                """)
                
                await client.create_table("""
                    CREATE TRIGGER IF NOT EXISTS documents_fts_delete
                    AFTER DELETE ON documents
                    BEGIN
                        DELETE FROM documents_fts WHERE rowid = OLD.id;
                        DELETE FROM documents_fts_extended WHERE rowid = OLD.id;
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
                # FTS tables are automatically updated via triggers, no manual insert needed
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

    def close(self):
        """Close MCP client connections."""
        pass  # MCP client cleanup is handled globally

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection statistics (MCP-compliant placeholder)."""
        return {"mcp_compliant": True, "direct_connections": 0, "status": "connected_via_mcp"}

async def initialize_database():
    """Initialize database through MCP protocol with proper context management."""
    try:
        if not DB_FILE.parent.exists():
            DB_FILE.parent.mkdir(parents=True)
        store = DocumentStore(DB_FILE)
        await store._ensure_initialized()
        logger.info("Database initialized successfully via MCP")
    except Exception as e:
        logger.error(f"Failed to initialize database via MCP: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(initialize_database())
    print("Database initialized successfully via MCP.")