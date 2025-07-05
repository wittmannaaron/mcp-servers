"""
File system event handler for processing watchdog events.
"""

import threading
from pathlib import Path
from typing import Optional
from datetime import datetime

from watchdog.events import FileSystemEventHandler, FileSystemEvent

from src.core.events import FileEvent, FileEventType
from src.core.file_watcher_utils import FileFilter, create_file_event


class FileEventHandler(FileSystemEventHandler):
    """Handles file system events and filters them based on configuration."""

    def __init__(
        self,
        event_queue,
        file_extensions=None,
        max_file_size=None,
        ignore_patterns=None,
        file_filter=None
    ):
        # Support both old and new interfaces
        if file_filter is not None:
            self.file_filter = file_filter
            self.event_queue = event_queue
        else:
            # Legacy interface for tests
            self.file_filter = FileFilter(
                file_extensions or set(),
                max_file_size or 1024*1024*1024,
                ignore_patterns or []
            )
            self.event_queue = event_queue
            # Add legacy methods for tests
            self._processing_lock = threading.Lock()
            self._processed_events = set()

    def _should_process_file(self, file_path: Path) -> bool:
        """Legacy method for tests."""
        return self.file_filter.should_process_file(file_path)

    def _queue_event(self, file_event: FileEvent) -> None:
        """Legacy method for tests."""
        if hasattr(self.event_queue, 'put_event'):
            self.event_queue.put_event(file_event)
        else:
            # Legacy queue interface
            with self._processing_lock:
                event_hash = hash(file_event)
                if event_hash in self._processed_events:
                    return
                try:
                    self.event_queue.put_nowait(file_event)
                    self._processed_events.add(event_hash)
                    if len(self._processed_events) > 10000:
                        self._processed_events.clear()
                except:
                    pass

    def _create_and_queue_event(
        self,
        event_type: FileEventType,
        file_path: Path,
        old_path: Optional[Path] = None
    ) -> None:
        """Create and queue a file event if it should be processed."""
        if not self.file_filter.should_process_file(file_path):
            return

        file_event = create_file_event(event_type, file_path, old_path)
        self.event_queue.put_event(file_event)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        self._create_and_queue_event(FileEventType.CREATED, file_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        self._create_and_queue_event(FileEventType.MODIFIED, file_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if event.is_directory:
            return

        # For deleted files, we can't check if it should be processed
        # So we create the event directly
        file_event = FileEvent(
            event_type=FileEventType.DELETED,
            file_path=Path(event.src_path),
            timestamp=datetime.now()
        )
        self.event_queue.put_event(file_event)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename events."""
        if event.is_directory:
            return

        old_path = Path(event.src_path)
        new_path = Path(event.dest_path)

        self._create_and_queue_event(FileEventType.MOVED, new_path, old_path=old_path)