from loguru import logger
import hashlib
import uuid
import platform
import tempfile
import os
import shutil
from pathlib import Path
from typing import Tuple, Dict, Any

from src.utils.applescript_converter import export_pages_to_docx, ConversionError

# Third-party libraries
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import ConversionStatus

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

def extract_text(file_path: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extracts text and metadata from a given file using Docling, with fallbacks for text files and OCR.
    Handles .pages files on macOS by converting them to .docx first.

    Args:
        file_path: The path to the file to process.

    Returns:
        A tuple containing the extracted text and a dictionary of metadata.
        Returns an error message and empty dict if all methods fail.
    """
    source_path = Path(file_path)
    processing_path = file_path
    temp_dir = None

    try:
        # Check if file exists first
        if not source_path.exists():
            logger.error(f"File does not exist: '{file_path}'")
            return f"Extraction failed: File not found ({file_path})", {}

        # Handle simple text files directly (no need for Docling)
        if source_path.suffix.lower() in {'.txt', '.md', '.csv', '.json', '.xml', '.html', '.rtf', '.log', '.py'}:
            logger.debug(f"Processing text file '{source_path.name}' directly (no Docling needed).")
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                logger.success(f"Successfully read text file '{source_path.name}'")
                metadata = {
                    "source": source_path.name,
                    "format": source_path.suffix.lower(),
                    "extraction_method": "direct_text_read",
                    "file_size": source_path.stat().st_size
                }
                return text_content, metadata
            except UnicodeDecodeError:
                # Try with different encoding
                try:
                    with open(source_path, 'r', encoding='latin-1') as f:
                        text_content = f.read()
                    logger.success(f"Successfully read text file '{source_path.name}' with latin-1 encoding")
                    metadata = {
                        "source": source_path.name,
                        "format": source_path.suffix.lower(),
                        "extraction_method": "direct_text_read_latin1",
                        "file_size": source_path.stat().st_size
                    }
                    return text_content, metadata
                except Exception as e:
                    logger.error(f"Failed to read text file '{source_path.name}': {e}")
                    return f"Extraction failed: Could not read text file ({e})", {}
            except Exception as e:
                logger.error(f"Failed to read text file '{source_path.name}': {e}")
                return f"Extraction failed: Could not read text file ({e})", {}

        # Handle .pages conversion on macOS
        if source_path.suffix.lower() == ".pages" and platform.system() == "Darwin":
            temp_dir = tempfile.mkdtemp()
            logger.info(f"'{source_path.name}' is a Pages document. Converting to .docx.")
            try:
                docx_path = export_pages_to_docx(source_path, Path(temp_dir))
                logger.success(f"Successfully converted '{source_path.name}' to '{docx_path.name}'")
                processing_path = str(docx_path)
            except ConversionError as e:
                logger.error(f"Failed to convert .pages file '{source_path.name}': {e}")
                return f"Extraction failed: Pages conversion error ({e})", {}

        # Use the DocumentConverter API for document files
        logger.debug(f"Attempting to extract text from '{processing_path}' using Docling.")
        try:
            converter = DocumentConverter()
            results = converter.convert_all([processing_path])
            result = next(results, None)

            if result and result.status == ConversionStatus.SUCCESS:
                logger.success(f"Docling successfully extracted text from '{processing_path}'")
                metadata = {
                    "source": result.input.file.name,
                    "hash": result.input.document_hash,
                    "format": result.input.format.value,
                    "extraction_method": "docling"
                }
                with tempfile.NamedTemporaryFile(mode='w+', suffix=".md", delete=True, encoding='utf-8') as temp_f:
                    result.document.save_as_markdown(filename=Path(temp_f.name), strict_text=True)
                    temp_f.seek(0)
                    text_content = temp_f.read()
                    return text_content, metadata

            if result and result.status == ConversionStatus.FAILURE:
                corrupt_msg = f"Docling conversion failed for '{processing_path}'"
                if hasattr(result, 'errors') and result.errors:
                    corrupt_msg += f": {', '.join(result.errors)}"
                logger.error(corrupt_msg)
                return corrupt_msg, {}

            logger.warning(f"Docling failed for '{processing_path}'. Attempting OCR fallback.")
            if result:
                logger.debug(f"Docling error details: {result.errors}")
        except Exception as docling_error:
            logger.error(f"Docling processing failed for '{processing_path}': {docling_error}")

        # Fallback to OCR for image files
        if pytesseract and Image and source_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'}:
            try:
                logger.info(f"Falling back to OCR for image file '{file_path}'.")
                img = Image.open(file_path)
                ocr_text = pytesseract.image_to_string(img)
                logger.success(f"OCR fallback successful for '{file_path}'.")
                return ocr_text, {"extraction_method": "ocr_fallback", "source": source_path.name}
            except Exception as ocr_error:
                logger.error(f"OCR fallback also failed for '{file_path}': {ocr_error}")
                return f"Extraction failed: OCR fallback also failed ({ocr_error})", {}
        else:
            if not pytesseract or not Image:
                logger.error("OCR libraries (pytesseract, Pillow) not installed. Cannot fallback to OCR.")
            return f"Extraction failed: Unsupported file format or Docling processing failed for '{source_path.name}'", {}

    except Exception as e:
        logger.opt(exception=True).error(f"An unexpected error occurred during extraction for '{file_path}'")
        return f"Extraction failed with unexpected error: {e}", {}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")

def preprocess_data(text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocesses the extracted text and metadata.

    Args:
        text: The extracted text content.
        metadata: The extracted metadata.

    Returns:
        A dictionary containing the preprocessed data.
    """
    # Generate a unique ID for the document
    doc_uuid = str(uuid.uuid4())

    # Calculate MD5 checksum
    md5_hash = hashlib.md5(text.encode()).hexdigest()

    # Convert to Markdown format
    markdown_content = f"# Document Content\n\n{text}"

    return {
        "uuid": doc_uuid,
        "md5_hash": md5_hash,
        "checksum": md5_hash,  # Keep for backward compatibility
        "original_text": text,
        "markdown_content": markdown_content,
        "original_metadata": metadata,
    }

def extract_and_preprocess(file_path: str) -> Dict[str, Any]:
    """
    Extracts and preprocesses data from a file.

    Args:
        file_path: The path to the file.

    Returns:
        A dictionary with the processed data, or an error dictionary.
    """
    text, metadata = extract_text(file_path)
    if "Extraction failed" in text:
        return {"error": text, "metadata": metadata}

    return preprocess_data(text, metadata)