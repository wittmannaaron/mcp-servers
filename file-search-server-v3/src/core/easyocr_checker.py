"""
EasyOCR Environment Checker Module
Task #44: Utility Script Refactoring

Comprehensive EasyOCR environment verification and fixing utility.
Extracted from scripts/verify_easyocr.py for architectural compliance.
"""

import os
import sys
import logging
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.core.system_checker import SystemChecker
from src.core.dependency_checker import DependencyChecker


class EasyOCREnvironmentChecker:
    """Comprehensive EasyOCR environment verification and fixing utility."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        self.system_checker = SystemChecker(verbose)
        self.dependency_checker = DependencyChecker(verbose)
        self.issues_found = []
        self.fixes_applied = []

    @property
    def system_info(self) -> Dict[str, Any]:
        """Get system information from system checker."""
        return self.system_checker.system_info

    def check_python_requirements(self) -> bool:
        """Check if Python version and basic requirements are met."""
        return self.system_checker.check_python_requirements()

    def check_system_dependencies(self) -> bool:
        """Check system-level dependencies required by EasyOCR."""
        return self.system_checker.check_system_dependencies()

    def check_python_dependencies(self) -> bool:
        """Check if all required Python packages are installed with correct versions."""
        return self.dependency_checker.check_python_dependencies()

    def run_comprehensive_check(self) -> bool:
        """Run all environment checks and return overall status."""
        self.logger.info("Starting comprehensive EasyOCR environment verification...")
        self.logger.info("=" * 60)

        # Log system information
        self.logger.info("System Information:")
        for key, value in self.system_info.items():
            if isinstance(value, dict):
                self.logger.info(f"  {key}:")
                for sub_key, sub_value in value.items():
                    self.logger.info(f"    {sub_key}: {sub_value}")
            else:
                self.logger.info(f"  {key}: {value}")

        self.logger.info("-" * 60)

        # Run all checks
        checks = [
            ("Python Requirements", self.check_python_requirements),
            ("System Dependencies", self.check_system_dependencies),
            ("Python Dependencies", self.check_python_dependencies),
        ]

        all_passed = True

        for check_name, check_func in checks:
            self.logger.info(f"\nRunning check: {check_name}")
            self.logger.info("-" * 30)
            try:
                if not check_func():
                    all_passed = False
                    # Collect issues from sub-checkers
                    if hasattr(self.system_checker, 'issues_found'):
                        self.issues_found.extend(self.system_checker.issues_found)
                    if hasattr(self.dependency_checker, 'issues_found'):
                        self.issues_found.extend(self.dependency_checker.issues_found)
            except Exception as e:
                self.logger.error(f"Check '{check_name}' failed with exception: {str(e)}")
                self.issues_found.append(f"Check '{check_name}' failed: {str(e)}")
                all_passed = False

        # Summary
        self.logger.info("\n" + "=" * 60)
        self.logger.info("VERIFICATION SUMMARY")
        self.logger.info("=" * 60)

        if all_passed and not self.issues_found:
            self.logger.info("✅ All checks passed! EasyOCR environment is ready.")
        else:
            self.logger.warning(f"❌ Found {len(self.issues_found)} issue(s):")
            for i, issue in enumerate(self.issues_found, 1):
                self.logger.warning(f"  {i}. {issue}")

        return all_passed and not self.issues_found

    def attempt_automatic_fixes(self, force_redownload: bool = False) -> bool:
        """Attempt to automatically fix detected issues."""
        self.logger.info("Starting automatic fix attempts...")
        self.logger.info("=" * 50)

        fixes_successful = True

        # Delegate fixes to appropriate checkers
        if hasattr(self.dependency_checker, 'attempt_fixes'):
            if not self.dependency_checker.attempt_fixes():
                fixes_successful = False
            self.fixes_applied.extend(getattr(self.dependency_checker, 'fixes_applied', []))

        # Summary of fixes
        self.logger.info("\n" + "=" * 50)
        self.logger.info("FIX ATTEMPT SUMMARY")
        self.logger.info("=" * 50)

        if self.fixes_applied:
            self.logger.info(f"✅ Applied {len(self.fixes_applied)} fix(es):")
            for i, fix in enumerate(self.fixes_applied, 1):
                self.logger.info(f"  {i}. {fix}")
        else:
            self.logger.info("○ No fixes were applied")

        return fixes_successful