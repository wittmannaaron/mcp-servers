#!/usr/bin/env python3
"""
Robust ZIP Ingestion Test Script
Tests ZIP file processing with automatic stop on WARNING/ERROR.
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
from loguru import logger
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.ingestion import IngestionOrchestrator
from src.database.database import DocumentStore
from src.core.events import FileEvent, FileEventType
from src.core.logging_config import setup_logging
from src.core.mcp_client import get_mcp_client
import clear_database as db_clear

class TestStopHandler(logging.Handler):
    """Custom log handler that stops test on WARNING or ERROR."""
    
    def __init__(self):
        super().__init__()
        self.should_stop = False
        self.warning_count = 0
        self.error_count = 0
        
    def emit(self, record):
        if record.levelname in ['WARNING', 'ERROR']:
            if record.levelname == 'WARNING':
                self.warning_count += 1
                # Only stop on specific warnings that indicate real problems
                if any(keyword in record.getMessage().lower() for keyword in [
                    'failed to parse', 'unparseable', 'fallback metadata', 'json'
                ]):
                    logger.critical(f"STOPPING TEST: Critical warning detected - {record.getMessage()}")
                    self.should_stop = True
            elif record.levelname == 'ERROR':
                self.error_count += 1
                logger.critical(f"STOPPING TEST: Error detected - {record.getMessage()}")
                self.should_stop = True

async def run_robust_zip_test():
    """Run ZIP ingestion test with automatic stop on critical issues."""
    
    # Setup logging
    setup_logging()
    
    # Add our custom handler to catch warnings/errors
    test_handler = TestStopHandler()
    test_handler.setLevel(logging.WARNING)
    
    # Get the loguru logger and add our handler
    logger.add(test_handler.emit, level="WARNING", format="{message}")
    
    # Clear the database before running the test
    logger.info("Clearing the database before the test...")
    await db_clear.main()
    logger.info("Database cleared.")
    
    # Test directory
    test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
    if not test_dir.exists():
        logger.error(f"Test directory does not exist: {test_dir}")
        return
    
    # Find ZIP files
    zip_files = list(test_dir.glob("*.zip"))
    total_files = len(zip_files)
    logger.info(f"Found {total_files} .zip files to process in {test_dir}")
    
    if not zip_files:
        logger.warning("No .zip files found for testing!")
        return
    
    # Initialize orchestrator
    document_store = DocumentStore()
    orchestrator = IngestionOrchestrator(document_store)
    
    start_time = time.time()
    logger.info(f"Starting robust ZIP ingestion test at {datetime.now()}")
    
    processed_count = 0
    stored_count = 0
    failed_count = 0
    failed_to_store = []
    failed_to_process = []
    
    try:
        # Process each ZIP file
        for i, zip_file in enumerate(zip_files, 1):
            # Check if we should stop due to warnings/errors
            if test_handler.should_stop:
                logger.critical("Test stopped due to critical warning/error!")
                break
                
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
                
                # Check again after processing
                if test_handler.should_stop:
                    logger.critical("Test stopped due to critical warning/error during processing!")
                    break
                
                if doc_id:
                    stored_count += 1
                    logger.info(f"({i}/{total_files}) Successfully processed and stored: {zip_file.name} (ID: {doc_id})")
                else:
                    logger.warning(f"({i}/{total_files}) Processed but failed to store: {zip_file.name}")
                    failed_to_store.append(zip_file.name)
                    logger.error("Stopping test due to storage failure.")
                    break
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"({i}/{total_files}) Failed to process: {zip_file.name} - {e}")
                failed_to_process.append(zip_file.name)
                break  # Stop on any processing exception
    
    finally:
        # Cleanup
        await orchestrator.cleanup()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Robust test finished at {datetime.now()}")
        logger.info(f"Total processing time: {processing_time:.2f} seconds")
        
        # Test Summary
        logger.info("--- Robust Test Summary ---")
        logger.info(f"Total .zip files to process: {total_files}")
        logger.info(f"Successfully processed and stored: {stored_count}")
        logger.info(f"Processed but failed to store: {len(failed_to_store)}")
        if failed_to_store:
            logger.warning("Files that failed to store:")
            for f in failed_to_store:
                logger.warning(f"  - {f}")
        logger.info(f"Failed to process: {len(failed_to_process)}")
        if failed_to_process:
            logger.warning("Files that failed to process:")
            for f in failed_to_process:
                logger.warning(f"  - {f}")
        
        # Log handler statistics
        logger.info(f"Test handler detected {test_handler.warning_count} warnings and {test_handler.error_count} errors")
        
        # Check database entries only if we processed files successfully
        if stored_count > 0:
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
        
        # Final status
        if test_handler.should_stop:
            logger.critical("TEST FAILED: Stopped due to critical warnings/errors")
            return False
        elif stored_count == total_files:
            logger.success("TEST PASSED: All ZIP files processed successfully")
            return True
        else:
            logger.warning(f"TEST PARTIAL: Only {stored_count}/{total_files} files processed successfully")
            return False

if __name__ == "__main__":
    success = asyncio.run(run_robust_zip_test())
    sys.exit(0 if success else 1)