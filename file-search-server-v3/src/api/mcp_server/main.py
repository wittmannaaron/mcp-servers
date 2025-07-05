"""
MCP-Compliant API Service for FileBrowser.

Architectural Compliance:
- File size ≤ 200 lines enforced
- No direct LLM calls allowed
- Uses MCP-compliant services exclusively
"""

from fastapi import FastAPI, HTTPException
from typing import Dict, Any
from loguru import logger

from src.core.mcp_llm_service import get_mcp_llm_service

app = FastAPI(
    title="FileBrowser MCP API",
    description="MCP-compliant API service for FileBrowser metadata generation",
    version="1.0.0"
)


@app.post("/generate")
async def generate_metadata(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates metadata (summary, categories, entities) for a given text using MCP-compliant LLM service.

    Args:
        request: Dictionary containing 'text' field with content to analyze

    Returns:
        Dictionary with 'summary', 'categories', and 'entities' fields

    Raises:
        HTTPException: If text is missing or AI processing fails
    """
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        # Get MCP-compliant LLM service
        llm_service = get_mcp_llm_service()

        # Generate metadata using MCP-compliant service
        metadata = await llm_service.generate_metadata(text)

        logger.info(f"Generated metadata for text of length {len(text)}")

        return {
            "summary": metadata.get("summary", ""),
            "categories": metadata.get("categories", ""),
            "entities": metadata.get("entities", [])
        }

    except Exception as e:
        logger.error(f"Failed to generate metadata: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during AI processing: {str(e)}"
        )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for service monitoring."""
    return {"status": "healthy", "service": "FileBrowser MCP API"}


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with service information."""
    return {
        "service": "FileBrowser MCP API",
        "version": "1.0.0",
        "description": "MCP-compliant API service for metadata generation",
        "endpoints": "POST /generate, GET /health, GET /"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)