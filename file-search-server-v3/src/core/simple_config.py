"""
Simple configuration management without Pydantic dependencies.
MCP-compliant configuration using environment variables and defaults.
"""

import os
from pathlib import Path
from typing import List, Set

class SimpleConfig:
    """Simple configuration class using environment variables."""

    def __init__(self):
        # Application settings
        self.app_name = "FileBrowser"
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"
        self.log_file_path = Path(os.getenv("LOG_FILE_PATH", "logs/filebrowser.log"))
        self.log_file_rotation = os.getenv("LOG_FILE_ROTATION", "10 MB")
        self.log_file_retention = os.getenv("LOG_FILE_RETENTION", "10 days")

        # File monitoring settings
        watch_dirs_env = os.getenv("WATCH_DIRECTORIES", str(Path.home()))
        if "," in watch_dirs_env:
            self.watch_directories = [d.strip() for d in watch_dirs_env.split(",")]
        else:
            self.watch_directories = [watch_dirs_env]

        # Resolve paths to absolute
        self.watch_directories = [str(Path(d).expanduser().resolve()) for d in self.watch_directories]

        # File extensions
        self.file_extensions = {
            '.txt', '.md', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.ppt', '.pptx', '.odt', '.ods', '.odp', '.rtf', '.tex',
            '.html', '.xml', '.json', '.csv', '.pages', '.jpeg', '.jpg', '.png',
            '.eml'  # Email files
        }

        self.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
        self.ignore_patterns = [
            '.*', '__pycache__', '*.tmp', '*.temp', '*.cache',
            '*.log', 'node_modules', '.git', '.svn', '.hg'
        ]

        # Queue settings
        self.queue_max_size = int(os.getenv("QUEUE_MAX_SIZE", "10000"))
        self.worker_threads = int(os.getenv("WORKER_THREADS", "4"))
        self.batch_size = int(os.getenv("BATCH_SIZE", "10"))

        # Database settings
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./data/filebrowser.db")
        self.mcp_db_path = "data/filebrowser.db"
        self.mcp_server_directory = "docs/MCP-Servers-src/sqlite_MCP_Server"

        # LLM Configuration
        self.llm_request_timeout = float(os.getenv("LLM_REQUEST_TIMEOUT", "60.0"))
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4000"))

        # Ollama settings
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        self.ollama_base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Platform-specific settings
        self.use_polling_observer = os.getenv("USE_POLLING_OBSERVER", "false").lower() == "true"
        self.polling_interval = float(os.getenv("POLLING_INTERVAL", "1.0"))

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

# Create global settings instance
settings = SimpleConfig()