#!/usr/bin/env python3
"""
MCP File Search Server V2 - German Document Research Assistant
With 9 specialized search tools for comprehensive document corpus research
"""
from mcp.server.fastmcp import FastMCP
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

mcp = FastMCP("file-search-server-v2")

def get_db_connection():
    return sqlite3.connect("/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db")

def initialize_fuzzy_tables():
    """Initialize and populate fuzzy search tables from existing document data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("Initializing fuzzy search tables...")
        
        # Check if fuzzy tables are already populated
        cursor.execute("SELECT COUNT(*) FROM persons_fuzzy")
        persons_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM places_fuzzy") 
        places_count = cursor.fetchone()[0]
        
        if persons_count > 0 and places_count > 0:
            print(f"Fuzzy tables already populated: {persons_count} persons, {places_count} places")
            return
        
        # Clear existing data
        cursor.execute("DELETE FROM persons_fuzzy")
        cursor.execute("DELETE FROM places_fuzzy")
        
        # Populate persons_fuzzy table
        cursor.execute("SELECT id, persons FROM documents WHERE persons IS NOT NULL AND persons != '' AND persons != '[]'")
        docs_with_persons = cursor.fetchall()
        
        for doc_id, persons_json in docs_with_persons:
            try:
                persons = json.loads(persons_json) if persons_json else []
                for person in persons:
                    if isinstance(person, dict) and 'name' in person:
                        name = person['name']
                    elif isinstance(person, str):
                        name = person
                    else:
                        continue
                        
                    if name and len(name.strip()) > 1:
                        normalized_name = name.upper().replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
                        soundex_code = soundex(name)
                        
                        cursor.execute("""
                            INSERT OR IGNORE INTO persons_fuzzy 
                            (document_id, original_name, soundex_code, normalized_name)
                            VALUES (?, ?, ?, ?)
                        """, [doc_id, name, soundex_code, normalized_name])
                        
            except json.JSONDecodeError:
                continue
        
        # Populate places_fuzzy table  
        cursor.execute("SELECT id, places FROM documents WHERE places IS NOT NULL AND places != '' AND places != '[]'")
        docs_with_places = cursor.fetchall()
        
        for doc_id, places_json in docs_with_places:
            try:
                places = json.loads(places_json) if places_json else []
                for place in places:
                    if isinstance(place, dict) and 'name' in place:
                        place_name = place['name']
                    elif isinstance(place, str):
                        place_name = place
                    else:
                        continue
                        
                    if place_name and len(place_name.strip()) > 1:
                        normalized_place = place_name.upper().replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
                        soundex_code = soundex(place_name)
                        
                        cursor.execute("""
                            INSERT OR IGNORE INTO places_fuzzy 
                            (document_id, original_place, soundex_code, normalized_place)
                            VALUES (?, ?, ?, ?)
                        """, [doc_id, place_name, soundex_code, normalized_place])
                        
            except json.JSONDecodeError:
                continue
        
        conn.commit()
        
        # Report results
        cursor.execute("SELECT COUNT(*) FROM persons_fuzzy")
        final_persons = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM places_fuzzy")
        final_places = cursor.fetchone()[0]
        
        print(f"Fuzzy tables populated: {final_persons} persons, {final_places} places")
        
    except Exception as e:
        print(f"Error initializing fuzzy tables: {e}")
        conn.rollback()
    finally:
        conn.close()

def soundex(name: str) -> str:
    """Simple soundex implementation for German names"""
    if not name:
        return "0000"
    
    name = name.upper().replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
    
    # Keep first letter
    soundex_code = name[0]
    
    # Replace consonants with digits
    mapping = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3',
        'L': '4',
        'M': '5', 'N': '5',
        'R': '6'
    }
    
    for i in range(1, len(name)):
        if name[i] in mapping:
            soundex_code += mapping[name[i]]
    
    # Remove duplicates and pad to 4 characters
    clean_code = soundex_code[0]
    for i in range(1, len(soundex_code)):
        if soundex_code[i] != soundex_code[i-1]:
            clean_code += soundex_code[i]
    
    return (clean_code + "0000")[:4]

@mcp.tool()
async def semantic_expression_search(query: str) -> List[Dict[str, Any]]:
    """
    Searches documents based on semantic expression in natural language (German).
    
    Args:
        query: Natural language expression or topic, e.g. 'Fusion Middleware Architektur'
    """
    print(f"DEBUG: semantic_expression_search called with query: {query}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Clean and prepare FTS5 query
        clean_query = query.replace('"', '').replace("'", '').strip()
        if not clean_query:
            return []
        
        # Use FTS5 search (documents_fts_extended table available)
        sql = """
        SELECT 
            d.id,
            d.filename,
            d.file_path,
            d.created_at,
            SUBSTR(COALESCE(d.original_text, d.markdown_content, d.summary, ''), 1, 300) as content_preview
        FROM documents_fts_extended fts
        JOIN documents d ON d.id = fts.rowid
        WHERE documents_fts_extended MATCH ?
        ORDER BY rank
        LIMIT 50
        """
        
        cursor.execute(sql, [clean_query])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "created_at": row[3],
                "content_preview": row[4]
            })
        
        print(f"DEBUG: Found {len(results)} results for semantic search")
        return results
        
    except Exception as e:
        print(f"ERROR in semantic_expression_search: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def fuzzy_search_person(name: str) -> List[Dict[str, Any]]:
    """
    Finds documents mentioning person with phonetically similar names (German input).
    
    Args:
        name: Person name, possibly with OCR errors (e.g. 'Muller' for 'Müller')
    """
    print(f"DEBUG: fuzzy_search_person called with name: {name}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Generate soundex for the input name
        name_soundex = soundex(name)
        normalized_name = name.upper().replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
        
        print(f"DEBUG: Name soundex: {name_soundex}, normalized: {normalized_name}")
        
        # Search in persons_fuzzy table using soundex and normalized names
        sql = """
        SELECT DISTINCT
            d.id,
            d.filename,
            d.file_path,
            d.created_at,
            pf.original_name,
            SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 300) as content_preview
        FROM persons_fuzzy pf
        JOIN documents d ON d.id = pf.document_id
        WHERE pf.soundex_code = ? OR pf.normalized_name LIKE ?
        ORDER BY d.created_at DESC
        LIMIT 50
        """
        
        cursor.execute(sql, [name_soundex, f"%{normalized_name}%"])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "created_at": row[3],
                "matched_person": row[4],
                "content_preview": row[5]
            })
        
        print(f"DEBUG: Found {len(results)} results for person fuzzy search")
        return results
        
    except Exception as e:
        print(f"ERROR in fuzzy_search_person: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def fuzzy_search_place(place: str) -> List[Dict[str, Any]]:
    """
    Finds documents mentioning places with similar sounding names (German input).
    
    Args:
        place: Place name with possible spelling variation (e.g. 'Munchen' for 'München')
    """
    print(f"DEBUG: fuzzy_search_place called with place: {place}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Generate soundex for the input place
        place_soundex = soundex(place)
        normalized_place = place.upper().replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
        
        print(f"DEBUG: Place soundex: {place_soundex}, normalized: {normalized_place}")
        
        # Search in places_fuzzy table using soundex and normalized places
        sql = """
        SELECT DISTINCT
            d.id,
            d.filename,
            d.file_path,
            d.created_at,
            plf.original_place,
            SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 300) as content_preview
        FROM places_fuzzy plf
        JOIN documents d ON d.id = plf.document_id
        WHERE plf.soundex_code = ? OR plf.normalized_place LIKE ?
        ORDER BY d.created_at DESC
        LIMIT 50
        """
        
        cursor.execute(sql, [place_soundex, f"%{normalized_place}%"])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "created_at": row[3],
                "matched_place": row[4],
                "content_preview": row[5]
            })
        
        print(f"DEBUG: Found {len(results)} results for place fuzzy search")
        return results
        
    except Exception as e:
        print(f"ERROR in fuzzy_search_place: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def search_by_date_range(start: str, end: str) -> List[Dict[str, Any]]:
    """
    Finds documents created between two dates (YYYY-MM-DD).
    
    Args:
        start: Start date of range
        end: End date of range  
    """
    print(f"DEBUG: search_by_date_range called with start: {start}, end: {end}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Validate date format
        datetime.strptime(start, '%Y-%m-%d')
        datetime.strptime(end, '%Y-%m-%d')
        
        sql = """
        SELECT 
            id,
            filename,
            file_path,
            created_at,
            SUBSTR(COALESCE(original_text, markdown_content, ''), 1, 300) as content_preview
        FROM documents
        WHERE DATE(created_at) BETWEEN ? AND ?
        ORDER BY created_at DESC
        LIMIT 100
        """
        
        cursor.execute(sql, [start, end])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "created_at": row[3],
                "content_preview": row[4]
            })
        
        print(f"DEBUG: Found {len(results)} results for date range search")
        return results
        
    except ValueError as e:
        print(f"ERROR: Invalid date format in search_by_date_range: {e}")
        return [{"error": "Invalid date format. Use YYYY-MM-DD"}]
    except Exception as e:
        print(f"ERROR in search_by_date_range: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def search_creation_date(created: str) -> List[Dict[str, Any]]:
    """
    Finds documents created on specific date (YYYY-MM-DD).
    
    Args:
        created: Date when document was created
    """
    print(f"DEBUG: search_creation_date called with created: {created}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Validate date format
        datetime.strptime(created, '%Y-%m-%d')
        
        sql = """
        SELECT 
            id,
            filename,
            file_path,
            created_at,
            SUBSTR(COALESCE(original_text, markdown_content, ''), 1, 300) as content_preview
        FROM documents
        WHERE DATE(created_at) = ?
        ORDER BY created_at DESC
        LIMIT 100
        """
        
        cursor.execute(sql, [created])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "created_at": row[3],
                "content_preview": row[4]
            })
        
        print(f"DEBUG: Found {len(results)} results for creation date search")
        return results
        
    except ValueError as e:
        print(f"ERROR: Invalid date format in search_creation_date: {e}")
        return [{"error": "Invalid date format. Use YYYY-MM-DD"}]
    except Exception as e:
        print(f"ERROR in search_creation_date: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def search_date_in_document(date: str) -> List[Dict[str, Any]]:
    """
    Finds documents mentioning specific date in content (YYYY-MM-DD).
    
    Args:
        date: Specific date mentioned in document content
    """
    print(f"DEBUG: search_date_in_document called with date: {date}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Validate date format
        datetime.strptime(date, '%Y-%m-%d')
        
        # Search in mentioned_dates JSON field and content
        sql = """
        SELECT 
            id,
            filename,
            file_path,
            created_at,
            mentioned_dates,
            SUBSTR(COALESCE(original_text, markdown_content, ''), 1, 300) as content_preview
        FROM documents
        WHERE mentioned_dates LIKE ? 
           OR original_text LIKE ?
           OR markdown_content LIKE ?
        ORDER BY created_at DESC
        LIMIT 100
        """
        
        date_pattern = f"%{date}%"
        cursor.execute(sql, [date_pattern, date_pattern, date_pattern])
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "created_at": row[3],
                "mentioned_dates": row[4],
                "content_preview": row[5]
            })
        
        print(f"DEBUG: Found {len(results)} results for date in document search")
        return results
        
    except ValueError as e:
        print(f"ERROR: Invalid date format in search_date_in_document: {e}")
        return [{"error": "Invalid date format. Use YYYY-MM-DD"}]
    except Exception as e:
        print(f"ERROR in search_date_in_document: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def find_duplicates() -> List[Dict[str, Any]]:
    """
    Returns list of files with identical content (based on MD5 hash).
    """
    print("DEBUG: find_duplicates called")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        sql = """
        SELECT 
            md5_hash,
            COUNT(*) as duplicate_count,
            GROUP_CONCAT(filename || ' (' || file_path || ')') as files
        FROM documents
        WHERE md5_hash IS NOT NULL AND md5_hash != ''
        GROUP BY md5_hash
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
        LIMIT 100
        """
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "md5_hash": row[0],
                "duplicate_count": row[1],
                "files": row[2].split(',') if row[2] else []
            })
        
        print(f"DEBUG: Found {len(results)} duplicate groups")
        return results
        
    except Exception as e:
        print(f"ERROR in find_duplicates: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def get_document_content_by_id(id: int) -> Dict[str, Any]:
    """
    Returns full markdown content of document by ID.
    
    Args:
        id: Internal document ID
    """
    print(f"DEBUG: get_document_content_by_id called with id: {id}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        sql = """
        SELECT 
            id,
            filename,
            file_path,
            created_at,
            original_text,
            markdown_content,
            summary,
            document_type,
            categories,
            persons,
            places
        FROM documents
        WHERE id = ?
        """
        
        cursor.execute(sql, [id])
        row = cursor.fetchone()
        
        if not row:
            return {"error": f"Document with ID {id} not found"}
        
        result = {
            "id": row[0],
            "filename": row[1],
            "file_path": row[2],
            "created_at": row[3],
            "original_text": row[4],
            "markdown_content": row[5],
            "summary": row[6],
            "document_type": row[7],
            "categories": row[8],
            "persons": row[9],
            "places": row[10]
        }
        
        print(f"DEBUG: Retrieved document: {result['filename']}")
        return result
        
    except Exception as e:
        print(f"ERROR in get_document_content_by_id: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

@mcp.tool()
async def rank_documents_by_relevance(query: str, doc_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Ranks list of documents based on relevance to query.
    
    Args:
        query: Search query for relevance ranking
        doc_ids: List of document IDs to rank
    """
    print(f"DEBUG: rank_documents_by_relevance called with query: {query}, doc_ids: {doc_ids}")
    
    if not doc_ids:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create placeholders for IN clause
        placeholders = ','.join('?' * len(doc_ids))
        
        # Use FTS5 ranking with bm25 if available, otherwise simple text matching
        sql = f"""
        SELECT 
            d.id,
            d.filename,
            d.file_path,
            d.created_at,
            CASE 
                WHEN d.original_text LIKE ? THEN 3
                WHEN d.markdown_content LIKE ? THEN 2  
                WHEN d.summary LIKE ? THEN 1
                ELSE 0
            END as relevance_score,
            SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 300) as content_preview
        FROM documents d
        WHERE d.id IN ({placeholders})
        ORDER BY relevance_score DESC, d.created_at DESC
        """
        
        query_pattern = f"%{query}%"
        params = [query_pattern, query_pattern, query_pattern] + doc_ids
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "filename": row[1],
                "file_path": row[2],
                "created_at": row[3],
                "relevance_score": row[4],
                "content_preview": row[5]
            })
        
        print(f"DEBUG: Ranked {len(results)} documents by relevance")
        return results
        
    except Exception as e:
        print(f"ERROR in rank_documents_by_relevance: {e}")
        return [{"error": str(e)}]
    finally:
        conn.close()

