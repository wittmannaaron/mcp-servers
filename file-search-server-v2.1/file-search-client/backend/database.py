import sqlite3
import os
from typing import List, Dict, Any

# Database path from specification
DB_PATH = "/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db"

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def get_document_by_id(document_id: int) -> Dict[str, Any]:
    """Retrieve a document by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, uuid, file_path, filename, extension, size, mime_type, md5_hash,
               original_text, markdown_content, summary, document_type, categories,
               entities, persons, places, mentioned_dates, file_references,
               created_at, updated_at, indexed_at
        FROM documents 
        WHERE id = ?
    """, (document_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def search_documents_fts(query: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Search documents using FTS5."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Using the documents_fts table (the actual table that exists)
    cursor.execute("""
        SELECT
            d.created_at,
            d.filename,
            d.file_path,
            SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 300) as content_preview,
            d.id,
            d.mime_type,
            d.mentioned_dates
        FROM documents_fts fts
        JOIN documents d ON d.id = fts.rowid
        WHERE documents_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Process the results to extract first date and source type
    results = []
    for row in rows:
        result = dict(row)
        
        # Extract first date from mentioned_dates if available
        if result.get('mentioned_dates'):
            # Try to parse dates from the mentioned_dates field
            # This is a simple approach - in a real implementation, you might want more sophisticated parsing
            dates = [date.strip() for date in result['mentioned_dates'].split(',') if date.strip()]
            if dates:
                result['first_date_in_document'] = dates[0]
            else:
                result['first_date_in_document'] = None
        else:
            result['first_date_in_document'] = None
            
        # Determine source type based on mime_type
        mime_type = result.get('mime_type', '')
        if mime_type == 'application/zip':
            result['source_type'] = 'archive'
        elif mime_type == 'message/rfc822':
            result['source_type'] = 'e-mail'
        else:
            result['source_type'] = 'file'  # or "Datei" in German
            
        results.append(result)
    
    return results