"""
Utility classes and functions for queue processing.
"""

import threading
import time
from typing import List, Optional, Any
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


@dataclass
class ProcessingStats:
    """Statistics for queue processing."""
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    start_time: Optional[datetime] = None

    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_processed == 0:
            return 0.0
        return self.successful / self.total_processed

    def processing_time(self) -> float:
        """Calculate total processing time in seconds."""
        if not self.start_time:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()


class QueueMonitor:
    """Monitors queue and manages processing lifecycle."""

    def __init__(self, file_watcher, batch_size: int):
        self.file_watcher = file_watcher
        self.batch_size = batch_size
        self._stop_event = threading.Event()

    def should_stop(self) -> bool:
        """Check if monitoring should stop."""
        return self._stop_event.is_set()

    def stop(self) -> None:
        """Signal to stop monitoring."""
        self._stop_event.set()

    def get_batch(self, timeout: float = 0.1) -> List[Any]:
        """Get a batch of events from the queue."""
        batch = []

        while not self.should_stop() and len(batch) < self.batch_size:
            event = self.file_watcher.get_event(timeout=timeout)
            if event:
                batch.append(event)
            else:
                break  # No more events available

        return batch


class FutureManager:
    """Manages futures for concurrent processing."""

    def __init__(self):
        self._futures: List[Future] = []
        self._lock = threading.Lock()

    def add_future(self, future: Future) -> None:
        """Add a future to track."""
        with self._lock:
            self._futures.append(future)

    def cleanup_completed(self) -> None:
        """Remove completed futures from tracking."""
        with self._lock:
            self._futures = [f for f in self._futures if not f.done()]

    def get_pending_count(self) -> int:
        """Get number of pending futures."""
        with self._lock:
            return len([f for f in self._futures if not f.done()])

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all futures to complete."""
        start_time = time.time()

        while True:
            with self._lock:
                if all(f.done() for f in self._futures):
                    return True

            if timeout and (time.time() - start_time) > timeout:
                return False

            time.sleep(0.1)


def log_processing_error(file_path: str, error: Exception) -> None:
    """Log processing error with context."""
    logger.opt(exception=True).error(f"Error processing {file_path}")


def log_processing_success(file_path: str) -> None:
    """Log successful processing."""
    logger.debug(f"Successfully processed: {file_path}")


def log_processing_start(event_type: str, file_path: str) -> None:
    """Log start of processing."""
    logger.debug(f"Processing event: {event_type} - {file_path}")