"""
Event types and data structures for file system monitoring.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


class FileEventType(Enum):
    """Types of file system events."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileEvent:
    """Represents a file system event."""
    event_type: FileEventType
    file_path: Path
    timestamp: datetime
    old_path: Optional[Path] = None  # For move events
    file_size: Optional[int] = None

    def __hash__(self):
        """Make FileEvent hashable for deduplication."""
        return hash((self.event_type, str(self.file_path), self.timestamp))

    def __eq__(self, other):
        """Compare FileEvents for equality."""
        if not isinstance(other, FileEvent):
            return False
        return (
            self.event_type == other.event_type and
            self.file_path == other.file_path and
            abs((self.timestamp - other.timestamp).total_seconds()) < 1
        )