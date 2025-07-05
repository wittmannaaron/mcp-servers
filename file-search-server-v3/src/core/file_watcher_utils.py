"""
Utility classes and functions for file watching.
"""

import fnmatch
import queue
import threading
from pathlib import Path
from typing import Set, List, Optional
from datetime import datetime

from loguru import logger

from src.core.events import FileEvent, FileEventType


class FileFilter:
    """Handles file filtering logic."""

    def __init__(
        self,
        file_extensions: Set[str],
        max_file_size: int,
        ignore_patterns: List[str]
    ):
        self.file_extensions = file_extensions
        self.max_file_size = max_file_size
        self.ignore_patterns = ignore_patterns

    def should_process_file(self, file_path: Path) -> bool:
        """Check if a file should be processed based on filters."""
        # Check if it's a file (not directory)
        if not file_path.is_file():
            return False

        # Check file extension
        if self.file_extensions and file_path.suffix.lower() not in self.file_extensions:
            return False

        # Check ignore patterns
        for pattern in self.ignore_patterns:
            # Check filename against pattern
            if fnmatch.fnmatch(file_path.name, pattern):
                return False

            # Check each path component against pattern (for directory patterns like 'node_modules', '.git')
            for part in file_path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return False

            # Also check against full path for absolute patterns
            if fnmatch.fnmatch(str(file_path), pattern):
                return False

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                logger.warning(f"Skipping large file: {file_path} ({file_size} bytes)")
                return False
        except OSError as e:
            logger.warning(f"Cannot access file {file_path}: {e}")
            return False

        return True


class EventDeduplicator:
    """Handles event deduplication."""

    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self._processed_events = set()
        self._lock = threading.Lock()

    def is_duplicate(self, file_event: FileEvent) -> bool:
        """Check if event is a duplicate."""
        with self._lock:
            event_hash = hash(file_event)
            if event_hash in self._processed_events:
                return True

            self._processed_events.add(event_hash)

            # Clean up old processed events to prevent memory growth
            if len(self._processed_events) > self.max_events:
                self._processed_events.clear()

            return False


class EventQueue:
    """Manages the event queue with safety checks."""

    def __init__(self, maxsize: int):
        self.queue: queue.Queue[FileEvent] = queue.Queue(maxsize=maxsize)
        self.deduplicator = EventDeduplicator()
        self.maxsize = maxsize  # For compatibility with tests

    def put_event(self, file_event: FileEvent) -> bool:
        """Add event to queue with deduplication."""
        if self.deduplicator.is_duplicate(file_event):
            return False

        try:
            self.queue.put_nowait(file_event)
            logger.debug(f"Queued event: {file_event.event_type.value} - {file_event.file_path}")
            return True
        except queue.Full:
            logger.warning("Event queue is full, dropping event")
            return False

    def put(self, file_event: FileEvent) -> None:
        """Add event to queue (compatibility method)."""
        self.put_event(file_event)

    def get_event(self, timeout: Optional[float] = None) -> Optional[FileEvent]:
        """Get event from queue."""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_size(self) -> int:
        """Get queue size."""
        return self.queue.qsize()

    def clear(self) -> None:
        """Clear all events from queue."""
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break


def create_file_event(
    event_type: FileEventType,
    file_path: Path,
    old_path: Optional[Path] = None
) -> FileEvent:
    """Create a FileEvent object."""
    try:
        file_size = file_path.stat().st_size if file_path.exists() else None
    except OSError:
        file_size = None

    return FileEvent(
        event_type=event_type,
        file_path=file_path,
        timestamp=datetime.now(),
        old_path=old_path,
        file_size=file_size
    )


def validate_watch_directories(directories: List[str]) -> List[Path]:
    """Validate and convert watch directories to Path objects."""
    valid_dirs = []

    for directory in directories:
        dir_path = Path(directory).expanduser().resolve()
        if dir_path.exists() and dir_path.is_dir():
            valid_dirs.append(dir_path)
            logger.info(f"Monitoring directory (absolute path): {dir_path}")
        else:
            logger.warning(f"Skipping invalid or non-existent directory: {directory}")

    return valid_dirs


def log_observer_type(use_polling: bool, polling_interval: float) -> None:
    """Log the type of observer being used."""
    if use_polling:
        logger.info(f"Using polling observer with {polling_interval}s interval")
    else:
        logger.info("Using native file system observer")