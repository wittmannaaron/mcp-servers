"""
Dependency Checker Module
Task #44: Utility Script Refactoring

Python dependency checks for EasyOCR environment verification.
"""

import sys
import logging
import subprocess
from typing import Dict, Any


class DependencyChecker:
    """Python dependency checker for EasyOCR."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        self.issues_found = []
        self.fixes_applied = []

    def check_python_dependencies(self) -> bool:
        """Check if all required Python packages are installed with correct versions."""
        self.logger.info("Checking Python dependencies...")

        # Core dependencies for EasyOCR
        required_packages = {
            'torch': {'min_version': '1.6.0', 'description': 'PyTorch deep learning framework'},
            'torchvision': {'min_version': '0.7.0', 'description': 'PyTorch computer vision library'},
            'opencv-python': {'min_version': '4.1.0', 'description': 'OpenCV computer vision library'},
            'numpy': {'min_version': '1.19.0', 'description': 'Numerical computing library'},
            'Pillow': {'min_version': '8.0.0', 'description': 'Python Imaging Library'},
            'scipy': {'min_version': '1.5.0', 'description': 'Scientific computing library'},
            'scikit-image': {'min_version': '0.17.0', 'description': 'Image processing library'},
        }

        # Optional but recommended packages
        optional_packages = {
            'psutil': {'description': 'System monitoring utilities'},
        }

        all_deps_ok = True

        for package, info in required_packages.items():
            try:
                module = __import__(package.replace('-', '_'))
                version = getattr(module, '__version__', 'unknown')
                self.logger.info(f"✓ {package} installed (version: {version})")

                # Version checking (simplified)
                if version != 'unknown' and 'min_version' in info:
                    # Basic version comparison (this could be more sophisticated)
                    try:
                        from packaging import version as pkg_version
                        if pkg_version.parse(version) < pkg_version.parse(info['min_version']):
                            self.issues_found.append(
                                f"{package} version {version} is below recommended minimum {info['min_version']}"
                            )
                            self.logger.warning(f"⚠ {package} version {version} < {info['min_version']}")
                    except ImportError:
                        # packaging not available, skip version check
                        pass

            except ImportError:
                self.issues_found.append(f"Missing required package: {package} - {info['description']}")
                self.logger.error(f"✗ {package} not installed")
                all_deps_ok = False

        # Check optional packages
        for package, info in optional_packages.items():
            try:
                __import__(package.replace('-', '_'))
                self.logger.info(f"✓ {package} installed (optional)")
            except ImportError:
                self.logger.info(f"○ {package} not installed (optional) - {info['description']}")

        return all_deps_ok

    def attempt_fixes(self) -> bool:
        """Attempt to install missing Python dependencies."""
        self.logger.info("Attempting to fix missing dependencies...")

        # Check if pip is available
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.logger.error("pip is not available - cannot install dependencies")
                return False
        except Exception as e:
            self.logger.error(f"Cannot check pip availability: {str(e)}")
            return False

        # List of packages to install if missing
        packages_to_install = []

        # Check which packages are missing
        required_packages = ['torch', 'torchvision', 'opencv-python', 'numpy', 'Pillow', 'scipy', 'scikit-image']
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                packages_to_install.append(package)

        if not packages_to_install:
            self.logger.info("✓ All required packages are already installed")
            return True

        # Install missing packages
        for package in packages_to_install:
            try:
                self.logger.info(f"Installing {package}...")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", package
                ], capture_output=True, text=True, timeout=300)

                if result.returncode == 0:
                    self.logger.info(f"✓ Successfully installed {package}")
                    self.fixes_applied.append(f"Installed {package}")
                else:
                    self.logger.error(f"✗ Failed to install {package}: {result.stderr}")
                    return False

            except subprocess.TimeoutExpired:
                self.logger.error(f"✗ Installation of {package} timed out")
                return False
            except Exception as e:
                self.logger.error(f"✗ Error installing {package}: {str(e)}")
                return False

        return True