#!/usr/bin/env python3
"""
Query the email processing database to find entries
"""

import sqlite3
from pathlib import Path
import json

def query_email_database():
    """Query the email processing database"""
    
    db_path = Path("../data/test_email_processing.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("   Run test_database_storage.py first to create test data")
        return
    
    print(f"📂 Querying database: {db_path}")
    print("="*60)
    
    with sqlite3.connect(db_path) as conn:
        # Get all tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 Tables in database: {[t[0] for t in tables]}")
        
        # Get email documents
        cursor = conn.execute("""
        SELECT COUNT(*) as total,
               COUNT(DISTINCT eml_file_path) as unique_emails,
               COUNT(DISTINCT email_from) as unique_senders
        FROM email_documents
        """)
        
        stats = cursor.fetchone()
        print(f"\n📈 Database Statistics:")
        print(f"   Total documents: {stats[0]}")
        print(f"   Unique email files: {stats[1]}")
        print(f"   Unique senders: {stats[2]}")
        
        # Show all entries
        cursor = conn.execute("""
        SELECT id, eml_file_path, attachment_filename, email_from, email_subject, created_at
        FROM email_documents 
        ORDER BY created_at DESC
        """)
        
        print(f"\n📄 All Email Documents:")
        print("-" * 60)
        for row in cursor.fetchall():
            eml_file = Path(row[1]).name
            print(f"ID: {row[0]}")
            print(f"Source: {eml_file}")
            print(f"Attachment: {row[2]}")
            print(f"From: {row[3][:50]}..." if row[3] else "")
            print(f"Subject: {row[4][:50]}..." if row[4] else "")
            print(f"Created: {row[5]}")
            print("-" * 30)
        
        # Example searches
        print(f"\n🔍 Example Searches:")
        print("="*40)
        
        # Search by keyword
        keyword = "Familiensache"
        cursor = conn.execute("""
        SELECT attachment_filename, email_subject, content_text
        FROM email_documents 
        WHERE content_text LIKE ?
        """, (f"%{keyword}%",))
        
        results = cursor.fetchall()
        print(f"\n1. Documents containing '{keyword}': {len(results)}")
        for result in results:
            print(f"   📎 {result[0]}")
            print(f"   📧 {result[1][:60]}...")
            print(f"   📝 ...{result[2][200:300]}...")
        
        # Search by sender domain
        cursor = conn.execute("""
        SELECT COUNT(*), email_from
        FROM email_documents 
        WHERE email_from LIKE '%rechtsanw%'
        GROUP BY email_from
        """)
        
        results = cursor.fetchall()
        print(f"\n2. Documents from law firms: {len(results)}")
        for count, sender in results:
            print(f"   {count} documents from: {sender[:60]}...")
        
        # Search by file type
        cursor = conn.execute("""
        SELECT COUNT(*), 
               CASE 
                 WHEN attachment_filename LIKE '%.pdf' THEN 'PDF'
                 WHEN attachment_filename LIKE '%.doc%' THEN 'Word'
                 ELSE 'Other'
               END as file_type
        FROM email_documents 
        GROUP BY file_type
        """)
        
        results = cursor.fetchall()
        print(f"\n3. Documents by file type:")
        for count, file_type in results:
            print(f"   {file_type}: {count} documents")
    
    print(f"\n✅ Database query completed!")
    print(f"\n💡 To query this database manually:")
    print(f"   sqlite3 {db_path}")
    print(f"   .tables")
    print(f"   SELECT * FROM email_documents;")

def query_with_mcp():
    """Show how to query using MCP SQLite server"""
    print(f"\n🔌 Using MCP SQLite Server:")
    print("="*40)
    print("If you have the MCP SQLite server running, you can query like this:")
    print()
    print("1. Start the MCP server (already configured in .mcp.json)")
    print("2. Use these MCP queries:")
    print()
    
    queries = [
        "SELECT COUNT(*) FROM email_documents",
        "SELECT attachment_filename, email_subject FROM email_documents WHERE content_text LIKE '%court%'",
        "SELECT DISTINCT email_from FROM email_documents",
        "SELECT * FROM email_documents WHERE created_at > datetime('now', '-1 day')"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"   Query {i}: {query}")
    
    print()
    print("3. Or use the MCP tools directly in your code:")
    print("""
    # Example MCP usage:
    from mcp_client import MCPClient
    
    async with MCPClient() as client:
        await client.connect_to_server("sqlite-filebrowser")
        
        result = await client.call_tool("read_query", {
            "query": "SELECT * FROM email_documents WHERE content_text LIKE ?",
            "params": ["%court%"]
        })
        
        print(f"Found {len(result)} documents about courts")
    """)

if __name__ == "__main__":
    query_email_database()
    query_with_mcp()