"""
File Size Validator Module
Task #44: Utility Script Refactoring

Validates file size limits for architectural compliance.
"""

from pathlib import Path
from typing import List

from src.core.violations import Violation, ViolationType


class FileSizeValidator:
    """Validates file size limits"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.violations: List[Violation] = []

        # File size limits
        self.SOFT_LINE_LIMIT = 200
        self.HARD_LINE_LIMIT = 220

        # Directories to check
        self.CHECK_DIRS = ["src", "tests", "scripts"]

    def validate(self) -> None:
        """Validate file size limits"""
        print("📏 Checking file size compliance...")

        for check_dir in self.CHECK_DIRS:
            dir_path = self.project_root / check_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                line_count = self._count_lines(py_file)
                relative_path = str(py_file.relative_to(self.project_root))

                if line_count > self.HARD_LINE_LIMIT:
                    self.violations.append(Violation(
                        file_path=relative_path,
                        violation_type=ViolationType.FILE_SIZE_HARD,
                        line_number=None,
                        details=f"{line_count} lines (exceeds hard limit of {self.HARD_LINE_LIMIT})",
                        severity="ERROR"
                    ))
                elif line_count > self.SOFT_LINE_LIMIT:
                    self.violations.append(Violation(
                        file_path=relative_path,
                        violation_type=ViolationType.FILE_SIZE_SOFT,
                        line_number=None,
                        details=f"{line_count} lines (exceeds soft limit of {self.SOFT_LINE_LIMIT})",
                        severity="WARNING"
                    ))

    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except Exception:
            return 0