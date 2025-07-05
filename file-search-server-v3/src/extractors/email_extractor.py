import email
import email.policy
import tempfile
import os
import zipfile
from pathlib import Path
from typing import List, Tuple, Dict, Any
from loguru import logger

from src.extractors.docling_extractor import extract_and_preprocess


class EmailExtractor:
    """Extracts and processes .eml files and their attachments."""
    
    def __init__(self):
        self.supported_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.ppt', '.pptx', '.xls', '.xlsx', '.zip'}
    
    def extract_eml_file(self, eml_path: str) -> Dict[str, Any]:
        """
        Extract content from .eml file and process all document attachments.
        
        Args:
            eml_path: Path to the .eml file
            
        Returns:
            Dictionary containing:
            - 'eml_data': Data for the EML file itself
            - 'attachments': List of processed attachment documents
        """
        try:
            logger.info(f"Processing .eml file: {eml_path}")
            
            with open(eml_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=email.policy.default)
            
            # Extract email metadata
            email_metadata = self._extract_email_metadata(msg)
            
            # Extract email body text
            email_body = self._extract_email_body(msg)
            
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract attachments
                attachments = self._extract_attachments(msg, temp_path)
                
                # Process each attachment
                processed_attachments = []
                for attachment_info in attachments:
                    temp_file_path = attachment_info['temp_path']
                    original_filename = attachment_info['filename']
                    
                    # Check if it's a zip file
                    if temp_file_path.suffix.lower() == '.zip':
                        zip_docs = self._process_zip_file(temp_file_path, eml_path, email_metadata)
                        processed_attachments.extend(zip_docs)
                    else:
                        # Process regular document
                        doc_data = self._process_document(temp_file_path, eml_path, original_filename, email_metadata)
                        if doc_data:
                            processed_attachments.append(doc_data)
            
            # Create EML file data
            attachment_names = [att['filename'] for att in attachments]
            eml_data = {
                'email_metadata': email_metadata,
                'email_body': email_body,
                'attachment_list': attachment_names,
                'source_type': 'email_file'
            }
            
            logger.info(f"Successfully processed EML file and {len(processed_attachments)} attachments from {eml_path}")
            return {
                'eml_data': eml_data,
                'attachments': processed_attachments
            }
            
        except Exception as e:
            logger.error(f"Failed to process .eml file {eml_path}: {e}")
            return {'eml_data': None, 'attachments': []}
    
    def _extract_email_metadata(self, msg: email.message.EmailMessage) -> Dict[str, Any]:
        """Extract metadata from email message."""
        return {
            'from': msg.get('From', ''),
            'to': msg.get('To', ''),
            'subject': msg.get('Subject', ''),
            'date': msg.get('Date', ''),
            'message_id': msg.get('Message-ID', ''),
        }
    
    def _extract_email_body(self, msg: email.message.EmailMessage) -> str:
        """Extract the body text from email message."""
        body_text = ""
        
        try:
            # Try to get plain text body first
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = part.get_content_disposition()
                    
                    # Skip attachments
                    if content_disposition == 'attachment':
                        continue
                    
                    # Get text content
                    if content_type == 'text/plain':
                        body_text = part.get_content()
                        break
                    elif content_type == 'text/html' and not body_text:
                        # Use HTML as fallback if no plain text found
                        html_content = part.get_content()
                        # Simple HTML tag removal (basic)
                        import re
                        body_text = re.sub(r'<[^>]+>', '', html_content)
            else:
                # Single part message
                if msg.get_content_type() == 'text/plain':
                    body_text = msg.get_content()
                elif msg.get_content_type() == 'text/html':
                    html_content = msg.get_content()
                    import re
                    body_text = re.sub(r'<[^>]+>', '', html_content)
        
        except Exception as e:
            logger.warning(f"Failed to extract email body: {e}")
            body_text = ""
        
        return body_text.strip() if body_text else ""
    
    def _is_hidden_file(self, filename: str) -> bool:
        """Check if a filename represents a hidden or system file."""
        if not filename:
            return True
        
        # Hidden files (start with dot)
        if filename.startswith('.'):
            return True
        
        # macOS resource fork files
        if filename.startswith('._'):
            return True
        
        # Common system files
        system_files = {
            '.DS_Store', '._.DS_Store', 'Thumbs.db', 'desktop.ini',
            '.directory', '.localized', '__MACOSX'
        }
        
        if filename in system_files:
            return True
        
        # Check if filename contains __MACOSX path
        if '__MACOSX' in filename:
            return True
        
        return False

    def _extract_attachments(self, msg: email.message.EmailMessage, temp_dir: Path) -> List[Dict[str, Any]]:
        """Extract all attachments from email message to temporary directory."""
        attachments = []
        
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    # Skip hidden/system files
                    if self._is_hidden_file(filename):
                        logger.debug(f"Skipping hidden/system attachment: {filename}")
                        continue
                    
                    # Check if it's a supported document type
                    file_ext = Path(filename).suffix.lower()
                    if file_ext in self.supported_extensions:
                        try:
                            # Save attachment to temp directory
                            temp_file_path = temp_dir / filename
                            with open(temp_file_path, 'wb') as f:
                                f.write(part.get_payload(decode=True))
                            
                            attachments.append({
                                'filename': filename,
                                'temp_path': temp_file_path,
                                'content_type': part.get_content_type()
                            })
                            
                            logger.debug(f"Extracted attachment: {filename}")
                            
                        except Exception as e:
                            logger.error(f"Failed to extract attachment {filename}: {e}")
                    else:
                        logger.debug(f"Skipping unsupported attachment: {filename}")
        
        return attachments
    
    def _process_zip_file(self, zip_path: Path, original_eml_path: str, email_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process zip file and extract documents."""
        processed_docs = []
        
        try:
            with tempfile.TemporaryDirectory() as extract_dir:
                extract_path = Path(extract_dir)
                
                # Extract zip contents
                with zipfile.ZipFile(zip_path, 'r') as zip_file:
                    zip_file.extractall(extract_path)
                
                # Process each extracted file
                for extracted_file in extract_path.rglob('*'):
                    if extracted_file.is_file():
                        file_ext = extracted_file.suffix.lower()
                        if file_ext in self.supported_extensions:
                            doc_data = self._process_document(
                                extracted_file, 
                                original_eml_path, 
                                f"{zip_path.name}/{extracted_file.name}", 
                                email_metadata
                            )
                            if doc_data:
                                processed_docs.append(doc_data)
                        
        except Exception as e:
            logger.error(f"Failed to process zip file {zip_path}: {e}")
        
        return processed_docs
    
    def _process_document(self, file_path: Path, original_eml_path: str, display_filename: str, email_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual document file."""
        try:
            # Use existing document extractor
            processed_data = extract_and_preprocess(str(file_path))
            
            if "error" in processed_data:
                logger.error(f"Failed to extract content from {display_filename}: {processed_data['error']}")
                return None
            
            # Add email-specific metadata
            processed_data['email_metadata'] = email_metadata
            processed_data['original_eml_path'] = original_eml_path
            processed_data['attachment_filename'] = display_filename
            processed_data['source_type'] = 'email_attachment'
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Failed to process document {display_filename}: {e}")
            return None


def extract_email_data(eml_path: str) -> Dict[str, Any]:
    """
    Public interface for extracting email data and attachments.
    
    Args:
        eml_path: Path to the .eml file
        
    Returns:
        Dictionary containing:
        - 'eml_data': Data for the EML file itself
        - 'attachments': List of processed attachment documents
    """
    extractor = EmailExtractor()
    return extractor.extract_eml_file(eml_path)


def extract_email_attachments(eml_path: str) -> List[Dict[str, Any]]:
    """
    Legacy interface for extracting email attachments only.
    Maintained for backward compatibility.
    
    Args:
        eml_path: Path to the .eml file
        
    Returns:
        List of processed documents with metadata
    """
    extractor = EmailExtractor()
    result = extractor.extract_eml_file(eml_path)
    return result.get('attachments', [])