#!/usr/bin/env python3
"""
ZIP Ingestion Test Script
Tests ZIP file processing to ensure multiple entries are created correctly.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.ingestion import IngestionOrchestrator
from src.database.database import DocumentStore
from src.core.events import FileEvent, FileEventType
from src.core.logging_config import setup_logging
from src.core.mcp_client import get_mcp_client

async def run_zip_ingestion_test():
    """Run ZIP ingestion test to validate multiple entries per ZIP file."""
    
    # Setup logging
    setup_logging()
    
    logger.info("Clearing the database before the test...")
    # Clear database first
    async with get_mcp_client() as client:
        try:
            await client.write_query("DROP TABLE IF EXISTS documents")
            await client.write_query("DROP TABLE IF EXISTS documents_fts")
            logger.info("'documents' table dropped.")
            logger.info("'documents_fts' table dropped.")
        except Exception as e:
            logger.warning(f"Error dropping tables: {e}")
    logger.info("Database cleared.")
    
    # Test directory
    test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
    
    # Find ZIP files
    zip_files = list(test_dir.glob("*.zip"))
    logger.info(f"Found {len(zip_files)} .zip files to process in {test_dir}")
    
    if not zip_files:
        logger.warning("No .zip files found for testing!")
        return
    
    # Initialize orchestrator
    document_store = DocumentStore()
    orchestrator = IngestionOrchestrator(document_store)
    
    start_time = datetime.now()
    logger.info(f"Starting ZIP ingestion test at {start_time}")
    
    processed_count = 0
    stored_count = 0
    failed_count = 0
    
    try:
        # Process each ZIP file
        for i, zip_file in enumerate(zip_files, 1):
            logger.info(f"Processing event: created for {zip_file}")
            
            # Create file event
            event = FileEvent(
                event_type=FileEventType.CREATED,
                file_path=zip_file,
                timestamp=datetime.now()
            )
            
            # Process the file
            try:
                doc_id = await orchestrator.process_file_event(event)
                processed_count += 1
                
                if doc_id:
                    stored_count += 1
                    logger.info(f"({i}/{len(zip_files)}) Successfully processed and stored: {zip_file.name} (ID: {doc_id})")
                else:
                    logger.warning(f"({i}/{len(zip_files)}) Processed but failed to store: {zip_file.name}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"({i}/{len(zip_files)}) Failed to process: {zip_file.name} - {e}")
    
    finally:
        # Cleanup
        await orchestrator.cleanup()
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Ingestion test finished at {end_time}")
        logger.info(f"Total processing time: {processing_time:.2f} seconds")
        
        logger.info("--- Test Summary ---")
        logger.info(f"Total .zip files to process: {len(zip_files)}")
        logger.info(f"Successfully processed and stored: {stored_count}")
        logger.info(f"Processed but failed to store: {processed_count - stored_count}")
        if failed_count > 0:
            logger.error(f"Failed to process: {failed_count}")
        else:
            logger.info(f"Failed to process: {failed_count}")
        
        # Check database entries
        async with get_mcp_client() as client:
            try:
                # Count total entries
                count_result = await client.read_query("SELECT COUNT(*) as total FROM documents")
                total_entries = count_result[0]['total'] if count_result else 0
                logger.info(f"Total entries in database: {total_entries}")
                
                # Count by document type
                type_result = await client.read_query("SELECT document_type, COUNT(*) as count FROM documents GROUP BY document_type")
                logger.info("Database entries by document type:")
                for row in type_result:
                    logger.info(f"  - {row['document_type']}: {row['count']}")
                
                # Check for ZIP files with multiple entries (ZIP + archived documents)
                path_result = await client.read_query("SELECT file_path, COUNT(*) as count FROM documents GROUP BY file_path HAVING COUNT(*) > 1")
                if path_result:
                    logger.success(f"SUCCESS: Found {len(path_result)} files with multiple entries (ZIP + Archived Documents).")
                    for row in path_result:
                        zip_name = Path(row['file_path']).name
                        logger.info(f"  - {zip_name}: {row['count']} entries")
                else:
                    logger.warning("WARNING: No ZIP files found with multiple entries. This might indicate an issue.")
                    
            except Exception as e:
                logger.error(f"Error checking database: {e}")

if __name__ == "__main__":
    asyncio.run(run_zip_ingestion_test())