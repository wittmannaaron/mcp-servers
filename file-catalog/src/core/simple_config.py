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
        self.app_name = "FileCatalog"
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"
        self.log_file_path = Path(os.getenv("LOG_FILE_PATH", "logs/filecatalog.log"))
        self.log_file_rotation = os.getenv("LOG_FILE_ROTATION", "10 MB")
        self.log_file_retention = os.getenv("LOG_FILE_RETENTION", "10 days")

        # File extensions (extended for new supported formats)
        self.file_extensions = {
            # Text & Markup
            '.txt', '.md', '.markdown', '.html', '.htm', '.rtf', '.epub', '.csv',
            # Office Documents - Text & Presentations
            '.doc', '.docx', '.odt', '.pages',
            '.ppt', '.pptx', '.odp',
            # Spreadsheets  
            '.xls', '.xlsx', '.ods',
            # PDFs (primary docling target)
            '.pdf',
            # Email files
            '.eml',
            # Images (for metadata extraction)
            '.jpeg', '.jpg', '.png', '.bmp',
            # Archives
            '.zip', '.tar', '.tar.gz', '.tgz',
            # Code files (for documentation extraction)
            '.py', '.js', '.ts', '.java', '.go', '.sh',
            # Other formats
            '.xml', '.json', '.tex'
        }

        self.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
        self.ignore_patterns = [
            '.*', '__pycache__', '*.tmp', '*.temp', '*.cache',
            '*.log', 'node_modules', '.git', '.svn', '.hg'
        ]

        # Database settings
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./data/filecatalog.db")
        self.mcp_db_path = "data/filecatalog.db"

        # LLM Configuration (Ollama)
        self.llm_request_timeout = float(os.getenv("LLM_REQUEST_TIMEOUT", "60.0"))
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4000"))

        # Ollama settings
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        self.ollama_base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Processing tools preferences
        self.prefer_markitdown = os.getenv("PREFER_MARKITDOWN", "true").lower() == "true"
        self.prefer_pandoc = os.getenv("PREFER_PANDOC", "true").lower() == "true"
        self.use_docling_for_pdf_only = os.getenv("USE_DOCLING_PDF_ONLY", "true").lower() == "true"

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

# Create global settings instance
settings = SimpleConfig()