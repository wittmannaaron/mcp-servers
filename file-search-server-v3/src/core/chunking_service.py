"""
Context-Aware Chunking Service for Markdown Content.
"""
from typing import List
from langchain.text_splitter import MarkdownHeaderTextSplitter

def chunk_text(markdown_text: str) -> List[str]:
    """
    Splits Markdown text into chunks based on headers, preserving context.

    Args:
        markdown_text: The Markdown content to be chunked.

    Returns:
        A list of text chunks.
    """
    if not markdown_text or not markdown_text.strip():
        return []

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    fragments = markdown_splitter.split_text(markdown_text)

    # We only need the page_content from the resulting Document objects
    return [fragment.page_content for fragment in fragments]

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
