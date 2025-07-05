"""
Queue processor for handling file events from the file watcher.
Implements worker pool pattern for concurrent processing.
"""

import threading
import time
from typing import List, Callable, Optional, Any, Coroutine
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import anyio

from loguru import logger

from src.core.simple_config import settings
from src.core.events import FileEvent
from src.core.file_watcher import FileWatcher
from src.core.queue_utils import (
    ProcessingStats, QueueMonitor, FutureManager,
    log_processing_error, log_processing_success, log_processing_start
)


class QueueProcessor:
    """Processes file events from the file watcher queue."""

    def __init__(
        self,
        file_watcher: FileWatcher,
        process_callback: Callable[[FileEvent], Coroutine[Any, Any, Any]],
        worker_threads: Optional[int] = None,
        batch_size: Optional[int] = None,
        error_callback: Optional[Callable[[FileEvent, Exception], None]] = None
    ):
        self.file_watcher = file_watcher
        self.process_callback = process_callback
        self.error_callback = error_callback
        self.worker_threads = worker_threads or settings.worker_threads
        self.batch_size = batch_size or settings.batch_size

        self._executor: Optional[ThreadPoolExecutor] = None
        self._processing = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stats = ProcessingStats()
        self._queue_monitor = QueueMonitor(file_watcher, self.batch_size)
        self._future_manager = FutureManager()

    def start(self) -> None:
        """Start processing events from the queue."""
        if self._processing:
            logger.warning("Queue processor is already running")
            return

        self._processing = True
        self._stats = ProcessingStats(start_time=datetime.now())

        # Create thread pool
        self._executor = ThreadPoolExecutor(
            max_workers=self.worker_threads,
            thread_name_prefix="queue-worker"
        )

        # Start monitor thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_queue,
            name="queue-monitor"
        )
        self._monitor_thread.start()

        logger.info(f"Queue processor started with {self.worker_threads} workers")

    def stop(self, wait: bool = True) -> None:
        """Stop processing events."""
        if not self._processing:
            return

        self._queue_monitor.stop()

        if self._monitor_thread and wait:
            self._monitor_thread.join()

        if self._executor:
            self._executor.shutdown(wait=wait)

        self._processing = False
        logger.info("Queue processor stopped")

    def _monitor_queue(self) -> None:
        """Monitor the queue and submit events for processing."""
        while not self._queue_monitor.should_stop():
            try:
                # Get batch of events
                batch = self._queue_monitor.get_batch()

                if batch:
                    self._process_batch(batch)

                # Clean up completed futures
                self._future_manager.cleanup_completed()

            except Exception as e:
                logger.opt(exception=True).error("Error in queue monitor")

    def _process_batch(self, batch: List[FileEvent]) -> None:
        """Submit a batch of events for processing."""
        for event in batch:
            future = self._executor.submit(self._process_event, event)
            self._future_manager.add_future(future)

    def _process_event(self, event: FileEvent) -> None:
        """Process a single event."""
        self._stats.total_processed += 1

        try:
            log_processing_start(event.event_type.value, str(event.file_path))

            # Call the async processing callback
            anyio.run(self.process_callback, event)

            self._stats.successful += 1
            log_processing_success(str(event.file_path))

        except Exception as e:
            self._stats.failed += 1
            log_processing_error(str(event.file_path), e)

            # Call error callback if provided
            if self.error_callback:
                try:
                    self.error_callback(event, e)
                except Exception:
                    logger.opt(exception=True).error("Error in error callback")

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all queued events to be processed."""
        start_time = time.time()

        while True:
            # Check if queue is empty and all futures are done
            if (self.file_watcher.get_queue_size() == 0 and
                self._future_manager.get_pending_count() == 0):
                return True

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return False

            time.sleep(0.1)

    def get_stats(self) -> ProcessingStats:
        """Get processing statistics."""
        return self._stats

    def is_processing(self) -> bool:
        """Check if the processor is running."""
        return self._processing

    def get_pending_count(self) -> int:
        """Get number of pending events."""
        return (self.file_watcher.get_queue_size() +
                self._future_manager.get_pending_count())

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()