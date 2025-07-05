#!/usr/bin/env python3
"""
Comprehensive test script for the document ingestion pipeline.
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.ingestion import IngestionOrchestrator
from src.core.events import FileEvent, FileEventType
from src.database.database import DocumentStore
from src.core.mcp_client import get_mcp_client
from src.core.logging_config import setup_logging


class TestStopHandler:
    """Custom log handler that stops the test on WARNING or ERROR."""
    
    def __init__(self):
        self.should_stop = False
    
    def emit(self, record):
        """Handle log records and check for stop conditions."""
        try:
            if hasattr(record, 'level'):
                level_name = record.level.name
            else:
                level_name = getattr(record, 'levelname', 'UNKNOWN')
                
            if level_name in ['WARNING', 'ERROR']:
                message = str(record.message) if hasattr(record, 'message') else str(record)
                print(f"[TestStopHandler] {level_name} detected - stopping test!")
                print(f"[TestStopHandler] Message: {message}")
                self.should_stop = True
        except Exception as e:
            print(f"[TestStopHandler] Error in handler: {e}")
            pass


def is_hidden_file(file_path: Path) -> bool:
    """Check if a file is hidden or a system file."""
    # Hidden files (start with dot)
    if file_path.name.startswith('.'):
        return True
    
    # Common system files
    system_files = {
        '.DS_Store', '._.DS_Store', 'Thumbs.db', 'desktop.ini',
        '.directory', '.localized', '.fseventsd', '.Spotlight-V100',
        '.Trashes', '.TemporaryItems', '.DocumentRevisions-V100'
    }
    
    if file_path.name in system_files:
        return True
    
    # macOS resource fork files
    if file_path.name.startswith('._'):
        return True
    
    return False

async def run_ingestion_test():
    """
    Runs the full ingestion test, processing all files in the specified
    directory and reporting on the results.
    """
    # Setup global logging configuration first
    setup_logging()
    
    # Set up the test stop handler to capture all WARNING and ERROR messages
    test_handler = TestStopHandler()
    # Use DEBUG level to ensure we capture everything, then filter in the handler
    logger.add(test_handler.emit, level="DEBUG")
    
    test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
    if not test_dir.exists():
        logger.error(f"Test directory does not exist: {test_dir}")
        return

    # Filter out hidden files and system files
    all_files = [f for f in test_dir.iterdir() if f.is_file() and not is_hidden_file(f)]
    total_files = len(all_files)
    logger.info(f"Found {total_files} files to process in {test_dir} (hidden files filtered out)")

    # Show file types that will be processed
    file_types = {}
    for f in all_files:
        ext = f.suffix.lower()
        file_types[ext] = file_types.get(ext, 0) + 1
    
    logger.info("File types to be processed:")
    for ext, count in sorted(file_types.items()):
        logger.info(f"  {ext or '(no extension)'}: {count} files")

    document_store = DocumentStore()
    orchestrator = IngestionOrchestrator(document_store)
    
    start_time = time.time()
    logger.info(f"Starting comprehensive ingestion test at {datetime.now()}")

    processed_files = 0
    failed_to_store = []
    failed_to_process = []

    for file_path in all_files:
        # Check if test should stop due to critical warnings/errors
        if test_handler.should_stop:
            logger.error("Test stopped due to critical warnings/errors")
            break
            
        try:
            event = FileEvent(
                event_type=FileEventType.CREATED,
                file_path=file_path,
                timestamp=datetime.now()
            )
            doc_id = await orchestrator.process_file_event(event)
            if doc_id:
                processed_files += 1
                logger.info(f"({processed_files}/{total_files}) Successfully processed and stored: {file_path.name} (ID: {doc_id})")
            else:
                logger.warning(f"({processed_files}/{total_files}) Processed but failed to store: {file_path.name}")
                failed_to_store.append(file_path.name)
                logger.error("Stopping test due to storage failure.")
                break

        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            failed_to_process.append(file_path.name)

    await orchestrator.cleanup()
    
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Ingestion test finished at {datetime.now()}")
    logger.info(f"Total processing time: {duration:.2f} seconds")

    logger.info("--- Comprehensive Test Summary ---")
    logger.info(f"Total files in directory: {total_files}")
    logger.info(f"Successfully processed and stored files: {processed_files}")
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
    
    # Check if test was stopped due to warnings/errors
    if test_handler.should_stop:
        logger.error("TEST FAILED: Stopped due to WARNING or ERROR")
        return False
    else:
        logger.success("TEST PASSED: No warnings or errors detected")
        return True


async def verify_database():
    """Verify the database contents after ingestion."""
    async with get_mcp_client() as client:
        result = await client.read_query("SELECT COUNT(*) as count FROM documents")
        total_docs = result[0]['count'] if result else 0
        logger.info(f"Total entries in database: {total_docs}")

        result = await client.read_query("SELECT document_type, COUNT(*) as count FROM documents GROUP BY document_type")
        logger.info("Database entries by document type:")
        for row in result:
            logger.info(f"  - {row['document_type']}: {row['count']}")


async def main():
    """Main function that runs the test and verifies the database."""
    # Run the ingestion test
    success = await run_ingestion_test()
    
    if success:
        # Verify database contents
        await verify_database()
    
    return success


if __name__ == "__main__":
    import sys
    
    # Run the main function
    success = asyncio.run(main())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)