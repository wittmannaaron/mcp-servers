"""
Batch processor for handling file events in batches.
"""

import threading
import time
from typing import List, Callable, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from src.core.events import FileEvent
from src.core.file_watcher import FileWatcher
from src.core.queue_utils import QueueMonitor


class BatchProcessor:
    """Alternative processor that processes events in batches."""

    def __init__(
        self,
        file_watcher: FileWatcher,
        batch_callback: Callable[[List[FileEvent]], Any],
        batch_size: int = 10,
        batch_timeout: float = 5.0,
        worker_threads: int = 2
    ):
        self.file_watcher = file_watcher
        self.batch_callback = batch_callback
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.worker_threads = worker_threads

        self._executor: Optional[ThreadPoolExecutor] = None
        self._processing = False
        self._queue_monitor = QueueMonitor(file_watcher, batch_size)
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start batch processing."""
        if self._processing:
            return

        self._processing = True

        self._executor = ThreadPoolExecutor(
            max_workers=self.worker_threads,
            thread_name_prefix="batch-worker"
        )

        self._monitor_thread = threading.Thread(
            target=self._monitor_queue,
            name="batch-monitor"
        )
        self._monitor_thread.start()

        logger.info(f"Batch processor started with batch size {self.batch_size}")

    def stop(self, wait: bool = True) -> None:
        """Stop batch processing."""
        if not self._processing:
            return

        self._queue_monitor.stop()

        if self._monitor_thread and wait:
            self._monitor_thread.join()

        if self._executor:
            self._executor.shutdown(wait=wait)

        self._processing = False
        logger.info("Batch processor stopped")

    def _monitor_queue(self) -> None:
        """Monitor queue and process batches."""
        batch: List[FileEvent] = []
        last_batch_time = time.time()

        while not self._queue_monitor.should_stop():
            try:
                # Get event with short timeout
                event = self.file_watcher.get_event(timeout=0.1)

                if event:
                    batch.append(event)

                # Check if batch should be processed
                current_time = time.time()
                time_elapsed = current_time - last_batch_time

                if (len(batch) >= self.batch_size or
                    (batch and time_elapsed >= self.batch_timeout)):
                    self._executor.submit(self._process_batch, batch.copy())
                    batch.clear()
                    last_batch_time = current_time

            except Exception as e:
                logger.error(f"Error in batch monitor: {e}")

        # Process any remaining events
        if batch:
            self._process_batch(batch)

    def _process_batch(self, batch: List[FileEvent]) -> None:
        """Process a batch of events."""
        try:
            logger.debug(f"Processing batch of {len(batch)} events")
            self.batch_callback(batch)
            logger.debug(f"Batch processed successfully")
        except Exception as e:
            logger.error(f"Error processing batch: {e}")