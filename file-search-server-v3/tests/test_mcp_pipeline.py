#!/usr/bin/env python3
"""
Test the complete MCP-based document ingestion pipeline with email processing
This tests the actual production pipeline using the real filebrowser.db database
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.ingestion import IngestionOrchestrator
from src.core.events import FileEvent, FileEventType
from src.database.database import DocumentStore
from src.core.logging_config import setup_logging

async def test_mcp_email_pipeline():
    """Test the complete MCP-based email processing pipeline"""
    setup_logging()
    logger.info("Testing complete MCP-based email processing pipeline")
    
    # Initialize the actual document store and orchestrator
    document_store = DocumentStore()
    orchestrator = IngestionOrchestrator(document_store)
    
    try:
        # First, check current database state
        print("\n" + "="*80)
        print("CURRENT DATABASE STATE")
        print("="*80)
        
        # Use MCP to query current state
        from src.core.mcp_client import get_mcp_client
        
        async with get_mcp_client() as client:
            # Get current document count
            current_docs = await client.read_query("SELECT COUNT(*) as count FROM documents")
            print(f"📊 Current documents in database: {current_docs[0]['count']}")
            
            # Check for existing .eml files
            eml_docs = await client.read_query("SELECT COUNT(*) as count FROM documents WHERE file_path LIKE '%.eml'")
            print(f"📧 Existing .eml files: {eml_docs[0]['count']}")
            
            # Check recent documents
            recent_docs = await client.read_query("""
                SELECT filename, extension, created_at 
                FROM documents 
                ORDER BY indexed_at DESC 
                LIMIT 5
            """)
            print(f"\n📄 Recent documents:")
            for doc in recent_docs:
                print(f"   - {doc['filename']} ({doc['extension']}) - {doc['created_at']}")
        
        print(f"\n" + "="*80)
        print("TESTING EMAIL PROCESSING")
        print("="*80)
        
        # Test with specific .eml files
        test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
        
        # Test with the two files that have attachments
        test_files = [
            "Ihring ._. Ihring.eml",
            "Ihring ._. Ihring,  3 F 248_24 (Strreitwert).eml"
        ]
        
        processed_count = 0
        
        for filename in test_files:
            eml_file = test_dir / filename
            if not eml_file.exists():
                logger.warning(f"Test file not found: {eml_file}")
                continue
                
            logger.info(f"Processing: {filename}")
            print(f"\n🔄 Processing: {filename}")
            
            # Create file event and process through the actual pipeline
            event = FileEvent(
                event_type=FileEventType.CREATED,
                file_path=eml_file,
                timestamp=datetime.now()
            )
            
            # This will use the complete MCP-based pipeline
            await orchestrator.process_file_event(event)
            processed_count += 1
            
            print(f"✅ Completed processing: {filename}")
        
        print(f"\n" + "="*80)
        print("VERIFYING RESULTS IN DATABASE")
        print("="*80)
        
        # Wait a moment for processing to complete
        await asyncio.sleep(2)
        
        async with get_mcp_client() as client:
            # Check new document count
            new_docs = await client.read_query("SELECT COUNT(*) as count FROM documents")
            print(f"📊 Documents after processing: {new_docs[0]['count']}")
            
            # Look for newly added .eml related documents
            email_docs = await client.read_query("""
                SELECT id, filename, file_path, summary, categories, persons, created_at
                FROM documents 
                WHERE file_path LIKE '%Ihring%' 
                   OR filename LIKE '%BES_%'
                   OR file_path LIKE '%.eml'
                ORDER BY indexed_at DESC
                LIMIT 10
            """)
            
            print(f"\n📧 Email-related documents found: {len(email_docs)}")
            for doc in email_docs:
                print(f"\nID: {doc['id']}")
                print(f"📁 File: {doc['filename']}")
                print(f"📂 Path: {Path(doc['file_path']).name}")
                print(f"📝 Summary: {doc['summary'][:100] if doc['summary'] else 'No summary'}...")
                print(f"🏷️  Categories: {doc['categories'] if doc['categories'] else 'None'}")
                print(f"👥 Persons: {doc['persons'] if doc['persons'] else 'None'}")
                print(f"📅 Created: {doc['created_at']}")
                print("-" * 50)
            
            # Search for specific content
            search_results = await client.read_query("""
                SELECT filename, summary, categories
                FROM documents 
                WHERE original_text LIKE '%Familiensache%' 
                   OR summary LIKE '%court%'
                   OR categories LIKE '%legal%'
                ORDER BY indexed_at DESC
                LIMIT 5
            """)
            
            print(f"\n🔍 Documents with legal content: {len(search_results)}")
            for result in search_results:
                print(f"   📄 {result['filename']}")
                print(f"      Summary: {result['summary'][:80] if result['summary'] else 'No summary'}...")
                print(f"      Categories: {result['categories'] if result['categories'] else 'None'}")
        
        print(f"\n" + "="*80)
        print("TESTING ZIP FILE PROCESSING")
        print("="*80)
        
        # Test one ZIP file through the pipeline
        zip_file = test_dir / "Polizeiliche Mitteilung.zip"
        if zip_file.exists():
            print(f"🔄 Processing ZIP file: {zip_file.name}")
            
            event = FileEvent(
                event_type=FileEventType.CREATED,
                file_path=zip_file,
                timestamp=datetime.now()
            )
            
            await orchestrator.process_file_event(event)
            print(f"✅ Completed processing ZIP file")
            
            # Wait and check results
            await asyncio.sleep(2)
            
            async with get_mcp_client() as client:
                zip_docs = await client.read_query("""
                    SELECT filename, summary, file_path
                    FROM documents 
                    WHERE file_path LIKE '%Polizeiliche%'
                    ORDER BY indexed_at DESC
                    LIMIT 5
                """)
                
                print(f"\n📦 ZIP-related documents: {len(zip_docs)}")
                for doc in zip_docs:
                    print(f"   📄 {doc['filename']}")
                    print(f"      Path: {Path(doc['file_path']).name}")
                    if doc['summary']:
                        print(f"      Summary: {doc['summary'][:60]}...")
        
        print(f"\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        async with get_mcp_client() as client:
            final_count = await client.read_query("SELECT COUNT(*) as count FROM documents")
            
            # Get latest documents added
            latest_docs = await client.read_query("""
                SELECT filename, extension, categories, indexed_at
                FROM documents 
                ORDER BY indexed_at DESC 
                LIMIT 5
            """)
            
            print(f"📊 Final document count: {final_count[0]['count']}")
            print(f"📈 Documents processed in this test: {processed_count}")
            print(f"\n📄 Latest documents added:")
            for doc in latest_docs:
                print(f"   - {doc['filename']} ({doc['extension']}) - {doc['indexed_at']}")
                if doc['categories']:
                    print(f"     Categories: {doc['categories']}")
        
        print(f"\n✅ MCP Pipeline test completed successfully!")
        print(f"   Database: /Users/aaron/Projects/Simple_MCP_DB/filebrowser.db")
        print(f"   Use MCP tools to query the database for the processed documents")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    finally:
        await orchestrator.cleanup()

if __name__ == "__main__":
    asyncio.run(test_mcp_email_pipeline())