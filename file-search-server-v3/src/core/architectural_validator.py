"""
Architectural Validator Module
Task #44: Utility Script Refactoring

Validates architectural compliance across the codebase.
Extracted from scripts/validate_architecture.py for architectural compliance.
"""

from pathlib import Path
from typing import List
from dataclasses import dataclass
from enum import Enum

from src.core.file_size_validator import FileSizeValidator
from src.core.pattern_validator import PatternValidator


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
    line_number: int
    details: str
    severity: str  # "ERROR", "WARNING"


class ArchitecturalValidator:
    """Validates architectural compliance across the codebase"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.violations: List[Violation] = []

        # Initialize sub-validators
        self.file_size_validator = FileSizeValidator(project_root)
        self.pattern_validator = PatternValidator(project_root)

    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("🔍 Starting Architectural Compliance Validation...")
        print("=" * 80)

        # Check file sizes
        self.file_size_validator.validate()
        self.violations.extend(self.file_size_validator.violations)

        # Check for forbidden patterns
        self.pattern_validator.validate()
        self.violations.extend(self.pattern_validator.violations)

        # Generate report
        return self._generate_report()

    def _generate_report(self) -> bool:
        """Generate validation report"""
        print("\n" + "=" * 80)
        print("📊 ARCHITECTURAL COMPLIANCE REPORT")
        print("=" * 80)

        if not self.violations:
            print("✅ ALL CHECKS PASSED!")
            print("✅ No architectural violations found")
            print("✅ File size limits respected")
            print("✅ No direct database/LLM calls detected")
            print("✅ MCP protocol compliance verified")
            return True

        # Group violations by type
        violations_by_type = {}
        for violation in self.violations:
            if violation.violation_type not in violations_by_type:
                violations_by_type[violation.violation_type] = []
            violations_by_type[violation.violation_type].append(violation)

        # Report violations
        error_count = 0
        warning_count = 0

        for violation_type, violations in violations_by_type.items():
            print(f"\n❌ {violation_type.value.upper()} VIOLATIONS:")
            print("-" * 50)

            for violation in violations:
                if violation.severity == "ERROR":
                    error_count += 1
                    icon = "🚨"
                else:
                    warning_count += 1
                    icon = "⚠️"

                line_info = f" (line {violation.line_number})" if violation.line_number else ""
                print(f"{icon} {violation.file_path}{line_info}")
                print(f"   {violation.details}")

        # Summary
        print(f"\n📈 SUMMARY:")
        print(f"   🚨 Errors: {error_count}")
        print(f"   ⚠️  Warnings: {warning_count}")
        print(f"   📁 Total violations: {len(self.violations)}")

        if error_count > 0:
            print(f"\n❌ VALIDATION FAILED - {error_count} critical errors found")
            return False
        elif warning_count > 0:
            print(f"\n⚠️  VALIDATION PASSED WITH WARNINGS - {warning_count} warnings found")
            return True

        return True