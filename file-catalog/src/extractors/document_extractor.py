"""
Enhanced Document Extractor for file-catalog.
Supports multiple processing tools based on file type and preferences.

Tool Priority (based on specifications):
- PDF: docling (existing, optimized for PDFs)  
- Office & Others: markitdown (primary), pandoc (fallback)
- Images: exiftool/piexif for metadata
- Code: Direct text reading with syntax preservation
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
import mimetypes
import json

from src.core.simple_config import settings


class DocumentExtractor:
    """Enhanced document extractor with multiple tool support."""
    
    def __init__(self):
        self.supported_tools = self._check_available_tools()
        logger.info(f"Available extraction tools: {list(self.supported_tools.keys())}")
    
    def _check_available_tools(self) -> Dict[str, bool]:
        """Check which extraction tools are available on the system."""
        tools = {}
        
        # Check for markitdown
        try:
            import markitdown
            tools['markitdown'] = True
        except ImportError:
            tools['markitdown'] = False
            logger.warning("markitdown not available - install with: pip install markitdown")
        
        # Check for pandoc
        try:
            result = subprocess.run(['pandoc', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            tools['pandoc'] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tools['pandoc'] = False
            logger.warning("pandoc not available - install from: https://pandoc.org/installing.html")
        
        # Check for docling
        try:
            import docling
            tools['docling'] = True
        except ImportError:
            tools['docling'] = False
            logger.warning("docling not available - install with: pip install docling")
        
        # Check for exiftool  
        try:
            result = subprocess.run(['exiftool', '-ver'], 
                                  capture_output=True, text=True, timeout=5)
            tools['exiftool'] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tools['exiftool'] = False
            logger.debug("exiftool not available - install for image metadata extraction")
        
        return tools
    
    def extract_document(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text and metadata from document using appropriate tool.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dict containing extracted text, metadata, and processing info
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {"error": f"File not found: {file_path}"}
        
        if not file_path_obj.is_file():
            return {"error": f"Path is not a file: {file_path}"}
        
        # Get file metadata
        file_stats = file_path_obj.stat()
        mime_type, _ = mimetypes.guess_type(file_path)
        extension = file_path_obj.suffix.lower()
        
        # Determine extraction strategy based on file type
        extraction_result = self._determine_extraction_strategy(file_path_obj, extension, mime_type)
        
        # Add file metadata to result
        extraction_result.update({
            'file_path': file_path,
            'filename': file_path_obj.name,
            'extension': extension,
            'file_size': file_stats.st_size,
            'mime_type': mime_type or 'application/octet-stream'
        })
        
        return extraction_result
    
    def _determine_extraction_strategy(self, file_path: Path, extension: str, mime_type: str) -> Dict[str, Any]:
        """Determine and execute the best extraction strategy for the file type."""
        
        # PDF files - use docling (optimized for PDFs)
        if extension == '.pdf':
            if self.supported_tools.get('docling'):
                return self._extract_with_docling(file_path)
            elif self.supported_tools.get('markitdown'):
                return self._extract_with_markitdown(file_path)
            elif self.supported_tools.get('pandoc'):
                return self._extract_with_pandoc(file_path)
            else:
                return {"error": "No PDF extraction tools available"}
        
        # Office documents - prioritize markitdown, fallback to pandoc
        office_extensions = {'.docx', '.pptx', '.xlsx', '.odt', '.ods', '.odp', '.pages'}
        if extension in office_extensions:
            if settings.prefer_markitdown and self.supported_tools.get('markitdown'):
                result = self._extract_with_markitdown(file_path)
                if 'error' not in result:
                    return result
            
            if settings.prefer_pandoc and self.supported_tools.get('pandoc'):
                return self._extract_with_pandoc(file_path)
            
            return {"error": f"No suitable extraction tool for {extension}"}
        
        # HTML/RTF/EPUB - use pandoc or markitdown
        markup_extensions = {'.html', '.htm', '.rtf', '.epub'}
        if extension in markup_extensions:
            if self.supported_tools.get('pandoc'):
                return self._extract_with_pandoc(file_path)
            elif self.supported_tools.get('markitdown'):
                return self._extract_with_markitdown(file_path)
            else:
                return {"error": f"No markup extraction tool for {extension}"}
        
        # Images - extract metadata only
        image_extensions = {'.jpeg', '.jpg', '.png', '.bmp', '.gif', '.tiff'}
        if extension in image_extensions:
            return self._extract_image_metadata(file_path)
        
        # Code files - direct text reading
        code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.sh', '.cpp', '.c', '.h', '.css'}
        if extension in code_extensions:
            return self._extract_code_file(file_path)
        
        # Text files - direct reading
        text_extensions = {'.txt', '.md', '.markdown', '.csv', '.json', '.xml'}
        if extension in text_extensions:
            return self._extract_text_file(file_path)
        
        # Email files - special handling needed (will be handled by email_extractor)
        if extension == '.eml':
            return {"error": "EML files should be processed by email_extractor"}
        
        # Archive files - special handling needed (will be handled by archive_extractor)
        archive_extensions = {'.zip', '.tar', '.tar.gz', '.tgz'}
        if extension in archive_extensions:
            return {"error": "Archive files should be processed by archive_extractor"}
        
        # Fallback: try markitdown for unknown types
        if self.supported_tools.get('markitdown'):
            logger.debug(f"Trying markitdown for unknown file type: {extension}")
            return self._extract_with_markitdown(file_path)
        
        return {"error": f"Unsupported file type: {extension}"}
    
    def _extract_with_docling(self, file_path: Path) -> Dict[str, Any]:
        """Extract using docling (optimized for PDFs)."""
        try:
            from docling.document_converter import DocumentConverter
            
            logger.debug(f"Extracting with docling: {file_path}")
            converter = DocumentConverter()
            
            # Convert document
            result = converter.convert(str(file_path))
            
            # Extract markdown content
            markdown_content = result.document.export_to_markdown()
            
            return {
                'original_text': markdown_content,
                'markdown_content': markdown_content,
                'extraction_tool': 'docling',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Docling extraction failed for {file_path}: {e}")
            return {"error": f"Docling extraction failed: {str(e)}"}
    
    def _extract_with_markitdown(self, file_path: Path) -> Dict[str, Any]:
        """Extract using markitdown."""
        try:
            from markitdown import MarkItDown
            
            logger.debug(f"Extracting with markitdown: {file_path}")
            md = MarkItDown()
            
            # Convert to markdown
            result = md.convert(str(file_path))
            
            if result and hasattr(result, 'text_content'):
                markdown_content = result.text_content
                
                return {
                    'original_text': markdown_content,
                    'markdown_content': markdown_content,
                    'extraction_tool': 'markitdown',
                    'success': True
                }
            else:
                return {"error": "Markitdown returned empty result"}
                
        except Exception as e:
            logger.error(f"Markitdown extraction failed for {file_path}: {e}")
            return {"error": f"Markitdown extraction failed: {str(e)}"}
    
    def _extract_with_pandoc(self, file_path: Path) -> Dict[str, Any]:
        """Extract using pandoc."""
        try:
            logger.debug(f"Extracting with pandoc: {file_path}")
            
            # Use pandoc to convert to markdown
            cmd = [
                'pandoc',
                str(file_path),
                '--to=markdown',
                '--wrap=none',
                '--extract-media=.',
                '--standalone'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                markdown_content = result.stdout
                
                return {
                    'original_text': markdown_content,
                    'markdown_content': markdown_content,
                    'extraction_tool': 'pandoc',
                    'success': True
                }
            else:
                return {"error": f"Pandoc failed: {result.stderr}"}
                
        except subprocess.TimeoutExpired:
            return {"error": "Pandoc extraction timed out"}
        except Exception as e:
            logger.error(f"Pandoc extraction failed for {file_path}: {e}")
            return {"error": f"Pandoc extraction failed: {str(e)}"}
    
    def _extract_image_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from images using exiftool."""
        try:
            if not self.supported_tools.get('exiftool'):
                return {
                    'original_text': f"Image file: {file_path.name}",
                    'markdown_content': f"# Image: {file_path.name}\n\nImage metadata extraction not available.",
                    'extraction_tool': 'basic',
                    'success': True
                }
            
            logger.debug(f"Extracting image metadata with exiftool: {file_path}")
            
            cmd = ['exiftool', '-json', str(file_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                metadata = json.loads(result.stdout)[0]
                
                # Create markdown representation of metadata
                markdown_content = f"# Image: {file_path.name}\n\n"
                
                # Extract key metadata
                for key, value in metadata.items():
                    if key not in ['SourceFile', 'Directory', 'FileName']:
                        markdown_content += f"**{key}**: {value}\n\n"
                
                return {
                    'original_text': markdown_content,
                    'markdown_content': markdown_content,
                    'metadata': metadata,
                    'extraction_tool': 'exiftool',
                    'success': True
                }
            else:
                return {"error": f"Exiftool failed: {result.stderr}"}
                
        except Exception as e:
            logger.error(f"Image metadata extraction failed for {file_path}: {e}")
            return {"error": f"Image metadata extraction failed: {str(e)}"}
    
    def _extract_code_file(self, file_path: Path) -> Dict[str, Any]:
        """Extract code files with syntax preservation."""
        try:
            logger.debug(f"Extracting code file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Determine language for syntax highlighting
            language_map = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.java': 'java', '.go': 'go', '.sh': 'bash',
                '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.css': 'css'
            }
            
            language = language_map.get(file_path.suffix.lower(), 'text')
            
            # Create markdown with code block
            markdown_content = f"# Code: {file_path.name}\n\n```{language}\n{content}\n```"
            
            return {
                'original_text': content,
                'markdown_content': markdown_content,
                'language': language,
                'extraction_tool': 'direct_read',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Code file extraction failed for {file_path}: {e}")
            return {"error": f"Code file extraction failed: {str(e)}"}
    
    def _extract_text_file(self, file_path: Path) -> Dict[str, Any]:
        """Extract plain text files."""
        try:
            logger.debug(f"Extracting text file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # For markdown files, keep as-is; for others, add basic structure
            if file_path.suffix.lower() in ['.md', '.markdown']:
                markdown_content = content
            else:
                markdown_content = f"# {file_path.name}\n\n{content}"
            
            return {
                'original_text': content,
                'markdown_content': markdown_content,
                'extraction_tool': 'direct_read',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Text file extraction failed for {file_path}: {e}")
            return {"error": f"Text file extraction failed: {str(e)}"}


# Main extraction function for compatibility with existing code
def extract_and_preprocess(file_path: str) -> Dict[str, Any]:
    """
    Main extraction function that maintains compatibility with existing ingestion code.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Dict containing extracted text and metadata
    """
    extractor = DocumentExtractor()
    return extractor.extract_document(file_path)


if __name__ == "__main__":
    # Test the extractor with various file types
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python document_extractor.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    result = extract_and_preprocess(file_path)
    
    print(f"Extraction result for {file_path}:")
    print(json.dumps(result, indent=2, ensure_ascii=False))