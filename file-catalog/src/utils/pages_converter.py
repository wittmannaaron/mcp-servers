#!/usr/bin/env python3
"""
Pages to DOCX Converter for macOS
Converts Apple Pages documents to DOCX format using AppleScript automation.
"""

import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple, Optional
from loguru import logger


class PagesConverter:
    """Converts Apple Pages documents to DOCX format on macOS."""
    
    def __init__(self):
        """Initialize the Pages converter."""
        self.is_macos = platform.system() == "Darwin"
        if not self.is_macos:
            logger.warning("Pages converter only works on macOS")
    
    def is_available(self) -> bool:
        """Check if Pages conversion is available on this system."""
        if not self.is_macos:
            return False
        
        try:
            # Check if Pages app is installed
            result = subprocess.run(
                ["osascript", "-e", "tell application \"System Events\" to exists application process \"Pages\""],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check if Pages application exists
            result = subprocess.run(
                ["ls", "/Applications/Pages.app"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return result.returncode == 0
            
        except Exception as e:
            logger.debug(f"Pages availability check failed: {e}")
            return False
    
    def convert_to_docx(self, pages_file_path: Path) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Convert a Pages file to DOCX format.
        
        Args:
            pages_file_path: Path to the .pages file
            
        Returns:
            Tuple of (success, output_path, error_message)
        """
        if not self.is_macos:
            return False, None, "Pages conversion only available on macOS"
        
        if not pages_file_path.exists():
            return False, None, f"Pages file not found: {pages_file_path}"
        
        if not pages_file_path.suffix.lower() == '.pages':
            return False, None, f"Not a Pages file: {pages_file_path}"
        
        # Create temporary directory for output
        temp_dir = Path(tempfile.mkdtemp(prefix="pages_conversion_"))
        output_file = temp_dir / f"{pages_file_path.stem}.docx"
        
        try:
            # AppleScript to open Pages, export as DOCX, and close
            applescript = f'''
            tell application "Pages"
                -- Open the Pages document
                set sourceDoc to open POSIX file "{pages_file_path.absolute()}"
                
                -- Export as DOCX (using proper format constant)
                export sourceDoc to POSIX file "{output_file.absolute()}" as Microsoft Word
                
                -- Close the document without saving
                close sourceDoc saving no
            end tell
            '''
            
            logger.debug(f"Converting Pages file: {pages_file_path} -> {output_file}")
            
            # Execute AppleScript
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=60  # Allow up to 60 seconds for conversion
            )
            
            if result.returncode == 0 and output_file.exists():
                logger.debug(f"Successfully converted Pages file to: {output_file}")
                return True, output_file, None
            else:
                error_msg = f"AppleScript conversion failed: {result.stderr}"
                logger.error(error_msg)
                return False, None, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = "Pages conversion timed out"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Pages conversion failed: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        finally:
            # Clean up if conversion failed
            if output_file.exists():
                try:
                    # Don't delete successful conversions here - caller will handle cleanup
                    pass
                except Exception:
                    pass
    
    def cleanup_temp_file(self, temp_file_path: Optional[Path]) -> None:
        """Clean up temporary DOCX file and its directory."""
        if temp_file_path and temp_file_path.exists():
            try:
                # Remove the file
                temp_file_path.unlink()
                
                # Remove the temporary directory if it's empty
                temp_dir = temp_file_path.parent
                if temp_dir.exists() and not any(temp_dir.iterdir()):
                    temp_dir.rmdir()
                    
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {temp_file_path}: {e}")


# Global instance for use throughout the application
pages_converter = PagesConverter()