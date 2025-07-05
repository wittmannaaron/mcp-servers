#!/usr/bin/env python3
"""
Test storing email processing results in database using MCP
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.extractors.email_extractor import extract_email_attachments
from src.core.logging_config import setup_logging

async def test_database_storage():
    """Test storing email processing results in database"""
    setup_logging()
    logger.info("Testing database storage of email processing results")
    
    # Process one email file to test database storage
    test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
    eml_file = test_dir / "Ihring ._. Ihring.eml"
    
    if not eml_file.exists():
        logger.error(f"Test file not found: {eml_file}")
        return
    
    logger.info(f"Processing test file: {eml_file.name}")
    
    try:
        # Extract attachments
        attachments = extract_email_attachments(str(eml_file))
        logger.info(f"Found {len(attachments)} attachments")
        
        # Try to use MCP SQLite server to store data
        try:
            from mcp_client import MCPClient
            
            async with MCPClient() as client:
                await client.connect_to_server("sqlite-filebrowser")
                
                # Create test table if needed
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS email_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    eml_file_path TEXT NOT NULL,
                    attachment_filename TEXT,
                    content_text TEXT,
                    email_from TEXT,
                    email_to TEXT,
                    email_subject TEXT,
                    email_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                await client.call_tool("create_table", {"query": create_table_sql})
                logger.info("Created/verified email_documents table")
                
                # Insert each attachment
                for i, attachment in enumerate(attachments):
                    email_meta = attachment.get("email_metadata", {})
                    
                    insert_sql = """
                    INSERT INTO email_documents 
                    (eml_file_path, attachment_filename, content_text, email_from, email_to, email_subject, email_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    await client.call_tool("write_query", {
                        "query": insert_sql,
                        "params": [
                            str(eml_file),
                            attachment.get("attachment_filename", ""),
                            attachment.get("original_text", "")[:1000],  # Truncate for testing
                            email_meta.get("from", ""),
                            email_meta.get("to", ""),
                            email_meta.get("subject", ""),
                            email_meta.get("date", "")
                        ]
                    })
                    
                    logger.info(f"Stored attachment {i+1}: {attachment.get('attachment_filename', '')}")
                
                # Query back the data to verify
                query_sql = "SELECT * FROM email_documents WHERE eml_file_path = ?"
                result = await client.call_tool("read_query", {
                    "query": query_sql,
                    "params": [str(eml_file)]
                })
                
                logger.info(f"Retrieved {len(result)} records from database")
                print("\nStored email documents:")
                print("-" * 60)
                for row in result:
                    print(f"ID: {row[0]}")
                    print(f"EML File: {Path(row[1]).name}")
                    print(f"Attachment: {row[2]}")
                    print(f"From: {row[4][:50]}...")
                    print(f"Subject: {row[6][:50]}...")
                    print(f"Content Preview: {row[3][:100]}...")
                    print("-" * 60)
                
        except ImportError:
            logger.warning("MCP client not available, using direct SQLite instead")
            
            # Fallback to direct SQLite for testing
            import sqlite3
            
            db_path = Path("./data/test_email_processing.db")
            db_path.parent.mkdir(exist_ok=True)
            
            with sqlite3.connect(db_path) as conn:
                # Create table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS email_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    eml_file_path TEXT NOT NULL,
                    attachment_filename TEXT,
                    content_text TEXT,
                    email_from TEXT,
                    email_to TEXT,
                    email_subject TEXT,
                    email_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Insert attachments
                for i, attachment in enumerate(attachments):
                    email_meta = attachment.get("email_metadata", {})
                    
                    conn.execute("""
                    INSERT INTO email_documents 
                    (eml_file_path, attachment_filename, content_text, email_from, email_to, email_subject, email_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(eml_file),
                        attachment.get("attachment_filename", ""),
                        attachment.get("original_text", "")[:1000],  # Truncate for testing
                        email_meta.get("from", ""),
                        email_meta.get("to", ""),
                        email_meta.get("subject", ""),
                        email_meta.get("date", "")
                    ))
                    
                    logger.info(f"Stored attachment {i+1}: {attachment.get('attachment_filename', '')}")
                
                conn.commit()
                
                # Query back the data
                cursor = conn.execute("SELECT * FROM email_documents WHERE eml_file_path = ?", (str(eml_file),))
                rows = cursor.fetchall()
                
                logger.info(f"Retrieved {len(rows)} records from database")
                print("\n" + "="*80)
                print("DATABASE STORAGE TEST RESULTS")
                print("="*80)
                print(f"Database: {db_path}")
                print(f"Records stored: {len(rows)}")
                print("\nStored email documents:")
                print("-" * 60)
                for row in rows:
                    print(f"ID: {row[0]}")
                    print(f"EML File: {Path(row[1]).name}")
                    print(f"Attachment: {row[2]}")
                    print(f"From: {row[4][:50]}..." if row[4] else "")
                    print(f"Subject: {row[6][:50]}..." if row[6] else "")
                    print(f"Content Preview: {row[3][:100]}..." if row[3] else "")
                    print(f"Created: {row[8]}")
                    print("-" * 60)
                
                # Show how to search the database
                print("\nSEARCH EXAMPLES:")
                print("="*40)
                
                # Search by content
                search_cursor = conn.execute("""
                SELECT attachment_filename, email_subject 
                FROM email_documents 
                WHERE content_text LIKE ? 
                LIMIT 5
                """, ("%Familiensache%",))
                
                search_results = search_cursor.fetchall()
                print(f"\nDocuments containing 'Familiensache': {len(search_results)}")
                for result in search_results:
                    print(f"  - {result[0]} (Subject: {result[1][:40]}...)")
                
                # Search by sender
                sender_cursor = conn.execute("""
                SELECT COUNT(*), email_from 
                FROM email_documents 
                GROUP BY email_from
                """)
                
                sender_results = sender_cursor.fetchall()
                print(f"\nDocuments by sender:")
                for count, sender in sender_results:
                    sender_display = sender[:50] + "..." if len(sender) > 50 else sender
                    print(f"  - {count} documents from: {sender_display}")
                
                print(f"\n✅ Database storage test completed successfully!")
                print(f"   Database file: {db_path}")
                print(f"   You can query this database using any SQLite tool.")
                
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_database_storage())