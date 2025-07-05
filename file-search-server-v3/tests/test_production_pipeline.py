#!/usr/bin/env python3
"""
Test the email processing by running files through the actual production pipeline
and then verify results using MCP tools
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.extractors.email_extractor import extract_email_attachments
from src.core.logging_config import setup_logging

def test_email_extraction():
    """Test email extraction without MCP dependencies"""
    setup_logging()
    logger.info("Testing email extraction functionality")
    
    test_dir = Path("/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958")
    
    print("\n" + "="*80)
    print("EMAIL PROCESSING EXTRACTION TEST")
    print("="*80)
    
    # Test the two files with attachments
    test_files = [
        "Ihring ._. Ihring.eml",
        "Ihring ._. Ihring,  3 F 248_24 (Strreitwert).eml"
    ]
    
    processed_docs = []
    
    for filename in test_files:
        eml_file = test_dir / filename
        if not eml_file.exists():
            print(f"❌ File not found: {filename}")
            continue
            
        print(f"\n🔄 Processing: {filename}")
        
        try:
            # Extract attachments using our email extractor
            attachments = extract_email_attachments(str(eml_file))
            
            print(f"   📎 Attachments found: {len(attachments)}")
            
            for i, attachment in enumerate(attachments, 1):
                doc_info = {
                    "source_eml": filename,
                    "attachment_filename": attachment.get("attachment_filename", "unknown"),
                    "content_length": len(attachment.get("original_text", "")),
                    "email_metadata": attachment.get("email_metadata", {}),
                    "content_preview": attachment.get("original_text", "")[:200]
                }
                
                processed_docs.append(doc_info)
                
                print(f"   {i}. {doc_info['attachment_filename']}")
                print(f"      Content: {doc_info['content_length']} characters")
                print(f"      From: {doc_info['email_metadata'].get('from', 'Unknown')[:50]}...")
                print(f"      Subject: {doc_info['email_metadata'].get('subject', 'Unknown')[:50]}...")
                print(f"      Preview: {doc_info['content_preview'][:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n📊 Summary: {len(processed_docs)} documents extracted")
    return processed_docs

def verify_database_content():
    """Check what's currently in the production database using MCP tools"""
    print(f"\n" + "="*80)
    print("DATABASE CONTENT VERIFICATION")
    print("="*80)
    
    try:
        # Import the MCP tools directly
        import mcp__sqlite_filebrowser__read_query
        import mcp__sqlite_filebrowser__describe_table
        
        # Check total documents
        print("Using MCP tools to query the database...")
        
    except ImportError:
        print("MCP tools not available in test environment")
        print("Please use the following commands to check the database:")
        print()
        print("1. Check total documents:")
        print("   Use MCP tool: read_query with 'SELECT COUNT(*) FROM documents'")
        print()
        print("2. Check for email-related documents:")
        print("   Use MCP tool: read_query with 'SELECT * FROM documents WHERE file_path LIKE \"%eml%\" OR filename LIKE \"%Ihring%\"'")
        print()
        print("3. Search for legal content:")
        print("   Use MCP tool: read_query with 'SELECT filename, summary FROM documents WHERE original_text LIKE \"%Familiensache%\"'")
        print()
        print("4. Recent documents:")
        print("   Use MCP tool: read_query with 'SELECT filename, indexed_at FROM documents ORDER BY indexed_at DESC LIMIT 10'")

if __name__ == "__main__":
    # Test email extraction
    processed_docs = test_email_extraction()
    
    # Show database verification steps
    verify_database_content()
    
    print(f"\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("To complete the test, please:")
    print("1. Run the main ingestion pipeline with these .eml files")
    print("2. Use MCP tools to verify the documents were stored")
    print("3. Check that email metadata is preserved")
    print()
    print("Expected results in database:")
    for doc in processed_docs:
        print(f"📄 Document: {doc['attachment_filename']}")
        print(f"   Source: {doc['source_eml']}")
        print(f"   Content length: {doc['content_length']} chars")
        print(f"   Should contain: 'Familiensache', 'court', legal terms")
    
    print(f"\n✅ Email extraction test completed!")
    print(f"📂 Test files location: /Users/aaron/Documents/Anke_docs_bak_19-07-24-0958/")
    print(f"🗄️  Production database: /Users/aaron/Projects/Simple_MCP_DB/filebrowser.db")