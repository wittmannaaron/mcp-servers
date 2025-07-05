# File System Monitoring Module

This module implements the file system monitoring functionality for the FileBrowser project using the watchdog library.

## Components

### 1. `events.py`
Defines the event types and data structures:
- `FileEventType`: Enum for event types (CREATED, MODIFIED, DELETED, MOVED)
- `FileEvent`: Data class representing a file system event

### 2. `config.py`
Configuration management using Pydantic:
- Environment variable support
- File monitoring settings (directories, extensions, size limits)
- Queue and worker thread configuration
- Platform-specific settings (polling vs native observers)

### 3. `file_watcher.py`
Main file monitoring implementation:
- `FileEventHandler`: Processes raw watchdog events and filters files
- `FileWatcher`: Manages file system observers and event queue
  - Supports both native (FSEvents/inotify) and polling observers
  - Implements pause/resume functionality
  - Thread-safe event queueing with deduplication

### 4. `queue_processor.py`
Event processing implementation:
- `QueueProcessor`: Processes individual events using a worker pool
- `BatchProcessor`: Alternative processor for batch operations
- `ProcessingStats`: Tracks processing statistics

## Usage Example

```python
from src.core.file_watcher import FileWatcher
from src.core.queue_processor import QueueProcessor

def process_event(event):
    print(f"Processing {event.event_type.value}: {event.file_path}")

# Create and start file watcher
watcher = FileWatcher(
    watch_directories=["/path/to/watch"],
    file_extensions={'.txt', '.pdf', '.doc'},
    ignore_patterns=['*.tmp', '.*']
)

# Create processor
processor = QueueProcessor(
    file_watcher=watcher,
    process_callback=process_event,
    worker_threads=4
)

# Start monitoring
with watcher, processor:
    # Monitor files...
    pass
```

## Configuration

The module can be configured via environment variables or `.env` file:

```bash
# Directories to watch (comma-separated)
WATCH_DIRECTORIES=/home/user/Documents,/home/user/Downloads

# File extensions to monitor (comma-separated)
FILE_EXTENSIONS=.txt,.pdf,.doc,.docx,.md

# Maximum file size in MB
MAX_FILE_SIZE_MB=100

# Worker threads for processing
WORKER_THREADS=4

# Use polling observer instead of native
USE_POLLING_OBSERVER=false
```

## Platform Support

- **macOS**: Uses FSEvents for efficient file monitoring
- **Linux**: Uses inotify for native file system events
- **Fallback**: Polling observer available for compatibility

## Testing

Run unit tests:
```bash
pytest tests/unit/test_file_watcher.py -v
```

Run integration tests:
```bash
pytest tests/unit/test_file_watcher.py -v -m integration
```

## Demo

A demo script is available in `examples/file_watcher_demo.py`:
```bash
python examples/file_watcher_demo.py /path/to/watch