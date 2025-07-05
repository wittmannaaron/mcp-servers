"""
Violations Module
Task #44: Utility Script Refactoring

Common violation types and data structures for architectural validation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ViolationType(Enum):
    FILE_SIZE_SOFT = "file_size_soft"
    FILE_SIZE_HARD = "file_size_hard"
    DIRECT_DATABASE = "direct_database"
    DIRECT_LLM = "direct_llm"
    NON_MCP_IMPORT = "non_mcp_import"


@dataclass
class Violation:
    file_path: str
    violation_type: ViolationType
    line_number: Optional[int]
    details: str
    severity: str  # "ERROR", "WARNING"