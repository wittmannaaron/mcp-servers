#!/usr/bin/env python3
"""
Debug script to test last_insert_rowid() behavior with MCP server.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.mcp_client import get_mcp_client

async def test_rowid():
    """Test what last_insert_rowid() returns."""
    async with get_mcp_client() as client:
        # First, let's see what's in the database
        result = await client.read_query("SELECT id, filename FROM documents LIMIT 5")
        print("Current documents in database:")
        for row in result:
            print(f"  ID: {row.get('id')}, Filename: {row.get('filename')}")
        
        # Test last_insert_rowid()
        print("\nTesting last_insert_rowid():")
        result = await client.read_query("SELECT last_insert_rowid() as last_id")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        if result:
            print(f"First row: {result[0]}")
            print(f"Keys in first row: {list(result[0].keys())}")
            for key, value in result[0].items():
                print(f"  {key}: {value} (type: {type(value)})")

if __name__ == "__main__":
    asyncio.run(test_rowid())