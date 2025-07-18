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
                    "/Users/aaron/Projects/mcp-servers/file-search-server-v3/src/sqlite",
                    "run",
                    "mcp-server-sqlite",
                    "--db-path",
                    "/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db"
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
        Simplified and robust JSON parsing.

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
            
            if not llm_response or not llm_response.strip():
                logger.warning(f"Empty LLM response for {filename}")
                return get_error_fallback_metadata(file_path, filename)

            # Simple and robust JSON extraction
            metadata = self._extract_json_simple(llm_response, filename)
            if metadata:
                logger.debug(f"Successfully analyzed document: {filename}")
                return metadata
            else:
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

    def _extract_json_simple(self, response: str, filename: str) -> dict:
        """
        Simplified JSON extraction with robust error handling.
        
        Args:
            response: Raw LLM response
            filename: Filename for logging
            
        Returns:
            Parsed JSON dict or None if extraction fails
        """
        import re
        
        logger.debug(f"Extracting JSON from response for {filename} (length: {len(response)})")
        
        # Step 1: Find JSON boundaries
        start_pos = response.find('{')
        if start_pos == -1:
            logger.warning(f"No opening brace found in response for {filename}")
            return None
            
        # Step 2: Find matching closing brace by counting braces
        brace_count = 0
        end_pos = -1
        
        for i in range(start_pos, len(response)):
            if response[i] == '{':
                brace_count += 1
            elif response[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break
        
        if end_pos == -1:
            logger.warning(f"No matching closing brace found for {filename}")
            return None
            
        # Step 3: Extract JSON string
        json_str = response[start_pos:end_pos + 1]
        logger.debug(f"Extracted JSON string for {filename}: {json_str[:200]}...")
        
        # Step 4: Clean and parse
        try:
            json_str = self._clean_json_simple(json_str)
            metadata = json.loads(json_str)
            
            # Validate required fields
            if self._validate_metadata(metadata):
                logger.info(f"Successfully extracted and validated JSON for {filename}")
                return metadata
            else:
                logger.warning(f"JSON validation failed for {filename}")
                return None
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed for {filename}: {e}")
            logger.debug(f"Failed JSON string: {json_str}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during JSON extraction for {filename}: {e}")
            return None

    def _clean_json_simple(self, json_str: str) -> str:
        """Simple JSON cleaning with minimal processing."""
        import re
        
        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Remove any trailing text after the last }
        last_brace = json_str.rfind('}')
        if last_brace != -1:
            json_str = json_str[:last_brace + 1]
        
        return json_str.strip()
    
    def _validate_metadata(self, metadata: dict) -> bool:
        """Validate that metadata contains required fields with correct types."""
        required_fields = {
            'summary': str,
            'document_type': str,
            'categories': list,
            'entities': list,
            'persons': list,
            'places': list,
            'mentioned_dates': list,
            'file_references': list,
            'language': str,
            'sentiment': str,
            'complexity': str,
            'word_count_estimate': (int, float)
        }
        
        for field, expected_type in required_fields.items():
            if field not in metadata:
                logger.debug(f"Missing required field: {field}")
                return False
            
            if not isinstance(metadata[field], expected_type):
                logger.debug(f"Field {field} has wrong type: {type(metadata[field])} (expected {expected_type})")
                return False
        
        return True


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