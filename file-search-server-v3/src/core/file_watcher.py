"""
File system monitoring module using watchdog library.
Monitors directories for file changes and queues them for processing.
"""

import threading
from pathlib import Path
from typing import Set, Optional, List

from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from loguru import logger

from src.core.simple_config import settings
from src.core.events import FileEvent
from src.core.file_watcher_utils import (
    FileFilter, EventQueue, validate_watch_directories, log_observer_type
)
from src.core.file_event_handler import FileEventHandler


class FileWatcher:
    """Main file watcher that monitors directories for changes."""

    def __init__(
        self,
        watch_directories: Optional[List[str]] = None,
        file_extensions: Optional[Set[str]] = None,
        max_file_size: Optional[int] = None,
        ignore_patterns: Optional[List[str]] = None,
        use_polling: Optional[bool] = None,
        polling_interval: Optional[float] = None
    ):
        self.watch_directories = watch_directories or settings.watch_directories
        self.file_extensions = file_extensions or settings.file_extensions
        self.max_file_size = max_file_size or settings.max_file_size_bytes
        self.ignore_patterns = ignore_patterns or settings.ignore_patterns
        self.use_polling = use_polling if use_polling is not None else settings.use_polling_observer
        self.polling_interval = polling_interval or settings.polling_interval

        # Initialize components
        self.event_queue = EventQueue(maxsize=settings.queue_max_size)
        self.file_filter = FileFilter(
            self.file_extensions,
            self.max_file_size,
            self.ignore_patterns
        )

        self.observer: Optional[Observer] = None
        self._running = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Start in unpaused state

    def start(self) -> None:
        """Start monitoring file system changes."""
        if self._running:
            logger.warning("File watcher is already running")
            return

        # Create observer (polling or native)
        log_observer_type(self.use_polling, self.polling_interval)

        if self.use_polling:
            self.observer = PollingObserver(timeout=self.polling_interval)
        else:
            self.observer = Observer()

        # Create event handler
        event_handler = FileEventHandler(
            event_queue=self.event_queue,
            file_filter=self.file_filter
        )

        # Schedule watchers for each directory
        valid_dirs = validate_watch_directories(self.watch_directories)
        for dir_path in valid_dirs:
            self.observer.schedule(event_handler, str(dir_path), recursive=True)

        # Start observer
        self.observer.start()
        self._running = True
        logger.info("File watcher started")

    def stop(self) -> None:
        """Stop monitoring file system changes."""
        if not self._running:
            return

        if self.observer:
            self.observer.stop()
            self.observer.join()

        self._running = False
        logger.info("File watcher stopped")

    def pause(self) -> None:
        """Pause processing of file events."""
        self._pause_event.clear()
        logger.info("File watcher paused")

    def resume(self) -> None:
        """Resume processing of file events."""
        self._pause_event.set()
        logger.info("File watcher resumed")

    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self._running

    def is_paused(self) -> bool:
        """Check if the watcher is paused."""
        return not self._pause_event.is_set()

    def get_event(self, timeout: Optional[float] = None) -> Optional[FileEvent]:
        """Get the next event from the queue."""
        if not self._pause_event.is_set():
            return None

        return self.event_queue.get_event(timeout)

    def get_queue_size(self) -> int:
        """Get the current size of the event queue."""
        return self.event_queue.get_size()

    def clear_queue(self) -> None:
        """Clear all pending events from the queue."""
        self.event_queue.clear()
        logger.info("Event queue cleared")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()