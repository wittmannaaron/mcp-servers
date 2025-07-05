"""
System Checker Module
Task #44: Utility Script Refactoring

System-level checks for EasyOCR environment verification.
"""

import sys
import logging
import platform
import subprocess
from typing import Dict, Any


class SystemChecker:
    """System-level environment checker for EasyOCR."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        self.system_info = self._collect_system_info()
        self.issues_found = []

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect comprehensive system information for troubleshooting."""
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
        except ImportError:
            memory_info = None
            disk_info = None

        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "memory_total_gb": round(memory_info.total / (1024**3), 2) if memory_info else "Unknown",
            "memory_available_gb": round(memory_info.available / (1024**3), 2) if memory_info else "Unknown",
            "disk_free_gb": round(disk_info.free / (1024**3), 2) if disk_info else "Unknown",
            "python_executable": sys.executable,
            "virtual_env": self._check_virtual_environment()
        }

    def _check_virtual_environment(self) -> Dict[str, Any]:
        """Check virtual environment status and details."""
        venv_info = {
            "active": False,
            "path": None,
            "type": None
        }

        # Check if virtual environment is active
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            venv_info["active"] = True
            venv_info["path"] = sys.prefix

            # Determine virtual environment type
            if "venv" in sys.prefix or "virtualenv" in sys.prefix:
                venv_info["type"] = "venv/virtualenv"
            elif "conda" in sys.prefix or "miniconda" in sys.prefix:
                venv_info["type"] = "conda"
            else:
                venv_info["type"] = "unknown"

        return venv_info

    def check_python_requirements(self) -> bool:
        """Check if Python version and basic requirements are met."""
        self.logger.info("Checking Python requirements...")

        # Check Python version (EasyOCR requires Python 3.6+, recommend 3.8+)
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.issues_found.append(
                f"Python version {version.major}.{version.minor} is too old. "
                "EasyOCR requires Python 3.8+ for optimal performance."
            )
            self.logger.error(f"✗ Python version: {version.major}.{version.minor}.{version.micro} (requires 3.8+)")
            return False

        self.logger.info(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")

        # Check virtual environment
        if not self.system_info["virtual_env"]["active"]:
            self.issues_found.append(
                "Virtual environment is not active. This may cause dependency conflicts."
            )
            self.logger.warning("⚠ Virtual environment not active")
        else:
            self.logger.info(f"✓ Virtual environment active: {self.system_info['virtual_env']['type']}")

        return True

    def check_system_dependencies(self) -> bool:
        """Check system-level dependencies required by EasyOCR."""
        self.logger.info("Checking system dependencies...")

        system_deps_ok = True

        # Check for system libraries based on OS
        if self.system_info["os"] == "Linux":
            system_deps_ok = self._check_linux_dependencies()
        elif self.system_info["os"] == "Darwin":  # macOS
            self._check_macos_dependencies()

        # Check system resources
        system_deps_ok = self._check_system_resources() and system_deps_ok

        return system_deps_ok

    def _check_linux_dependencies(self) -> bool:
        """Check Linux-specific dependencies."""
        required_libs = ["libgl1-mesa-glx", "libglib2.0-0", "libsm6", "libxext6", "libxrender-dev"]
        missing_libs = []

        for lib in required_libs:
            try:
                result = subprocess.run(
                    ["dpkg", "-l", lib],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    missing_libs.append(lib)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # If dpkg is not available, skip this check
                self.logger.debug("dpkg not available, skipping Linux library check")
                break

        if missing_libs:
            self.issues_found.append(
                f"Missing system libraries: {', '.join(missing_libs)}. "
                f"Install with: sudo apt-get install {' '.join(missing_libs)}"
            )
            return False

        return True

    def _check_macos_dependencies(self) -> None:
        """Check macOS-specific dependencies."""
        try:
            subprocess.run(["brew", "--version"], capture_output=True, check=True, timeout=5)
            self.logger.info("✓ Homebrew available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.warning("⚠ Homebrew not found (recommended for macOS dependencies)")

    def _check_system_resources(self) -> bool:
        """Check system resources (memory and disk space)."""
        resources_ok = True

        # Check available memory (EasyOCR models can be memory intensive)
        if self.system_info["memory_available_gb"] != "Unknown":
            if self.system_info["memory_available_gb"] < 2.0:
                self.issues_found.append(
                    f"Low available memory: {self.system_info['memory_available_gb']}GB. "
                    "EasyOCR may fail with insufficient memory."
                )
                resources_ok = False
                self.logger.warning(f"⚠ Low memory: {self.system_info['memory_available_gb']}GB available")
            else:
                self.logger.info(f"✓ Sufficient memory: {self.system_info['memory_available_gb']}GB available")

        # Check disk space (models can be large)
        if self.system_info["disk_free_gb"] != "Unknown":
            if self.system_info["disk_free_gb"] < 5.0:
                self.issues_found.append(
                    f"Low disk space: {self.system_info['disk_free_gb']}GB free. "
                    "EasyOCR models require several GB of storage."
                )
                resources_ok = False
                self.logger.warning(f"⚠ Low disk space: {self.system_info['disk_free_gb']}GB free")
            else:
                self.logger.info(f"✓ Sufficient disk space: {self.system_info['disk_free_gb']}GB free")

        return resources_ok