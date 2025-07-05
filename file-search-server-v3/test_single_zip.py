#!/usr/bin/env python3
"""
Single ZIP Test Script
Tests the problematic ZIP file to validate improved JSON parsing.
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

async def test_single_zip():
    """Test the problematic ZIP file specifically."""
    
    # Setup logging
    setup_logging()
    
    # Test the specific problematic file
    test_file = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958/Terminmitteilung 3 F 89323.zip")
    
    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return
    
    logger.info(f"Testing problematic ZIP file: {test_file.name}")
    
    # Initialize orchestrator
    document_store = DocumentStore()
    orchestrator = IngestionOrchestrator(document_store)
    
    try:
        # Create file event
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=test_file,
            timestamp=datetime.now()
        )
        
        # Process the file
        logger.info("Processing the problematic ZIP file...")
        doc_id = await orchestrator.process_file_event(event)
        
        if doc_id:
            logger.success(f"Successfully processed: {test_file.name} (ID: {doc_id})")
        else:
            logger.warning(f"Processed but failed to get ID: {test_file.name}")
            
    except Exception as e:
        logger.error(f"Failed to process: {test_file.name} - {e}")
    finally:
        await orchestrator.cleanup()

if __name__ == "__main__":
    asyncio.run(test_single_zip())