import time
from loguru import logger
from src.core.logging_config import setup_logging
from src.core.config import settings
from src.core.file_watcher import FileWatcher
from src.core.queue_processor import QueueProcessor
from src.core.document_store import DocumentStore, initialize_database
from src.core.ingestion import IngestionOrchestrator

def main():
    """Main function to start the file browser application."""
    setup_logging()

    # Initialize database
    initialize_database()
    document_store = DocumentStore()

    # Initialize ingestion orchestrator
    orchestrator = IngestionOrchestrator(document_store)

    # Initialize file watcher and queue processor
    file_watcher = FileWatcher(watch_directories=settings.watch_directories)

    queue_processor = QueueProcessor(
        file_watcher=file_watcher,
        process_callback=orchestrator.process_file_event
    )

    try:
        file_watcher.start()
        queue_processor.start()
        logger.info("File watcher and queue processor started.")

        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        queue_processor.stop()
        file_watcher.stop()
        logger.info("Application shut down gracefully.")

if __name__ == "__main__":
    main()