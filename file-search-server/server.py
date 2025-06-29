from mcp.server.fastmcp import FastMCP
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

mcp = FastMCP("file-search-server")

# Database connection helper
def get_db_connection():
    return sqlite3.connect("/Users/aaron/Projects/Simple_MCP_DB/filebrowser.db")

@mcp.tool()
async def search_file_content(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search for files containing specific text content.
    Searches in summary, categories, entities, persons, places, and markdown_content.
    
    Args:
        query: The text to search for in file contents
        limit: Maximum number of results to return (default: 20)
    
    Example: "Familie", "Bewerbung", "BMW", "Ihring"
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Search in multiple columns using OR
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT id, filename, file_path, extension, size, created_at, indexed_at,
                   summary, categories, entities, persons, places,
                   CASE 
                       WHEN summary LIKE ? THEN 'summary'
                       WHEN categories LIKE ? THEN 'categories' 
                       WHEN entities LIKE ? THEN 'entities'
                       WHEN persons LIKE ? THEN 'persons'
                       WHEN places LIKE ? THEN 'places'
                       ELSE 'other'
                   END as match_type
            FROM documents
            WHERE summary LIKE ? COLLATE NOCASE
               OR categories LIKE ? COLLATE NOCASE
               OR entities LIKE ? COLLATE NOCASE  
               OR persons LIKE ? COLLATE NOCASE
               OR places LIKE ? COLLATE NOCASE
               OR markdown_content LIKE ? COLLATE NOCASE
            ORDER BY created_at DESC
            LIMIT ?
        """, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern,
              search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "filename": row[1], 
                "path": row[2],
                "extension": row[3],
                "size": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "summary": row[7],
                "categories": row[8],
                "entities": row[9], 
                "persons": row[10],
                "places": row[11],
                "match_type": row[12]
            })
        
        return results
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]
    finally:
        conn.close()

@mcp.tool()
async def search_by_extension(extension: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Find all files with a specific extension.
    
    Args:
        extension: File extension (without dot, e.g., 'pdf', 'docx', 'txt')
        limit: Maximum results (default: 50)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Extension mit Punkt suchen falls ohne angegeben
        if not extension.startswith('.'):
            extension = '.' + extension
        
        cursor.execute("""
            SELECT id, filename, file_path, extension, size, created_at, indexed_at, summary
            FROM documents
            WHERE extension = ? COLLATE NOCASE
            ORDER BY created_at DESC  
            LIMIT ?
        """, (extension, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "filename": row[1],
                "path": row[2],
                "extension": row[3],
                "size": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "summary": row[7] if len(row) > 7 else ""
            })
        
        return results
    except Exception as e:
        return [{"error": f"Extension search failed: {str(e)}"}]
    finally:
        conn.close()

@mcp.tool()
async def get_database_stats() -> Dict[str, Any]:
    """
    Get basic statistics about the file database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Total files
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_files = cursor.fetchone()[0]
        
        # Total size - handle NULLs properly
        cursor.execute("SELECT SUM(COALESCE(size, 0)) FROM documents WHERE size IS NOT NULL")
        total_size_result = cursor.fetchone()
        total_size = total_size_result[0] if total_size_result and total_size_result[0] else 0
        
        # Files by extension
        cursor.execute("""
            SELECT extension, COUNT(*) as count
            FROM documents
            WHERE extension IS NOT NULL
            GROUP BY extension
            ORDER BY count DESC
            LIMIT 10
        """)
        extensions = [{"extension": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Files by document type
        cursor.execute("""
            SELECT document_type, COUNT(*) as count
            FROM documents
            WHERE document_type IS NOT NULL
            GROUP BY document_type
            ORDER BY count DESC
            LIMIT 5
        """)
        doc_types = [{"type": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Available categories
        cursor.execute("""
            SELECT DISTINCT categories
            FROM documents 
            WHERE categories IS NOT NULL AND categories != '[]'
            LIMIT 10
        """)
        categories = [row[0] for row in cursor.fetchall()]
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2) if total_size > 0 else 0,
            "top_extensions": extensions,
            "document_types": doc_types,
            "sample_categories": categories
        }
    except Exception as e:
        return {"error": f"Database stats failed: {str(e)}"}
    finally:
        conn.close()

if __name__ == "__main__":
    mcp.run(transport='stdio')

