#!/usr/bin/env python3
"""
Test script for email processing pipeline
Tests .eml files and zip files from the test directory
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.ingestion import IngestionOrchestrator
from src.core.events import FileEvent, FileEventType
from src.database.database import DocumentStore
from src.extractors.email_extractor import extract_email_attachments
from src.core.logging_config import setup_logging
import zipfile
import tempfile
from src.extractors.docling_extractor import extract_and_preprocess

class EmailProcessingTester:
    def __init__(self):
        self.test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "eml_files": [],
            "zip_files": [],
            "total_documents_processed": 0,
            "errors": []
        }
        
    async def run_comprehensive_test(self):
        """Run comprehensive test of email and zip processing"""
        logger.info("Starting comprehensive test of email processing pipeline")
        
        # Setup logging
        setup_logging()
        
        # Initialize document store and orchestrator
        document_store = DocumentStore()
        orchestrator = IngestionOrchestrator(document_store)
        
        try:
            # Test .eml files
            await self._test_eml_files(orchestrator)
            
            # Test .zip files
            await self._test_zip_files(orchestrator)
            
            # Generate report
            await self._generate_report()
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            self.results["errors"].append(f"Test failed: {e}")
        finally:
            await orchestrator.cleanup()
            
    async def _test_eml_files(self, orchestrator):
        """Test all .eml files in the test directory"""
        logger.info("Testing .eml files")
        
        eml_files = list(self.test_dir.glob("*.eml"))
        logger.info(f"Found {len(eml_files)} .eml files")
        
        for eml_file in eml_files:
            try:
                logger.info(f"Processing {eml_file.name}")
                
                # Extract attachments directly first to analyze
                attachments = extract_email_attachments(str(eml_file))
                
                eml_result = {
                    "filename": eml_file.name,
                    "size": eml_file.stat().st_size,
                    "attachments": [],
                    "total_attachments": len(attachments),
                    "processed_successfully": True,
                    "error": None
                }
                
                # Analyze each attachment
                for attachment in attachments:
                    attachment_info = {
                        "filename": attachment.get("attachment_filename", "unknown"),
                        "has_content": bool(attachment.get("original_text")),
                        "content_length": len(attachment.get("original_text", "")),
                        "email_metadata": attachment.get("email_metadata", {}),
                        "source_type": attachment.get("source_type", "unknown")
                    }
                    
                    # Get summary of content (first 200 chars)
                    content = attachment.get("original_text", "")
                    if content:
                        attachment_info["content_summary"] = content[:200] + "..." if len(content) > 200 else content
                    
                    eml_result["attachments"].append(attachment_info)
                
                # Test with ingestion pipeline
                event = FileEvent(
                    event_type=FileEventType.CREATED,
                    file_path=eml_file,
                    timestamp=datetime.now()
                )
                await orchestrator.process_file_event(event)
                
                self.results["eml_files"].append(eml_result)
                self.results["total_documents_processed"] += len(attachments)
                
                logger.info(f"Successfully processed {eml_file.name} - {len(attachments)} attachments")
                
            except Exception as e:
                logger.error(f"Failed to process {eml_file.name}: {e}")
                eml_result = {
                    "filename": eml_file.name,
                    "size": eml_file.stat().st_size,
                    "attachments": [],
                    "total_attachments": 0,
                    "processed_successfully": False,
                    "error": str(e)
                }
                self.results["eml_files"].append(eml_result)
                self.results["errors"].append(f"EML processing error for {eml_file.name}: {e}")
                
    async def _test_zip_files(self, orchestrator):
        """Test all .zip files in the test directory"""
        logger.info("Testing .zip files")
        
        zip_files = list(self.test_dir.glob("*.zip"))
        logger.info(f"Found {len(zip_files)} .zip files")
        
        for zip_file in zip_files:
            try:
                logger.info(f"Processing {zip_file.name}")
                
                zip_result = {
                    "filename": zip_file.name,
                    "size": zip_file.stat().st_size,
                    "contents": [],
                    "total_files": 0,
                    "processed_successfully": True,
                    "error": None
                }
                
                # Extract and analyze zip contents
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    with zipfile.ZipFile(zip_file, 'r') as zf:
                        zf.extractall(temp_path)
                    
                    # Process each file in the zip
                    for extracted_file in temp_path.rglob('*'):
                        if extracted_file.is_file():
                            file_info = {
                                "filename": extracted_file.name,
                                "relative_path": str(extracted_file.relative_to(temp_path)),
                                "size": extracted_file.stat().st_size,
                                "extension": extracted_file.suffix.lower(),
                                "processed": False,
                                "content_summary": None,
                                "error": None
                            }
                            
                            # Try to process document files
                            if extracted_file.suffix.lower() in {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}:
                                try:
                                    processed_data = extract_and_preprocess(str(extracted_file))
                                    if "error" not in processed_data:
                                        file_info["processed"] = True
                                        content = processed_data.get("original_text", "")
                                        if content:
                                            file_info["content_summary"] = content[:200] + "..." if len(content) > 200 else content
                                    else:
                                        file_info["error"] = processed_data.get("error", "Unknown error")
                                except Exception as e:
                                    file_info["error"] = str(e)
                            
                            zip_result["contents"].append(file_info)
                            zip_result["total_files"] += 1
                
                # Test with ingestion pipeline (this will use docling_extractor for zip files)
                event = FileEvent(
                    event_type=FileEventType.CREATED,
                    file_path=zip_file,
                    timestamp=datetime.now()
                )
                await orchestrator.process_file_event(event)
                
                self.results["zip_files"].append(zip_result)
                self.results["total_documents_processed"] += zip_result["total_files"]
                
                logger.info(f"Successfully processed {zip_file.name} - {zip_result['total_files']} files")
                
            except Exception as e:
                logger.error(f"Failed to process {zip_file.name}: {e}")
                zip_result = {
                    "filename": zip_file.name,
                    "size": zip_file.stat().st_size,
                    "contents": [],
                    "total_files": 0,
                    "processed_successfully": False,
                    "error": str(e)
                }
                self.results["zip_files"].append(zip_result)
                self.results["errors"].append(f"ZIP processing error for {zip_file.name}: {e}")
                
    async def _generate_report(self):
        """Generate comprehensive test report"""
        logger.info("Generating test report")
        
        # Save detailed results to JSON
        report_file = Path("test_results.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Generate human-readable summary
        summary_file = Path("test_summary.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("EMAIL PROCESSING PIPELINE TEST RESULTS\n")
            f.write("=" * 50 + "\n")
            f.write(f"Test Date: {self.results['timestamp']}\n\n")
            
            f.write("EML FILES PROCESSED:\n")
            f.write("-" * 30 + "\n")
            for eml in self.results["eml_files"]:
                f.write(f"File: {eml['filename']}\n")
                f.write(f"Size: {eml['size']:,} bytes\n")
                f.write(f"Attachments: {eml['total_attachments']}\n")
                f.write(f"Success: {eml['processed_successfully']}\n")
                if eml['error']:
                    f.write(f"Error: {eml['error']}\n")
                
                for att in eml['attachments']:
                    f.write(f"  - {att['filename']}\n")
                    f.write(f"    Content Length: {att['content_length']} chars\n")
                    if att.get('content_summary'):
                        f.write(f"    Summary: {att['content_summary'][:100]}...\n")
                f.write("\n")
            
            f.write("ZIP FILES PROCESSED:\n")
            f.write("-" * 30 + "\n")
            for zip_file in self.results["zip_files"]:
                f.write(f"File: {zip_file['filename']}\n")
                f.write(f"Size: {zip_file['size']:,} bytes\n")
                f.write(f"Contents: {zip_file['total_files']} files\n")
                f.write(f"Success: {zip_file['processed_successfully']}\n")
                if zip_file['error']:
                    f.write(f"Error: {zip_file['error']}\n")
                
                for content in zip_file['contents']:
                    f.write(f"  - {content['filename']} ({content['extension']})\n")
                    f.write(f"    Size: {content['size']:,} bytes\n")
                    f.write(f"    Processed: {content['processed']}\n")
                    if content.get('content_summary'):
                        f.write(f"    Summary: {content['content_summary'][:100]}...\n")
                    if content.get('error'):
                        f.write(f"    Error: {content['error']}\n")
                f.write("\n")
            
            f.write("SUMMARY:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total EML files: {len(self.results['eml_files'])}\n")
            f.write(f"Total ZIP files: {len(self.results['zip_files'])}\n")
            f.write(f"Total documents processed: {self.results['total_documents_processed']}\n")
            f.write(f"Total errors: {len(self.results['errors'])}\n")
            
            if self.results['errors']:
                f.write("\nERRORS:\n")
                for error in self.results['errors']:
                    f.write(f"- {error}\n")
        
        logger.info(f"Test report saved to {report_file}")
        logger.info(f"Summary saved to {summary_file}")

async def main():
    """Main entry point for testing"""
    tester = EmailProcessingTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())