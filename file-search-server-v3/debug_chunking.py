#!/usr/bin/env python3
"""
Debug script to test chunking behavior with problematic documents.
"""
import sqlite3
from src.core.chunking_service import chunk_text

def test_chunking_from_database():
    """Test chunking with the problematic document from database."""
    
    # Connect to database
    conn = sqlite3.connect('data/filebrowser.db')
    cursor = conn.cursor()
    
    # Get the problematic document (id 140)
    cursor.execute("SELECT id, file_path, markdown_content FROM documents WHERE id = 140")
    result = cursor.fetchone()
    
    if not result:
        print("Document with id 140 not found!")
        return
    
    doc_id, file_path, markdown_content = result
    print(f"Testing document: {file_path}")
    print(f"Original markdown length: {len(markdown_content)} characters")
    print("=" * 80)
    
    # Test current chunking
    chunks = chunk_text(markdown_content)
    
    print(f"Number of chunks created: {len(chunks)}")
    print("=" * 80)
    
    # Analyze chunk sizes
    for i, chunk in enumerate(chunks):
        chunk_size = len(chunk)
        print(f"Chunk {i+1}: {chunk_size} characters")
        
        if chunk_size > 4000:
            print(f"  ⚠️  OVERSIZED CHUNK! ({chunk_size} > 4000)")
            print(f"  First 200 chars: {repr(chunk[:200])}")
            print(f"  Last 200 chars: {repr(chunk[-200:])}")
            print()
    
    conn.close()

def test_chunking_with_simple_case():
    """Test with a simple case that should trigger the problem."""
    
    # Create a test case: one header followed by very long content
    long_content = "This is a very long paragraph. " * 500  # ~15000 characters
    
    test_markdown = f"""# Test Header

{long_content}

This is the end of the document.
"""
    
    print("Testing simple case:")
    print(f"Original length: {len(test_markdown)} characters")
    print("=" * 80)
    
    chunks = chunk_text(test_markdown)
    
    print(f"Number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        chunk_size = len(chunk)
        print(f"Chunk {i+1}: {chunk_size} characters")
        if chunk_size > 4000:
            print(f"  ⚠️  OVERSIZED CHUNK! ({chunk_size} > 4000)")

def debug_markdown_splitter():
    """Debug the MarkdownHeaderTextSplitter behavior."""
    from langchain.text_splitter import MarkdownHeaderTextSplitter
    
    # Test case with one header and long content
    long_content = "This is a very long paragraph. " * 500
    test_markdown = f"""# Test Header

{long_content}

This is the end.
"""
    
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"), 
        ("###", "Header 3"),
    ]
    
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    fragments = markdown_splitter.split_text(test_markdown)
    
    print("MarkdownHeaderTextSplitter results:")
    print(f"Number of fragments: {len(fragments)}")
    
    for i, fragment in enumerate(fragments):
        content = fragment.page_content
        print(f"Fragment {i+1}: {len(content)} characters")
        print(f"  Metadata: {fragment.metadata}")
        print(f"  First 100 chars: {repr(content[:100])}")
        print()

if __name__ == "__main__":
    print("=== DEBUGGING CHUNKING SERVICE ===")
    print()
    
    print("1. Testing MarkdownHeaderTextSplitter behavior:")
    debug_markdown_splitter()
    print()
    
    print("2. Testing simple case:")
    test_chunking_with_simple_case()
    print()
    
    print("3. Testing problematic document from database:")
    try:
        test_chunking_from_database()
    except Exception as e:
        print(f"Error testing database document: {e}")