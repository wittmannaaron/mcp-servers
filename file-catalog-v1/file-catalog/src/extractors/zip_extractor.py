import zipfile
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

from src.extractors.document_extractor import extract_and_preprocess


class ZipExtractor:
    """Extracts and processes ZIP files and their document contents."""
    
    def __init__(self):
        self.supported_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.ppt', '.pptx', '.xls', '.xlsx', '.md', '.html'}
    
    def extract_zip_file(self, zip_path: str) -> Dict[str, Any]:
        """
        Extract content from ZIP file and process all document files.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            Dictionary containing:
            - 'zip_data': Data for the ZIP file itself
            - 'contents': List of processed document files
        """
        try:
            logger.info(f"Processing ZIP file: {zip_path}")
            
            processed_docs = []
            file_list = []
            
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract ZIP contents and get file list
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_file:
                        # Get list of files in ZIP
                        zip_info_list = zip_file.infolist()
                        for info in zip_info_list:
                            if not info.is_dir():
                                # Skip macOS metadata files and directories
                                if (info.filename.startswith('._') or
                                    info.filename.endswith('.DS_Store') or
                                    info.filename.startswith('__MACOSX/') or
                                    '/__MACOSX/' in info.filename):
                                    continue
                                file_list.append(info.filename)
                        
                        zip_file.extractall(temp_path)
                        logger.debug(f"Extracted ZIP contents to: {temp_path}")
                except zipfile.BadZipFile:
                    logger.error(f"Invalid ZIP file: {zip_path}")
                    return {'zip_data': None, 'contents': []}
                
                # Process each extracted file recursively
                for extracted_file in temp_path.rglob('*'):
                    if extracted_file.is_file():
                        # Skip macOS metadata files
                        if extracted_file.name.startswith('._') or extracted_file.name == '.DS_Store':
                            logger.debug(f"Skipping metadata file: {extracted_file.name}")
                            continue
                        
                        file_ext = extracted_file.suffix.lower()
                        if file_ext in self.supported_extensions:
                            doc_data = self._process_document(extracted_file, zip_path)
                            if doc_data:
                                processed_docs.append(doc_data)
                        else:
                            logger.debug(f"Skipping unsupported file: {extracted_file.name} ({file_ext})")
            
            # Create ZIP file data
            zip_data = {
                'file_list': file_list,
                'total_files': len(file_list),
                'processed_files': len(processed_docs),
                'source_type': 'zip_file'
            }
            
            logger.info(f"Successfully processed ZIP file and {len(processed_docs)} documents from {zip_path}")
            return {
                'zip_data': zip_data,
                'contents': processed_docs
            }
            
        except Exception as e:
            logger.error(f"Failed to process ZIP file {zip_path}: {e}")
            return {'zip_data': None, 'contents': []}
    
    def _process_document(self, file_path: Path, original_zip_path: str) -> Dict[str, Any]:
        """Process individual document file from ZIP."""
        try:
            # Use existing document extractor
            processed_data = extract_and_preprocess(str(file_path))
            
            if "error" in processed_data:
                logger.error(f"Failed to extract content from {file_path.name}: {processed_data['error']}")
                return None
            
            # Calculate relative path within ZIP
            relative_path = file_path.name  # Simple approach - just filename
            # For nested directories, you could use: file_path.relative_to(temp_base_path)
            
            # Add ZIP-specific metadata
            processed_data['original_zip_path'] = original_zip_path
            processed_data['zip_internal_path'] = relative_path
            processed_data['source_type'] = 'zip_archive'
            processed_data['display_filename'] = f"{Path(original_zip_path).name}/{relative_path}"
            
            logger.debug(f"Processed document from ZIP: {relative_path}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Failed to process document {file_path.name}: {e}")
            return None


def extract_zip_data(zip_path: str) -> Dict[str, Any]:
    """
    Public interface for extracting ZIP file data and contents.
    
    Args:
        zip_path: Path to the ZIP file
        
    Returns:
        Dictionary containing:
        - 'zip_data': Data for the ZIP file itself
        - 'contents': List of processed document files
    """
    extractor = ZipExtractor()
    return extractor.extract_zip_file(zip_path)


def extract_zip_contents(zip_path: str) -> List[Dict[str, Any]]:
    """
    Legacy interface for extracting ZIP file contents only.
    Maintained for backward compatibility.
    
    Args:
        zip_path: Path to the ZIP file
        
    Returns:
        List of processed documents with metadata
    """
    extractor = ZipExtractor()
    result = extractor.extract_zip_file(zip_path)
    return result.get('contents', [])