"""
MCP Client for Ingestion Process.
Handles LLM communication and document analysis using MCP protocol.
"""

import asyncio
import json
import httpx
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.core.llm_prompts import get_document_analysis_prompt, get_ollama_system_prompt, get_error_fallback_metadata


class IngestionMCPClient:
    """MCP Client for document analysis during ingestion process."""

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools = []
        self.ollama_base_url = "http://localhost:11434"

    async def connect(self) -> bool:
        """Connect to SQLite MCP Server."""
        try:
            # Server parameters matching the working configuration
            server_params = StdioServerParameters(
                command="uv",
                args=[
                    "--directory",
                    "/Users/aaron/Projects/mcp-servers/src/sqlite",
                    "run",
                    "mcp-server-sqlite",
                    "--db-path",
                    "/Users/aaron/Projects/Simple_MCP_DB/filebrowser.db"
                ],
                env=None
            )

            # Establish connection
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            # Initialize session
            await self.session.initialize()

            # Get available tools
            response = await self.session.list_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in response.tools
            ]

            logger.debug(f"MCP Client connected. Available tools: {[t['name'] for t in self.tools]}")

            # Initialize database schema
            await self._initialize_database_schema()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def analyze_document_with_llm(self, file_path: str, filename: str, extension: str, original_text: str) -> Dict[str, Any]:
        """
        Analyze document content using LLM and return structured metadata.

        Args:
            file_path: Full path to the document
            filename: Name of the file
            extension: File extension
            original_text: Extracted text content

        Returns:
            Dictionary with structured metadata
        """
        try:
            # Generate prompt for document analysis
            prompt = get_document_analysis_prompt(file_path, filename, extension, original_text)
            system_prompt = get_ollama_system_prompt()

            # Call Ollama LLM
            llm_response = await self._call_ollama(prompt, system_prompt)

            # Parse JSON response with robust error handling
            try:
                # First try direct parsing
                metadata = json.loads(llm_response)
                logger.debug(f"Successfully analyzed document: {filename}")
                return metadata
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON for {filename}: {e}")
                logger.debug(f"Raw LLM response (first 500 chars): {llm_response[:500]}...")
                
                # Try multiple extraction strategies
                metadata = self._extract_json_from_response(llm_response, filename)
                if metadata:
                    return metadata
                
                logger.warning(f"Using fallback metadata for {filename} due to unparseable LLM response")
                return get_error_fallback_metadata(file_path, filename)

        except Exception as e:
            logger.error(f"Document analysis failed for {filename}: {e}")
            return get_error_fallback_metadata(file_path, filename)

    async def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama API for text generation."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": "llama3.2",
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temperature for consistent JSON output
                            "top_p": 0.9
                        }
                    },
                    timeout=60.0
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return ""

        except Exception as e:
            logger.error(f"Failed to call Ollama API: {e}")
            return ""

    async def store_document_metadata(self, doc_data: Dict[str, Any], ai_metadata: Dict[str, Any]) -> Optional[int]:
        """
        Store document with metadata in database using MCP.

        Args:
            doc_data: Basic document information
            ai_metadata: AI-generated metadata

        Returns:
            Document ID if successful, None otherwise
        """
        if not self.session:
            logger.error("MCP session not connected")
            return None

        try:
            # Generate UUID for the document
            import uuid
            doc_uuid = str(uuid.uuid4())

            # Prepare insert query with parametrized placeholders
            insert_query = """
                INSERT INTO documents
                (uuid, file_path, filename, extension, size, mime_type, md5_hash,
                 original_text, markdown_content, summary, document_type, categories, entities,
                 persons, places, mentioned_dates, file_references, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Prepare parameters - clean and safe
            params = [
                doc_uuid,
                doc_data.get('file_path', ''),
                doc_data.get('filename', ''),
                doc_data.get('extension', ''),
                doc_data.get('size', 0),
                doc_data.get('mime_type', ''),
                doc_data.get('md5_hash', ''),
                doc_data.get('original_text', '')[:150000],  # Increased limit for complete content
                doc_data.get('markdown_content', doc_data.get('original_text', ''))[:150000],
                ai_metadata.get('summary', ''),
                ai_metadata.get('document_type', 'Dokument'),
                json.dumps(ai_metadata.get('categories', [])),
                json.dumps(ai_metadata.get('entities', [])),
                json.dumps(ai_metadata.get('persons', [])),
                json.dumps(ai_metadata.get('places', [])),
                json.dumps(ai_metadata.get('mentioned_dates', [])),
                json.dumps(ai_metadata.get('file_references', [])),
                doc_data.get('created_at', ''),
                doc_data.get('updated_at', '')
            ]

            # Execute insert - MCP SQLite server expects just the query with embedded values.
            # We format the query safely on the client-side as a workaround.
            formatted_query = self._format_query_safely(insert_query, params)
            logger.debug(f"Executing formatted query: {formatted_query}")
            await self.session.call_tool("write_query", {"query": formatted_query})

            # Get the document ID by UUID (more reliable than last_insert_rowid with INSERT OR REPLACE)
            id_query = f"SELECT id FROM documents WHERE uuid = '{doc_uuid}'"
            id_result = await self.session.call_tool("read_query", {"query": id_query})
            
            # Parse the MCP result properly
            parsed_result = self._parse_mcp_result(id_result)
            
            if parsed_result and len(parsed_result) > 0:
                try:
                    doc_id = parsed_result[0].get('id')
                    if doc_id:
                        # Update FTS table
                        await self._update_fts_table(doc_id, doc_data, ai_metadata)

                        logger.info(f"Document stored with ID {doc_id}: {doc_data.get('filename')}")
                        return doc_id
                except (KeyError, AttributeError) as e:
                    logger.warning(f"Could not parse document ID from response: {e}")

            logger.warning(f"Could not retrieve document ID for {doc_data.get('filename')}")
            return None

        except Exception as e:
            logger.error(f"Failed to store document metadata: {e}")
            return None

    async def _update_fts_table(self, doc_id: int, doc_data: Dict[str, Any], ai_metadata: Dict[str, Any]):
        """Update the FTS table with document content for search."""
        try:
            fts_query = """
                INSERT OR REPLACE INTO documents_fts
                (rowid, original_text, markdown_content, summary, document_type,
                 categories, entities, persons, places, mentioned_dates, file_references)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            fts_params = [
                doc_id,
                doc_data.get('original_text', '')[:150000],  # Increased limit for FTS
                doc_data.get('markdown_content', doc_data.get('original_text', ''))[:150000],
                ai_metadata.get('summary', ''),
                ai_metadata.get('document_type', 'Dokument'),
                json.dumps(ai_metadata.get('categories', [])),
                json.dumps(ai_metadata.get('entities', [])),
                json.dumps(ai_metadata.get('persons', [])),
                json.dumps(ai_metadata.get('places', [])),
                json.dumps(ai_metadata.get('mentioned_dates', [])),
                json.dumps(ai_metadata.get('file_references', []))
            ]

            # Format the FTS query safely on the client-side.
            formatted_fts_query = self._format_query_safely(fts_query, fts_params)
            try:
                await self.session.call_tool("write_query", {"query": formatted_fts_query})
                logger.debug(f"FTS table updated for document {doc_id}")
            except Exception as e:
                logger.error(f"Database error during FTS update for doc {doc_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to update FTS table: {e}")

    def _format_query_safely(self, query: str, params: list) -> str:
        """
        Formats an SQL query with parameters, escaping them safely.
        This is a client-side workaround because the MCP server does not
        currently support parameterized queries.
        """
        import re
        
        def escape_sql_string(value):
            # This is a basic implementation. For a production system,
            # a more robust solution would be required.
            if value is None:
                return "NULL"
            elif isinstance(value, (int, float)):
                return str(value)
            else:
                return "'" + str(value).replace("'", "''") + "'"

        parts = query.split('?')
        if len(parts) != len(params) + 1:
            raise ValueError("Query and parameter count mismatch")

        result = [parts[0]]
        for i, param in enumerate(params):
            result.append(escape_sql_string(param))
            result.append(parts[i+1])
        
        return "".join(result)

    def _parse_mcp_result(self, result):
        """Parse MCP result content, similar to mcp_client.py logic."""
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

    def _extract_json_from_response(self, response: str, filename: str) -> dict:
        """
        Extract JSON from LLM response using multiple strategies.
        
        Args:
            response: Raw LLM response
            filename: Filename for logging
            
        Returns:
            Parsed JSON dict or None if extraction fails
        """
        import re
        
        strategies = [
            # Strategy 1: Look for ```json blocks
            (r'```json\s*(\{.*?\})\s*```', "JSON code block"),
            # Strategy 2: Look for { } blocks (greedy)
            (r'(\{.*\})', "Curly brace block"),
            # Strategy 3: Look for { } blocks (non-greedy)
            (r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', "Nested JSON structure"),
            # Strategy 4: Look for JSON starting with specific keys
            (r'(\{\s*"summary".*?\})', "Summary-based JSON"),
        ]
        
        for pattern, strategy_name in strategies:
            try:
                match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
                if match:
                    json_str = match.group(1).strip()
                    
                    # Clean up common issues
                    json_str = self._clean_json_string(json_str)
                    
                    # Try to parse
                    metadata = json.loads(json_str)
                    logger.info(f"Successfully extracted JSON using {strategy_name} for {filename}")
                    return metadata
                    
            except (json.JSONDecodeError, AttributeError) as e:
                logger.debug(f"Strategy '{strategy_name}' failed for {filename}: {e}")
                continue
        
        # Last resort: try to build JSON from key-value pairs
        try:
            return self._build_json_from_text(response, filename)
        except Exception as e:
            logger.debug(f"Text parsing fallback failed for {filename}: {e}")
            return None

    def _clean_json_string(self, json_str: str) -> str:
        """Clean common JSON formatting issues."""
        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix unescaped quotes in strings (basic attempt)
        # This is a simple fix - more complex cases might still fail
        json_str = re.sub(r'(?<!\\)"(?=.*".*:)', '\\"', json_str)
        
        # Remove any text before first { and after last }
        start = json_str.find('{')
        end = json_str.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = json_str[start:end+1]
        
        return json_str

    def _build_json_from_text(self, response: str, filename: str) -> dict:
        """
        Last resort: try to extract key-value pairs from text.
        This is a very basic implementation.
        """
        import re
        
        # Look for key-value patterns
        patterns = {
            'summary': r'"summary":\s*"([^"]*)"',
            'document_type': r'"document_type":\s*"([^"]*)"',
            'categories': r'"categories":\s*\[([^\]]*)\]',
            'entities': r'"entities":\s*\[([^\]]*)\]',
            'persons': r'"persons":\s*\[([^\]]*)\]',
            'places': r'"places":\s*\[([^\]]*)\]',
            'mentioned_dates': r'"mentioned_dates":\s*\[([^\]]*)\]',
            'file_references': r'"file_references":\s*\[([^\]]*)\]',
        }
        
        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key in ['categories', 'entities', 'persons', 'places', 'mentioned_dates', 'file_references']:
                    # Parse array
                    if value:
                        items = [item.strip().strip('"') for item in value.split(',')]
                        result[key] = [item for item in items if item]
                    else:
                        result[key] = []
                else:
                    result[key] = value
        
        # Add defaults for missing keys
        fallback = get_error_fallback_metadata("", filename)
        for key, default_value in fallback.items():
            if key not in result:
                result[key] = default_value
        
        if result:
            logger.info(f"Built JSON from text patterns for {filename}")
            return result
        
        return None

    async def _initialize_database_schema(self):
        """Initialize database schema if it doesn't exist."""
        try:
            # Create documents table
            documents_table_query = """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    uuid TEXT UNIQUE NOT NULL,
                    file_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    extension TEXT,
                    size INTEGER,
                    mime_type TEXT,
                    md5_hash TEXT NOT NULL,
                    original_text TEXT,
                    markdown_content TEXT,
                    summary TEXT,
                    document_type TEXT,
                    categories TEXT,
                    entities TEXT,
                    persons TEXT,
                    places TEXT,
                    mentioned_dates TEXT,
                    file_references TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """

            await self.session.call_tool("write_query", {"query": documents_table_query})

            # Create FTS table
            fts_table_query = """
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    original_text, markdown_content, summary, document_type,
                    categories, entities, persons, places, mentioned_dates,
                    file_references, tokenize='unicode61'
                )
            """

            await self.session.call_tool("write_query", {"query": fts_table_query})

            logger.debug("Database schema initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    async def cleanup(self):
        """Clean up MCP connection resources."""
        try:
            await self.exit_stack.aclose()
            logger.debug("MCP client cleaned up")
        except Exception as e:
            logger.error(f"Error during MCP cleanup: {e}")