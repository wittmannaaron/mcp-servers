#!/usr/bin/env python3
"""
Test script to verify the chunking fix works correctly.
"""
from src.core.chunking_service import chunk_text

def test_chunking_fix():
    """Test that chunking now respects the 4000 character limit."""
    
    # Create a test document with very long content (similar to problematic documents)
    long_content = "This is a very long paragraph that should be split into multiple chunks. " * 300  # ~21000 characters
    
    test_markdown = f"""# Document Title

{long_content}

## Another Section

{long_content}

This is the end of the document.
"""
    
    print("=== TESTING CHUNKING FIX ===")
    print(f"Original document length: {len(test_markdown)} characters")
    print("=" * 80)
    
    # Test with explicit max_chunk_size parameter (like in the fixed ingestion.py)
    chunks = chunk_text(test_markdown, max_chunk_size=4000)
    
    print(f"Number of chunks created: {len(chunks)}")
    print("=" * 80)
    
    # Analyze all chunks
    oversized_chunks = []
    total_chars = 0
    
    for i, chunk in enumerate(chunks):
        chunk_size = len(chunk)
        total_chars += chunk_size
        print(f"Chunk {i+1}: {chunk_size} characters")
        
        if chunk_size > 4000:
            oversized_chunks.append(i+1)
            print(f"  ⚠️  OVERSIZED CHUNK! ({chunk_size} > 4000)")
            print(f"  First 100 chars: {repr(chunk[:100])}")
            print(f"  Last 100 chars: {repr(chunk[-100:])}")
            print()
    
    print("=" * 80)
    print(f"Total characters in all chunks: {total_chars}")
    print(f"Original document characters: {len(test_markdown)}")
    print(f"Character difference: {abs(total_chars - len(test_markdown))}")
    
    if oversized_chunks:
        print(f"❌ FAILED: Found {len(oversized_chunks)} oversized chunks: {oversized_chunks}")
        return False
    else:
        print("✅ SUCCESS: All chunks are within the 4000 character limit!")
        return True

def test_edge_cases():
    """Test edge cases for chunking."""
    
    print("\n=== TESTING EDGE CASES ===")
    
    # Test 1: Document with no headers
    no_headers = "This is a document without any headers. " * 200  # ~8000 characters
    chunks = chunk_text(no_headers, max_chunk_size=4000)
    print(f"No headers test: {len(chunks)} chunks, max size: {max(len(c) for c in chunks)}")
    
    # Test 2: Document with only one very long paragraph
    one_paragraph = "A" * 10000  # Exactly 10000 characters
    chunks = chunk_text(one_paragraph, max_chunk_size=4000)
    print(f"One paragraph test: {len(chunks)} chunks, max size: {max(len(c) for c in chunks)}")
    
    # Test 3: Document with multiple headers but long sections
    multi_headers = """# Header 1
""" + ("Content for section 1. " * 200) + """

## Header 2
""" + ("Content for section 2. " * 200) + """

### Header 3
""" + ("Content for section 3. " * 200)
    
    chunks = chunk_text(multi_headers, max_chunk_size=4000)
    print(f"Multi headers test: {len(chunks)} chunks, max size: {max(len(c) for c in chunks)}")
    
    # Check if any chunks are oversized
    all_within_limit = all(len(chunk) <= 4000 for chunk in chunks)
    print(f"All edge case chunks within limit: {'✅ YES' if all_within_limit else '❌ NO'}")
    
    return all_within_limit

if __name__ == "__main__":
    print("Testing chunking service fix...")
    
    success1 = test_chunking_fix()
    success2 = test_edge_cases()
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED! The chunking fix is working correctly.")
    else:
        print("\n❌ SOME TESTS FAILED! There may still be issues with the chunking.")