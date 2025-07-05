import subprocess
import platform
from pathlib import Path

class ConversionError(Exception):
    """Custom exception for file conversion errors."""
    pass

def export_pages_to_docx(source_path: Path, output_dir: Path) -> Path:
    """
    Converts a .pages file to a .docx file using AppleScript on macOS.

    Args:
        source_path: The path to the source .pages file.
        output_dir: The directory where the converted .docx file will be saved.

    Returns:
        The path to the converted .docx file.

    Raises:
        ValueError: If the source file is not a .pages file.
        NotImplementedError: If the operating system is not macOS.
        ConversionError: If the AppleScript execution fails.
    """
    if platform.system() != "Darwin":
        raise NotImplementedError("This function is only supported on macOS.")

    if source_path.suffix.lower() != ".pages":
        raise ValueError("Source file must be a .pages file.")

    docx_path = output_dir / f"{source_path.stem}.docx"

    # Ensure the output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    script = f'''
    tell application "Pages"
        try
            set a_file to POSIX file "{source_path.resolve()}" as alias
            open a_file

            set docx_file_path to POSIX file "{docx_path.resolve()}"
            export front document to file docx_file_path as Microsoft Word

            close front document saving no

            return "success"
        on error e
            return "error: " & e
        end try
    end tell
    '''

    try:
        process = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        if "error:" in process.stdout.lower():
            raise ConversionError(f"AppleScript execution failed: {process.stdout}")
    except FileNotFoundError:
        raise NotImplementedError("The 'osascript' command is not available. Ensure you are on macOS.")
    except subprocess.CalledProcessError as e:
        error_message = e.stderr or e.stdout
        raise ConversionError(f"Failed to convert {source_path.name}: {error_message}")
    except subprocess.TimeoutExpired:
        raise ConversionError(f"Conversion timed out for {source_path.name}.")

    if not docx_path.exists():
        raise ConversionError(f"Converted file not found at {docx_path}")

    return docx_path