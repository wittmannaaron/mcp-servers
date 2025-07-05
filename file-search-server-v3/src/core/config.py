"""
Configuration management for the FileBrowser application.
"""

import os
from pathlib import Path
from typing import List, Set, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    app_name: str = "FileBrowser"
    debug: bool = False
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: Path = Path("logs/filebrowser.log")
    log_file_rotation: str = "10 MB"
    log_file_retention: str = "10 days"

    # MCP Client Configuration (stdio-based)
    mcp_db_path: str = "src/database/filebrowser.db"
    mcp_server_directory: str = "docs/MCP-Servers-src/sqlite_MCP_Server"

    # LLM Configuration
    llm_request_timeout: float = 60.0
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4000

    # File monitoring settings
    watch_directories: List[str] = Field(
        default_factory=lambda: [str(Path.home())]
    )
    file_extensions: Set[str] = Field(
        default_factory=lambda: {
            '.txt', '.md', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.ppt', '.pptx', '.odt', '.ods', '.odp', '.rtf', '.tex',
            '.html', '.xml', '.json', '.csv', '.pages'
        }
    )
    max_file_size_mb: int = 100
    ignore_patterns: List[str] = Field(
        default_factory=lambda: [
            '.*', '__pycache__', '*.tmp', '*.temp', '*.cache',
            '*.log', 'node_modules', '.git', '.svn', '.hg'
        ]
    )

    # Queue settings
    queue_max_size: int = 10000
    worker_threads: int = 4
    batch_size: int = 10

    # Database settings
    database_url: str = "sqlite:///./data/filebrowser.db"

    # Platform-specific settings
    use_polling_observer: bool = Field(
        default=False,
        description="Use polling observer instead of native FSEvents/inotify"
    )
    polling_interval: float = Field(
        default=1.0,
        description="Polling interval in seconds when using polling observer"
    )

    # Ollama settings
    ollama_model: str = "llama3.2:latest"
    ollama_base_url: str = "http://localhost:11434"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("watch_directories", mode="before")
    @classmethod
    def parse_watch_directories(cls, v):
        """Parse comma-separated directories from environment variable and resolve to absolute paths."""
        if isinstance(v, str):
            directories = [d.strip() for d in v.split(",") if d.strip()]
            # Resolve each path to absolute form, expanding tilde (~) and resolving symlinks
            return [str(Path(d).expanduser().resolve()) for d in directories]
        elif isinstance(v, list):
            # Handle list input by resolving each path to absolute form
            return [str(Path(d.strip()).expanduser().resolve()) for d in v if d.strip()]
        return v

    @field_validator("file_extensions", mode="before")
    @classmethod
    def parse_file_extensions(cls, v):
        """Parse comma-separated file extensions from environment variable."""
        if isinstance(v, str):
            extensions = [ext.strip() for ext in v.split(",") if ext.strip()]
            # Ensure extensions start with a dot
            return {ext if ext.startswith('.') else f'.{ext}' for ext in extensions}
        return v

    @field_validator("ignore_patterns", mode="before")
    @classmethod
    def parse_ignore_patterns(cls, v):
        """Parse comma-separated ignore patterns from environment variable."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024


# Create global settings instance
settings = Settings()