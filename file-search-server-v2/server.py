#!/usr/bin/env python3
"""
Minimal MCP File Search Server - Only the essential code
"""
from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import List, Dict, Any

mcp = FastMCP("file-search-server")

def get_db_connection():
    return sqlite3.connect("/Users/aaron/Projects/Simple_MCP_DB/filebrowser.db")

@mcp.tool()
async def getData(search_terms: List[str]) -> List[Dict[str, Any]]:
    """
    Simple search using exact SQL query
    """
    print(f"DEBUG: getData called with search_terms: {search_terms}")
    print(f"DEBUG: Type of search_terms: {type(search_terms)}")
    if search_terms:
        for i, term in enumerate(search_terms):
            print(f"DEBUG: Term {i}: '{term}' (type: {type(term)})")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Build search query from search terms
        if not search_terms:
            search_terms = ["Ihring"]  # Default fallback
        
        # Clean and combine search terms - remove commas and quotes
        clean_terms = []
        for term in search_terms:
            # Remove problematic characters for FTS
            clean_term = str(term).replace(',', '').replace('"', '').replace("'", '').strip()
            if clean_term:  # Only add non-empty terms
                clean_terms.append(clean_term)
        
        if not clean_terms:
            clean_terms = ["Ihring"]  # Fallback
        
        # Combine search terms with OR logic
        search_query = " OR ".join(clean_terms)
        print(f"DEBUG: Original terms: {search_terms}")
        print(f"DEBUG: Cleaned terms: {clean_terms}")
        print(f"DEBUG: Final FTS search query: '{search_query}'")
        
        query = """
        SELECT 
            d.created_at,
            d.filename,
            d.file_path,
            SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 200) as content_preview
        FROM documents_fts_extended fts
        JOIN documents d ON d.id = fts.id
        WHERE documents_fts_extended MATCH ?
        LIMIT 100
        """
        
        cursor.execute(query, [search_query])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "created_at": row[0],
                "filename": row[1], 
                "file_path": row[2],
                "content_preview": row[3]
            })
        
        print(f"DEBUG: Found {len(results)} results")
        for i, result in enumerate(results):
            print(f"DEBUG: Result {i+1}: {result['filename']}")
        
        return results
        
    except Exception as e:
        print(f"ERROR: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def get_database_stats() -> Dict[str, Any]:
    """
    Simple database stats
    """
    print("DEBUG: get_database_stats called")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_files = cursor.fetchone()[0]
        
        print(f"DEBUG: Total files: {total_files}")
        
        return {
            "total_files": total_files,
            "status": "working"
        }
        
    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    mcp.run(transport='stdio')