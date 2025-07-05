import hashlib
import mimetypes
from pathlib import Path
from loguru import logger
from datetime import datetime

from src.core.events import FileEvent, FileEventType
from src.database.database import DocumentStore
from src.extractors.docling_extractor import extract_and_preprocess
from src.extractors.email_extractor import extract_email_data
from src.extractors.zip_extractor import extract_zip_data
from src.core.ingestion_mcp_client import IngestionMCPClient

class IngestionOrchestrator:
    """Orchestrates the file ingestion process using MCP architecture."""

    def __init__(self, document_store: DocumentStore):
        self.document_store = document_store
        self.mcp_client = IngestionMCPClient()
        self._mcp_connected = False

    async def process_file_event(self, event: FileEvent):
        """Processes a single file event from the queue using MCP architecture."""
        logger.info(f"Processing event: {event.event_type.value} for {event.file_path}")

        try:
            # Ensure MCP client is connected
            if not self._mcp_connected:
                self._mcp_connected = await self.mcp_client.connect()
                if not self._mcp_connected:
                    logger.error("Failed to connect to MCP client, skipping event")
                    return None

            if event.event_type in (FileEventType.CREATED, FileEventType.MODIFIED):
                return await self._handle_upsert(event.file_path)
            elif event.event_type == FileEventType.DELETED:
                self._handle_delete(event.file_path)
                return None
            elif event.event_type == FileEventType.MOVED:
                self._handle_move(event.old_path, event.file_path)
                return None
        except Exception as e:
            logger.opt(exception=True).error(
                f"Unhandled exception while processing event for {event.file_path}"
            )
            return None

    def _is_hidden_file(self, file_path: Path) -> bool:
        """Check if a file or any part of its path is hidden."""
        # Check if filename starts with dot (hidden file)
        if file_path.name.startswith('.'):
            return True
        
        # Check if any parent directory in the path is hidden
        for part in file_path.parts:
            if part.startswith('.') and part not in ['.', '..']:
                return True
        
        # Check for common system/metadata files
        system_files = {
            '.DS_Store', '._.DS_Store', 'Thumbs.db', 'desktop.ini',
            '.directory', '.localized', '.fseventsd', '.Spotlight-V100',
            '.Trashes', '.TemporaryItems', '.DocumentRevisions-V100',
            '.fuse_hidden', '.nfs', '.gvfs'
        }
        
        if file_path.name in system_files:
            return True
        
        # Check for macOS resource fork files
        if file_path.name.startswith('._'):
            return True
        
        # Check for __MACOSX directories (case insensitive)
        if '__MACOSX' in [part.upper() for part in file_path.parts]:
            return True
        
        return False

    async def _handle_upsert(self, file_path: Path):
        """Handles creation and modification of a file using MCP architecture."""
        logger.debug(f"Handling upsert for {file_path}")

        try:
            # Skip hidden files and system files
            if self._is_hidden_file(file_path):
                logger.debug(f"Skipping hidden/system file: {file_path}")
                return None
            # Check if this is an .eml file
            if file_path.suffix.lower() == '.eml':
                return await self._handle_email_file(file_path)
            
            # Check if this is a .zip file
            if file_path.suffix.lower() == '.zip':
                return await self._handle_zip_file(file_path)

            # 1. Extract and preprocess data
            logger.debug(f"Extracting and preprocessing data for {file_path}")
            processed_data = extract_and_preprocess(str(file_path))
            if "error" in processed_data:
                logger.error(f"Failed to extract/preprocess {file_path}: {processed_data['error']}")
                return None

            # 2. Prepare document metadata
            file_stats = file_path.stat()
            mime_type, _ = mimetypes.guess_type(str(file_path))

            # Calculate MD5 hash
            md5_hash = self._calculate_md5(file_path)

            doc_data = {
                'file_path': str(file_path),
                'filename': file_path.name,
                'extension': file_path.suffix.lower(),
                'size': file_stats.st_size,
                'mime_type': mime_type or 'application/octet-stream',
                'md5_hash': md5_hash,
                'original_text': processed_data.get("original_text", ""),
                'markdown_content': processed_data.get("markdown_content", processed_data.get("original_text", "")),
                'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            }

            # 3. Get AI enrichment using MCP client
            logger.debug(f"Getting AI metadata for {file_path}")
            ai_metadata = await self.mcp_client.analyze_document_with_llm(
                str(file_path),
                file_path.name,
                file_path.suffix.lower(),
                processed_data.get("original_text", "")
            )

            # 4. Store in database using MCP client
            logger.debug(f"Storing document for {file_path}")
            doc_id = await self.mcp_client.store_document_metadata(doc_data, ai_metadata)

            if doc_id:
                logger.info(f"Successfully ingested and stored {file_path} with document ID {doc_id}")
                return doc_id
            else:
                logger.warning(f"Document stored but could not retrieve ID for {file_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return None

    def _handle_delete(self, file_path: Path):
        """Handles deletion of a file."""
        try:
            self.document_store.delete_document_by_path(str(file_path))
            logger.info(f"Successfully deleted {file_path} from the database")
        except Exception as e:
            logger.error(f"Error during deletion for {file_path}: {e}")

    def _handle_move(self, old_path: Path, new_path: Path):
        """Handles moving or renaming a file."""
        try:
            self.document_store.update_document_path(str(old_path), str(new_path))
            logger.info(f"Successfully moved {old_path} to {new_path} in the database")
        except Exception as e:
            logger.error(f"Error during move for {old_path} -> {new_path}: {e}")

    async def _handle_email_file(self, file_path: Path):
        """Handles processing of .eml files and their attachments."""
        logger.info(f"Processing .eml file: {file_path}")
        
        try:
            # Extract email data and attachments
            email_result = extract_email_data(str(file_path))
            eml_data = email_result.get('eml_data')
            processed_attachments = email_result.get('attachments', [])
            logger.info(f"Processing EML file with {len(processed_attachments)} attachments")
            
            file_stats = file_path.stat()
            md5_hash = self._calculate_md5(file_path)
            
            main_doc_id = None
            
            # First, store the EML file itself
            if eml_data:
                email_metadata = eml_data.get('email_metadata', {})
                attachment_list = eml_data.get('attachment_list', [])
                
                # Create summary for the email
                email_summary = self._create_email_summary(
                    email_metadata,
                    eml_data.get('email_body', ''),
                    attachment_list
                )
                
                eml_doc_data = {
                    'file_path': str(file_path),
                    'filename': file_path.name,
                    'extension': file_path.suffix.lower(),
                    'size': file_stats.st_size,
                    'mime_type': 'message/rfc822',
                    'md5_hash': md5_hash,
                    'original_text': eml_data.get('email_body', ''),
                    'markdown_content': eml_data.get('email_body', ''),
                    'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                }
                
                # Add email-specific metadata
                eml_doc_data.update({
                    'email_from': email_metadata.get('from', ''),
                    'email_to': email_metadata.get('to', ''),
                    'email_subject': email_metadata.get('subject', ''),
                    'email_date': email_metadata.get('date', ''),
                    'source_type': 'email_file'
                })
                
                # Get AI enrichment for the email itself
                ai_metadata = await self.mcp_client.analyze_document_with_llm(
                    str(file_path),
                    file_path.name,
                    file_path.suffix.lower(),
                    eml_data.get('email_body', '') + f"\n\nEmail Summary: {email_summary}"
                )
                
                # Override the summary with our custom email summary
                ai_metadata['summary'] = email_summary
                
                # Store EML file in database
                main_doc_id = await self.mcp_client.store_document_metadata(eml_doc_data, ai_metadata)
                
                if main_doc_id:
                    logger.info(f"Successfully stored EML file {file_path.name}")
                else:
                    logger.warning(f"Failed to store EML file {file_path.name}")
            
            # Then, process each attachment as a separate document
            for attachment_data in processed_attachments:
                doc_data = {
                    'file_path': str(file_path),  # Reference to original .eml file
                    'filename': file_path.name,
                    'extension': file_path.suffix.lower(),
                    'size': file_stats.st_size,
                    'mime_type': 'message/rfc822',
                    'md5_hash': attachment_data.get('md5_hash', ''),
                    'original_text': attachment_data.get('original_text', ''),
                    'markdown_content': attachment_data.get('markdown_content', ''),
                    'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                }
                
                # Add email-specific metadata
                email_metadata = attachment_data.get('email_metadata', {})
                doc_data.update({
                    'email_from': email_metadata.get('from', ''),
                    'email_to': email_metadata.get('to', ''),
                    'email_subject': email_metadata.get('subject', ''),
                    'email_date': email_metadata.get('date', ''),
                    'source_type': 'email_attachment'
                })
                
                # Get AI enrichment for attachment
                ai_metadata = await self.mcp_client.analyze_document_with_llm(
                    str(file_path),
                    doc_data['filename'],
                    doc_data['extension'],
                    doc_data['original_text']
                )
                
                # Add context to summary that this is an email attachment
                attachment_name = attachment_data.get('attachment_filename', 'unknown')
                original_summary = ai_metadata.get('summary', '')
                ai_metadata['summary'] = f"Attachment '{attachment_name}' from email {file_path.name}. Content: {original_summary}"
                
                # Store attachment in database
                doc_id = await self.mcp_client.store_document_metadata(doc_data, ai_metadata)
                
                if doc_id:
                    logger.info(f"Stored attachment '{doc_data['filename']}' with ID {doc_id}")
                else:
                    logger.warning(f"Failed to store attachment {doc_data['filename']} from {file_path}")
            
            return main_doc_id
                     
        except Exception as e:
            logger.error(f"Failed to process .eml file {file_path}: {e}")
            return None

    async def _handle_zip_file(self, file_path: Path):
        """Handles processing of .zip files and their document contents."""
        logger.info(f"Processing ZIP file: {file_path}")
        
        try:
            # Extract ZIP data and contents
            zip_result = extract_zip_data(str(file_path))
            zip_data = zip_result.get('zip_data')
            processed_documents = zip_result.get('contents', [])
            
            file_stats = file_path.stat()
            md5_hash = self._calculate_md5(file_path)
            
            main_doc_id = None
            
            # First, store the ZIP file itself
            if zip_data:
                file_list = zip_data.get('file_list', [])
                total_files = zip_data.get('total_files', 0)
                processed_files = zip_data.get('processed_files', 0)
                
                # Create summary for the ZIP file
                zip_summary = self._create_zip_summary(file_list, total_files, processed_files)
                
                zip_doc_data = {
                    'file_path': str(file_path),
                    'filename': file_path.name,
                    'extension': file_path.suffix.lower(),
                    'size': file_stats.st_size,
                    'mime_type': 'application/zip',
                    'md5_hash': md5_hash,
                    'original_text': zip_summary,  # ZIP file list as content
                    'markdown_content': zip_summary,
                    'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                }
                
                # Add ZIP-specific metadata
                zip_doc_data.update({
                    'source_type': 'zip_file'
                })
                
                # Get AI enrichment for the ZIP file itself
                ai_metadata = await self.mcp_client.analyze_document_with_llm(
                    str(file_path),
                    file_path.name,
                    file_path.suffix.lower(),
                    f"ZIP Archive Summary: {zip_summary}"
                )
                
                # Override the summary with our custom ZIP summary
                ai_metadata['summary'] = zip_summary
                
                # Store ZIP file in database
                main_doc_id = await self.mcp_client.store_document_metadata(zip_doc_data, ai_metadata)
                
                if main_doc_id:
                    logger.info(f"Successfully stored ZIP file {file_path.name}")
                else:
                    logger.warning(f"Failed to store ZIP file {file_path.name}")
            
            # Then, process each document as a separate entry
            for document_data in processed_documents:
                doc_data = {
                    'file_path': str(file_path),  # Reference to original .zip file
                    'filename': file_path.name,
                    'extension': Path(document_data.get('zip_internal_path', '')).suffix.lower(),
                    'size': file_stats.st_size,
                    'mime_type': 'application/zip',
                    'md5_hash': document_data.get('md5_hash', ''),
                    'original_text': document_data.get('original_text', ''),
                    'markdown_content': document_data.get('markdown_content', ''),
                    'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                }
                
                # Add ZIP-specific metadata
                doc_data.update({
                    'zip_internal_path': document_data.get('zip_internal_path', ''),
                    'source_type': 'zip_archive'
                })
                
                # Get AI enrichment for ZIP content
                ai_metadata = await self.mcp_client.analyze_document_with_llm(
                    str(file_path),
                    doc_data['filename'],
                    doc_data['extension'],
                    doc_data['original_text']
                )
                
                # Add context to summary that this is part of a ZIP archive
                original_summary = ai_metadata.get('summary', '')
                ai_metadata['summary'] = f"This document is part of {file_path.name}. {original_summary}"
                
                # Store ZIP content in database
                doc_id = await self.mcp_client.store_document_metadata(doc_data, ai_metadata)
                
                if doc_id:
                    logger.info(f"Successfully stored ZIP content {doc_data['filename']} from {file_path}")
                else:
                    logger.warning(f"Failed to store ZIP content {doc_data['filename']} from {file_path}")
            
            return main_doc_id
                     
        except Exception as e:
            logger.error(f"Failed to process ZIP file {file_path}: {e}")
            return None

    def _create_email_summary(self, email_metadata: dict, email_body: str, attachment_list: list) -> str:
        """Create a summary for an email file including body preview."""
        sender = email_metadata.get('from', 'Unknown sender')
        recipient = email_metadata.get('to', 'Unknown recipient')
        subject = email_metadata.get('subject', 'No subject')

        summary = f"Email from {sender} to {recipient}\n"
        summary += f"Subject: {subject}\n\n"

        # Add email body preview (increased limit for complete content)
        if email_body:
            body_preview = email_body[:5000].strip()  # Much higher limit for email bodies
            if len(email_body) > 5000:
                body_preview += "..."
            summary += f"Message: {body_preview}\n\n"

        if attachment_list:
            summary += f"Attachments ({len(attachment_list)}):\n"
            for att in attachment_list:
                summary += f"  - {att}\n"
        else:
            summary += "No attachments\n"

        return summary
    
    def _create_zip_summary(self, file_list: list, total_files: int, processed_files: int) -> str:
        """Create a summary for a ZIP file."""
        if total_files == 0:
            return "Empty ZIP archive"
        
        summary = f"ZIP archive containing {total_files} file{'s' if total_files != 1 else ''}"
        
        if processed_files > 0:
            summary += f" ({processed_files} processed)"
        
        if file_list:
            # Show first few files
            # Show all files in the archive for complete cataloging
            if file_list:
                summary += f": {', '.join(file_list)}"
        
        return summary

    def _calculate_md5(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate MD5 for {file_path}: {e}")
            return ""

    async def cleanup(self):
        """Clean up MCP client resources."""
        if self.mcp_client:
            await self.mcp_client.cleanup()

async def main():
    """Main entry point for testing the ingestion process."""
    import asyncio
    from src.core.simple_config import settings
    from src.core.logging_config import setup_logging

    # Setup logging
    setup_logging()
    logger.info("Starting ingestion process test")

    # Initialize document store
    document_store = DocumentStore()
    orchestrator = IngestionOrchestrator(document_store)

    try:
        # Process all files in watch directories
        for watch_dir in settings.watch_directories:
            watch_path = Path(watch_dir)
            if not watch_path.exists():
                logger.warning(f"Watch directory does not exist: {watch_dir}")
                continue

            logger.info(f"Processing files in: {watch_dir}")

            # Get all files in directory
            files = []
            for ext in settings.file_extensions:
                files.extend(watch_path.glob(f"*{ext}"))

            logger.info(f"Found {len(files)} files to process")

            # Process each file
            for file_path in files:
                if file_path.is_file() and file_path.stat().st_size <= settings.max_file_size_bytes:
                    event = FileEvent(
                        event_type=FileEventType.CREATED,
                        file_path=file_path,
                        timestamp=datetime.now()
                    )
                    await orchestrator.process_file_event(event)
                else:
                    logger.debug(f"Skipping {file_path}: too large or not a file")

    except Exception as e:
        logger.error(f"Error in main ingestion process: {e}")
    finally:
        await orchestrator.cleanup()
        logger.info("Ingestion process completed")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())