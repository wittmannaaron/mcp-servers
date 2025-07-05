"""
MCP Python SDK Client Integration for FileBrowser.

This module provides MCP client functionality to connect to official SQLite MCP Server
with proper async context management to prevent task group violations.

Architectural Compliance:
- File size ≤ 200 lines enforced
- No direct database/LLM calls allowed
- Uses MCP Python SDK exclusively for external operations
- Proper async context management for resource cleanup
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from pathlib import Path
from loguru import logger

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.core.simple_config import settings


class MCPClientManager:
    """
    Async context manager for MCP client connections.

    Creates fresh connections per request to avoid task group violations
    and ensures proper resource cleanup within the same async context.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize MCP client manager with SQLite server configuration."""
        self.db_path = db_path or Path("src/database/filebrowser.db")
        self.session: Optional[ClientSession] = None
        self.tools = []
        self._read_stream = None
        self._write_stream = None

    async def __aenter__(self):
        """Enter async context and create MCP connection."""
        try:
            # Configure official SQLite MCP Server parameters
            server_params = StdioServerParameters(
                command="uv",
                args=[
                    "--directory", "/Users/aaron/Projects/mcp-servers/src/sqlite",
                    "run", "mcp-server-sqlite",
                    "--db-path", "/Users/aaron/Projects/Simple_MCP_DB/filebrowser.db"
                ],
            )

            # Use proper async context management for stdio_client
            from contextlib import AsyncExitStack
            self._exit_stack = AsyncExitStack()

            # Enter the stdio_client context properly
            self._read_stream, self._write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            # Enter the ClientSession context properly
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(self._read_stream, self._write_stream)
            )

            # Initialize connection
            await self.session.initialize()

            # List available tools
            tools_result = await self.session.list_tools()
            self.tools = tools_result.tools

            logger.debug(f"MCP client connected: {len(self.tools)} tools available")
            return self

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self._cleanup()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context and cleanup resources."""
        await self._cleanup()

    async def _cleanup(self):
        """Cleanup MCP connection resources."""
        try:
            if hasattr(self, '_exit_stack') and self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None

            self.session = None
            self._read_stream = None
            self._write_stream = None

            logger.debug("MCP client disconnected and cleaned up")
        except Exception as e:
            logger.error(f"Error during MCP cleanup: {e}")

    def _format_query(self, query: str, params: Optional[List] = None) -> str:
        """Format query with parameters."""
        if not params:
            return query
        formatted_query = query
        for param in params:
            if param is None:
                formatted_query = formatted_query.replace('?', 'NULL', 1)
            else:
                # Properly escape single quotes in parameters
                escaped_param = str(param).replace("'", "''")
                formatted_query = formatted_query.replace('?', f"'{escaped_param}'", 1)
        return formatted_query

    def _parse_result(self, result) -> Any:
        """Parse MCP result content."""
        if result.content and hasattr(result.content[0], 'text'):
            text = result.content[0].text
            # Check if this is a database error message
            if text.startswith("Database error"):
                raise RuntimeError(text)
            try:
                import ast
                return ast.literal_eval(text)
            except (ValueError, SyntaxError) as e:
                # If literal_eval fails, treat as error message
                raise RuntimeError(f"MCP result parsing failed: {text}")
        return []

    async def read_query(self, query: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query using MCP read_query tool."""
        try:
            formatted_query = self._format_query(query, params)
            result = await self.session.call_tool("read_query", {"query": formatted_query})
            return self._parse_result(result)
        except Exception as e:
            logger.error(f"MCP read_query failed: {e}")
            raise

    async def write_query(self, query: str, params: Optional[List] = None) -> Dict[str, Any]:
        """Execute INSERT/UPDATE/DELETE query using MCP write_query tool."""
        try:
            formatted_query = self._format_query(query, params)
            result = await self.session.call_tool("write_query", {"query": formatted_query})
            parsed = self._parse_result(result)
            return parsed if isinstance(parsed, dict) else {"affected_rows": 0}
        except Exception as e:
            logger.error(f"MCP write_query failed: {e}")
            raise

    async def list_tables(self) -> List[str]:
        """List all tables using MCP list_tables tool."""
        try:
            result = await self.session.call_tool("list_tables", {})
            parsed = self._parse_result(result)
            return [table['name'] for table in parsed] if isinstance(parsed, list) else []
        except Exception as e:
            logger.error(f"MCP list_tables failed: {e}")
            raise

    async def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Describe table schema using MCP describe_table tool."""
        try:
            result = await self.session.call_tool("describe_table", {"table_name": table_name})
            parsed = self._parse_result(result)
            return parsed if isinstance(parsed, dict) else {}
        except Exception as e:
            logger.error(f"MCP describe_table failed: {e}")
            raise

    async def create_table(self, query: str) -> Dict[str, Any]:
        """Create table using MCP create_table tool."""
        try:
            result = await self.session.call_tool("create_table", {"query": query})
            return result.content[0] if result.content else {}
        except Exception as e:
            logger.error(f"MCP create_table failed: {e}")
            raise


@asynccontextmanager
async def get_mcp_client(db_path: Optional[Path] = None):
    """
    Async context manager for MCP client operations.

    Creates a fresh connection per request to avoid task group violations.
    Ensures proper resource cleanup within the same async context.

    Usage:
        async with get_mcp_client() as client:
            results = await client.read_query("SELECT * FROM documents")
    """
    async with MCPClientManager(db_path) as client:
        yield client


# Legacy compatibility - deprecated, use get_mcp_client() context manager instead
async def close_mcp_client() -> None:
    """Legacy method - no longer needed with context manager pattern."""
    logger.debug("close_mcp_client() called - no action needed with context manager pattern")