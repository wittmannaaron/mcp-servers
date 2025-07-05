#!/usr/bin/env python3
"""
Test script for the document ingestion pipeline, focusing on .eml files.
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
import clear_database as db_clear

async def run_eml_ingestion_test():
    """
    Runs the EML ingestion test, processing only .eml files in the specified
    directory and reporting on the results.
    """
    # Clear the database before running the test
    logger.info("Clearing the database before the test...")
    await db_clear.main()
    logger.info("Database cleared.")
    
    test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
    if not test_dir.exists():
        logger.error(f"Test directory does not exist: {test_dir}")
        return

    eml_files = [f for f in test_dir.glob("*.eml")]
    total_files = len(eml_files)
    logger.info(f"Found {total_files} .eml files to process in {test_dir}")

    document_store = DocumentStore()
    orchestrator = IngestionOrchestrator(document_store)
    
    start_time = time.time()
    logger.info(f"Starting EML ingestion test at {datetime.now()}")

    processed_files = 0
    failed_to_store = []
    failed_to_process = []

    for file_path in eml_files:
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

    logger.info("--- Test Summary ---")
    logger.info(f"Total .eml files to process: {total_files}")
    logger.info(f"Successfully processed and stored: {processed_files}")
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

    # Final database verification
    async with get_mcp_client() as client:
        result = await client.read_query("SELECT COUNT(*) as count FROM documents")
        total_docs = result[0]['count'] if result else 0
        logger.info(f"Total entries in database: {total_docs}")

        result = await client.read_query("SELECT document_type, COUNT(*) as count FROM documents GROUP BY document_type")
        logger.info("Database entries by document type:")
        for row in result:
            logger.info(f"  - {row['document_type']}: {row['count']}")

        # Verify that some files have multiple entries
        multi_entry_query = """
            SELECT file_path, COUNT(*) as count
            FROM documents
            GROUP BY file_path
            HAVING COUNT(*) > 1
        """
        multi_entry_result = await client.read_query(multi_entry_query)
        if multi_entry_result:
            logger.success(f"SUCCESS: Found {len(multi_entry_result)} files with multiple entries (EML + Attachments).")
            for row in multi_entry_result:
                logger.info(f"  - {Path(row['file_path']).name}: {row['count']} entries")
        else:
            logger.error("FAILURE: No files with multiple entries were found. The main fix is not working.")

if __name__ == "__main__":
    asyncio.run(run_eml_ingestion_test())