@mcp.tool()
async def get_database_stats() -> Dict[str, Any]:
    """
    Returns comprehensive database statistics.
    """
    print("DEBUG: get_database_stats called")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        stats = {}
        
        # Count documents
        cursor.execute("SELECT COUNT(*) FROM documents")
        stats["total_documents"] = cursor.fetchone()[0]
        
        # Count chunks
        cursor.execute("SELECT COUNT(*) FROM chunks")
        stats["total_chunks"] = cursor.fetchone()[0]
        
        # Count persons_fuzzy entries
        cursor.execute("SELECT COUNT(*) FROM persons_fuzzy")
        stats["total_persons"] = cursor.fetchone()[0]
        
        # Count places_fuzzy entries  
        cursor.execute("SELECT COUNT(*) FROM places_fuzzy")
        stats["total_places"] = cursor.fetchone()[0]
        
        # Recent documents
        cursor.execute("SELECT COUNT(*) FROM documents WHERE DATE(created_at) >= DATE('now', '-7 days')")
        stats["recent_documents"] = cursor.fetchone()[0]
        
        stats["status"] = "operational"
        
        print(f"DEBUG: Database stats: {stats}")
        return stats
        
    except Exception as e:
        print(f"ERROR in get_database_stats: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    # Initialize fuzzy tables on startup
    initialize_fuzzy_tables()
    mcp.run(transport='stdio')
