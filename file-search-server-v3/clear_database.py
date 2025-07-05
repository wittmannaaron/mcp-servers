import asyncio
from src.core.mcp_client import get_mcp_client

async def main():
    """Clears the documents and documents_fts tables in the database."""
    async with get_mcp_client() as client:
        await client.write_query("DROP TABLE IF EXISTS documents;")
        print("'documents' table dropped.")
        await client.write_query("DROP TABLE IF EXISTS documents_fts;")
        print("'documents_fts' table dropped.")

if __name__ == "__main__":
    asyncio.run(main())