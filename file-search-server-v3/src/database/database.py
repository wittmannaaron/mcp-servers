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

DB_FILE = Path(__file__).parent / "filebrowser.db"

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