"""
Simplified Search Service for FileBrowser.

This module provides a simplified search service that executes structured queries
provided by the SearchOrchestrator. It no longer handles natural language processing
directly, focusing only on executing database queries through the DocumentStore.

Architectural Compliance:
- File size ≤ 200 lines enforced
- No direct database/LLM calls allowed
- Uses DocumentStore for all database operations
- Pure async implementation with proper context management
"""

from typing import List, Dict, Any
from loguru import logger
from src.core.document_store import DocumentStore


class SearchService:
    """
    Simplified search service that executes structured queries.

    This service works with the SearchOrchestrator architecture where natural language
    processing is handled by the orchestrator, and this service focuses solely on
    executing structured database queries through the DocumentStore.
    """

    def __init__(self, document_store: DocumentStore):
        """
        Initialize search service with a DocumentStore instance.

        Args:
            document_store: Instance of DocumentStore for database operations
        """
        self.document_store = document_store

    async def search(self, structured_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a structured search query against the document store.

        Args:
            structured_query: Dictionary containing structured query parameters
                Expected keys:
                - 'query': Search terms to use
                - 'limit': Maximum number of results (optional, defaults to 10)
                - 'filters': Additional filters to apply (optional)

        Returns:
            List of document dictionaries matching the search criteria
        """
        try:
            # Extract query parameters from structured query
            search_terms = structured_query.get('query', '')
            limit = structured_query.get('limit', 10)
            filters = structured_query.get('filters', {})

            if not search_terms:
                logger.warning("Empty search terms in structured query")
                return []

            # Execute search through DocumentStore
            results = await self.document_store._search_async(search_terms, limit)

            # Apply additional filters if specified
            if filters:
                results = self._apply_filters(results, filters)

            logger.debug(f"Search executed: terms='{search_terms}', results={len(results)}")
            return results

        except Exception as e:
            logger.error(f"Structured search failed: {e}")
            return []

    def _apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply additional filters to search results.

        Args:
            results: List of search results to filter
            filters: Dictionary of filters to apply

        Returns:
            Filtered list of results
        """
        filtered_results = results

        try:
            # Apply file type filters
            file_types = filters.get('file_types', [])
            if file_types:
                filtered_results = [
                    result for result in filtered_results
                    if any(result.get('file_path', '').lower().endswith(f'.{ft.lower()}') for ft in file_types)
                ]

            # Apply content type filters
            content_type = filters.get('content_type', 'any')
            if content_type != 'any':
                # Simple content type filtering based on mime_type or file extension
                if content_type == 'document':
                    doc_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md']
                    filtered_results = [
                        result for result in filtered_results
                        if any(result.get('file_path', '').lower().endswith(ext) for ext in doc_extensions)
                    ]
                elif content_type == 'code':
                    code_extensions = ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c']
                    filtered_results = [
                        result for result in filtered_results
                        if any(result.get('file_path', '').lower().endswith(ext) for ext in code_extensions)
                    ]

            logger.debug(f"Filters applied: {len(results)} -> {len(filtered_results)} results")
            return filtered_results

        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")
            return results