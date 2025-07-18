#!/usr/bin/env python3
"""
Enhanced MCP File Search Server with Multi-Word Search Support
"""
from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import List, Dict, Any

mcp = FastMCP("file-search-server")

def get_db_connection():
    return sqlite3.connect("/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db")

@mcp.tool()
async def getData(search_terms: List[str], search_mode: str = "OR") -> List[Dict[str, Any]]:
    """
    Enhanced search with multiple search terms and different modes
    
    Args:
        search_terms: List of search terms
        search_mode: "OR" (any term), "AND" (all terms), "PHRASE" (exact phrase)
    """
    print(f"DEBUG: getData called with search_terms: {search_terms}, mode: {search_mode}")
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
        
        # Clean search terms - remove problematic characters for FTS
        clean_terms = []
        for term in search_terms:
            # Remove problematic characters for FTS but keep meaningful punctuation
            clean_term = str(term).replace('"', '').replace("'", '').strip()
            if clean_term:  # Only add non-empty terms
                clean_terms.append(clean_term)
        
        if not clean_terms:
            clean_terms = ["Ihring"]  # Fallback
        
        # Build enhanced search query based on search mode
        if search_mode.upper() == "AND":
            # All terms must be present
            search_query = " AND ".join(clean_terms)
        elif search_mode.upper() == "PHRASE":
            # Exact phrase search
            search_query = '"' + " ".join(clean_terms) + '"'
        else:
            # Default OR logic - any term
            search_query = " OR ".join(clean_terms)
            
        print(f"DEBUG: Original terms: {search_terms}")
        print(f"DEBUG: Cleaned terms: {clean_terms}")
        print(f"DEBUG: Search mode: {search_mode}")
        print(f"DEBUG: Final FTS search query: '{search_query}'")
        
        query = """
        SELECT 
            d.created_at,
            d.filename,
            d.file_path,
            SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 200) as content_preview
        FROM documents_fts_extended fts
        JOIN documents d ON d.id = fts.rowid
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
async def search_with_auto_mode(search_terms: List[str]) -> List[Dict[str, Any]]:
    """
    Smart search that automatically detects the best search mode
    
    Args:
        search_terms: List of search terms
    """
    print(f"DEBUG: search_with_auto_mode called with: {search_terms}")
    
    try:
        # Auto-detect search mode based on input
        if len(search_terms) == 1:
            # Single term - just search normally
            print(f"DEBUG: Single term search with OR")
            return await getData(search_terms, "OR")
        elif len(search_terms) <= 3:
            # 2-3 terms - try AND first (more precise), fallback to OR
            print(f"DEBUG: Trying AND search first for {len(search_terms)} terms")
            and_results = await getData(search_terms, "AND")
            
            # Check if AND results are good enough
            if and_results and len(and_results) >= 5:  # Good number of results
                print(f"DEBUG: AND search successful with {len(and_results)} results")
                return and_results
            else:
                print(f"DEBUG: AND search returned {len(and_results) if and_results else 0} results, trying OR")
                or_results = await getData(search_terms, "OR")
                print(f"DEBUG: OR search returned {len(or_results) if or_results else 0} results")
                return or_results if or_results else []
        else:
            # Many terms - use OR to avoid too restrictive search
            print(f"DEBUG: Using OR search for {len(search_terms)} terms (avoiding too restrictive AND)")
            return await getData(search_terms, "OR")
    except Exception as e:
        print(f"ERROR in search_with_auto_mode: {e}")
        # Fallback to simple OR search
        try:
            return await getData(search_terms, "OR")
        except Exception as e2:
            print(f"ERROR in fallback search: {e2}")
            return []

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
