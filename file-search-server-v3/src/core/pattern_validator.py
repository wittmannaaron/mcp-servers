"""
Pattern Validator Module
Task #44: Utility Script Refactoring

Validates code patterns for architectural violations.
"""

import re
from pathlib import Path
from typing import List, Dict

from src.core.violations import Violation, ViolationType


class PatternValidator:
    """Validates code patterns for architectural violations"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.violations: List[Violation] = []

        # Directories to check
        self.CHECK_DIRS = ["src", "tests", "scripts"]

        # Patterns for violations
        self.FORBIDDEN_PATTERNS = {
            ViolationType.DIRECT_DATABASE: [
                r"^import sqlite3",
                r"^from sqlite3",
                r"sqlite3\.connect",
                r"\.execute\(",
                r"\.executemany\(",
                r"\.fetchall\(",
                r"\.fetchone\(",
                r"\.commit\(",
                r"\.rollback\(",
            ],
            ViolationType.DIRECT_LLM: [
                r"ollama\.generate",
                r"ollama\.chat",
                r"openai\.ChatCompletion",
                r"openai\.Completion",
                r"anthropic\.messages",
                r"requests\.post.*api\.openai",
                r"requests\.post.*api\.anthropic",
                r"httpx\.post.*api\.openai",
                r"httpx\.post.*api\.anthropic",
            ],
            ViolationType.NON_MCP_IMPORT: [
                r"^import requests(?!\s+#.*MCP)",
                r"^import httpx(?!\s+#.*MCP)",
                r"^from requests",
                r"^from httpx",
            ]
        }

        # Allowed MCP-related imports
        self.ALLOWED_MCP_PATTERNS = [
            r"from mcp",
            r"import mcp",
            r"from.*mcp_client",
            r"from.*mcp_.*_service",
        ]

    def validate(self) -> None:
        """Validate code patterns for architectural violations"""
        print("🔍 Checking code patterns for violations...")

        for check_dir in self.CHECK_DIRS:
            dir_path = self.project_root / check_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                self._check_file_patterns(py_file)

    def _check_file_patterns(self, file_path: Path) -> None:
        """Check a single file for pattern violations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️  Could not read {file_path}: {e}")
            return

        relative_path = str(file_path.relative_to(self.project_root))
        is_test_file = "/test" in relative_path or "test_" in file_path.name

        for line_num, line in enumerate(lines, 1):
            original_line = line
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#') or line.strip().startswith('#'):
                continue

            # Skip inline comments (everything after #)
            if '#' in line:
                line = line.split('#')[0].strip()
                if not line:
                    continue

            # Skip string literals and regex patterns in code
            if self._is_string_literal_or_regex(line):
                continue

            # Check for forbidden patterns
            for violation_type, patterns in self.FORBIDDEN_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, line):
                        # Check if it's an allowed MCP-related usage
                        if self._is_allowed_mcp_usage(line):
                            continue

                        # Skip test files for certain violations (they may contain test data)
                        if is_test_file and self._is_test_exception(violation_type, line):
                            continue

                        self.violations.append(Violation(
                            file_path=relative_path,
                            violation_type=violation_type,
                            line_number=line_num,
                            details=f"Found: {line.strip()}",
                            severity="ERROR"
                        ))

    def _is_allowed_mcp_usage(self, line: str) -> bool:
        """Check if the line contains allowed MCP-related usage"""
        for pattern in self.ALLOWED_MCP_PATTERNS:
            if re.search(pattern, line):
                return True
        return False

    def _is_string_literal_or_regex(self, line: str) -> bool:
        """Check if the line is a string literal or regex pattern"""
        # Skip lines that are clearly string literals or regex patterns
        if (line.strip().startswith(('r"', "r'", '"', "'")) or
            'r"' in line or "r'" in line or
            line.strip().startswith('"""') or
            line.strip().startswith("'''")):
            return True
        return False

    def _is_test_exception(self, violation_type: ViolationType, line: str) -> bool:
        """Check if this is an acceptable test file exception"""
        # Test files may contain test data that looks like violations
        if violation_type == ViolationType.DIRECT_DATABASE:
            # Allow test assertions and test data
            if any(keyword in line.lower() for keyword in ['assert', 'test', 'mock', 'patch', 'content =', 'Found:']):
                return True

        if violation_type == ViolationType.DIRECT_LLM:
            # Allow test mocks and test data
            if any(keyword in line.lower() for keyword in ['mock', 'patch', 'test', 'content =', 'Found:']):
                return True

        if violation_type == ViolationType.NON_MCP_IMPORT:
            # Allow test data and test content
            if any(keyword in line.lower() for keyword in ['content =', 'Found:', 'test']):
                return True

        return False