#!/usr/bin/env python3
"""
Simple test of email processing without MCP dependencies
Tests .eml files and generates detailed report
"""

import sys
from pathlib import Path
import json
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.extractors.email_extractor import extract_email_attachments
from src.core.logging_config import setup_logging
import zipfile
import tempfile
from src.extractors.docling_extractor import extract_and_preprocess

def test_email_processing():
    """Test email processing functionality"""
    setup_logging()
    logger.info("Starting email processing test")
    
    test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
    
    # Test .eml files
    eml_files = list(test_dir.glob("*.eml"))
    logger.info(f"Found {len(eml_files)} .eml files")
    
    results = []
    
    for eml_file in eml_files:
        logger.info(f"Processing {eml_file.name}")
        
        try:
            # Extract attachments
            attachments = extract_email_attachments(str(eml_file))
            
            result = {
                "filename": eml_file.name,
                "size": eml_file.stat().st_size,
                "attachments_found": len(attachments),
                "attachments": []
            }
            
            for i, attachment in enumerate(attachments):
                att_info = {
                    "index": i+1,
                    "filename": attachment.get("attachment_filename", "unknown"),
                    "content_length": len(attachment.get("original_text", "")),
                    "email_metadata": {
                        "from": attachment.get("email_metadata", {}).get("from", ""),
                        "to": attachment.get("email_metadata", {}).get("to", ""),
                        "subject": attachment.get("email_metadata", {}).get("subject", ""),
                        "date": attachment.get("email_metadata", {}).get("date", "")
                    }
                }
                
                # Get content preview
                content = attachment.get("original_text", "")
                if content:
                    att_info["content_preview"] = content[:300] + "..." if len(content) > 300 else content
                
                result["attachments"].append(att_info)
            
            results.append(result)
            logger.info(f"✓ {eml_file.name}: {len(attachments)} attachments")
            
        except Exception as e:
            logger.error(f"✗ Failed to process {eml_file.name}: {e}")
            results.append({
                "filename": eml_file.name,
                "size": eml_file.stat().st_size,
                "attachments_found": 0,
                "error": str(e)
            })
    
    # Generate detailed report
    print("\n" + "="*80)
    print("EMAIL PROCESSING TEST RESULTS")
    print("="*80)
    
    for result in results:
        print(f"\nFile: {result['filename']}")
        print(f"Size: {result['size']:,} bytes")
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            continue
            
        print(f"📎 Attachments: {result['attachments_found']}")
        
        for att in result['attachments']:
            print(f"  {att['index']}. {att['filename']}")
            print(f"     Content: {att['content_length']:,} characters")
            if att['email_metadata']['subject']:
                print(f"     Subject: {att['email_metadata']['subject'][:50]}...")
            if att['email_metadata']['from']:
                print(f"     From: {att['email_metadata']['from'][:50]}...")
            if att.get('content_preview'):
                preview = att['content_preview'].replace('\n', ' ')[:100]
                print(f"     Preview: {preview}...")
    
    print(f"\n📊 Summary:")
    print(f"   Files processed: {len(results)}")
    print(f"   Total attachments: {sum(r.get('attachments_found', 0) for r in results)}")
    print(f"   Files with attachments: {sum(1 for r in results if r.get('attachments_found', 0) > 0)}")
    
    # Test ZIP files too
    print(f"\n" + "="*80)
    print("ZIP FILE ANALYSIS")
    print("="*80)
    
    zip_files = list(test_dir.glob("*.zip"))
    
    for zip_file in zip_files:
        print(f"\nFile: {zip_file.name}")
        print(f"Size: {zip_file.stat().st_size:,} bytes")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    zf.extractall(temp_path)
                
                doc_files = []
                for extracted_file in temp_path.rglob('*'):
                    if extracted_file.is_file() and not extracted_file.name.startswith('._'):
                        if extracted_file.suffix.lower() in {'.pdf', '.doc', '.docx', '.txt', '.rtf'}:
                            doc_files.append(extracted_file.name)
                
                print(f"📄 Document files: {len(doc_files)}")
                for doc in doc_files:
                    print(f"   - {doc}")
                    
        except Exception as e:
            print(f"❌ Error processing zip: {e}")

if __name__ == "__main__":
    test_email_processing()