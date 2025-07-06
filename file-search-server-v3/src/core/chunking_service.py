"""
Context-Aware Chunking Service for Markdown Content.
"""
from typing import List
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

def chunk_text(markdown_text: str, max_chunk_size: int = 4000) -> List[str]:
    """
    Splits Markdown text into chunks based on headers, preserving context.
    Large chunks are further split at sentence/paragraph boundaries to respect max_chunk_size.

    Args:
        markdown_text: The Markdown content to be chunked.
        max_chunk_size: Maximum size for chunks in characters (default: 4000).

    Returns:
        A list of text chunks, each respecting the maximum size while maintaining semantic coherence.
    """
    if not markdown_text or not markdown_text.strip():
        return []

    # First level: Split by headers for semantic structure
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    fragments = markdown_splitter.split_text(markdown_text)

    # Second level: Split large chunks while preserving semantic boundaries
    final_chunks = []
    
    # Configure recursive splitter for semantic boundaries
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=200,  # Small overlap to maintain context
        separators=[
            "\n\n",  # Paragraph breaks (highest priority)
            "\n",    # Line breaks
            ". ",    # Sentence endings
            "! ",    # Exclamation sentences
            "? ",    # Question sentences
            "; ",    # Semicolon breaks
            ", ",    # Comma breaks
            " ",     # Word breaks
            ""       # Character breaks (last resort)
        ],
        length_function=len,
        is_separator_regex=False,
    )
    
    for fragment in fragments:
        chunk_content = fragment.page_content
        
        # If chunk is within size limit, keep as is
        if len(chunk_content) <= max_chunk_size:
            final_chunks.append(chunk_content)
        else:
            # Split large chunks while preserving semantic boundaries
            sub_chunks = recursive_splitter.split_text(chunk_content)
            final_chunks.extend(sub_chunks)
    
    return final_chunks

if __name__ == '__main__':
    # Example Usage
    sample_markdown = """
# Introduction

This is the first section.

## Subsection 1.1

Here is some content for the first subsection.

### Sub-subsection 1.1.1

Deeper content here.

# Chapter 2

This is the second chapter. It has some lists.

- Item 1
- Item 2

## Subsection 2.1

Content for the second chapter's subsection.
"""
    chunks = chunk_text(sample_markdown)
    for i, chunk in enumerate(chunks):
        print(f"--- CHUNK {i+1} ---")
        print(chunk)
        print()
