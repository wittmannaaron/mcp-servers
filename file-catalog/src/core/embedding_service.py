"""
Embedding Service to generate vector embeddings for text chunks.
"""
import asyncio
from typing import List
from loguru import logger
from langchain_ollama import OllamaEmbeddings

# Configuration for the embedding model
# As per the requirements, we are using the local bge-m3 model via Ollama.
EMBEDDING_MODEL = "bge-m3"

def get_embedding_client() -> OllamaEmbeddings:
    """Initializes and returns the Ollama embedding client."""
    return OllamaEmbeddings(model=EMBEDDING_MODEL)

def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates vector embeddings for a list of text chunks using a batch process.

    Args:
        texts: A list of text chunks to be embedded.

    Returns:
        A list of vector embeddings.
    """
    if not texts:
        return []
    
    try:
        logger.debug(f"Generating embeddings for {len(texts)} chunks...")
        embedding_client = get_embedding_client()
        # The embed_documents method handles batching internally.
        vectors = embedding_client.embed_documents(texts)
        logger.debug("Embeddings generated successfully.")
        return vectors
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        # Depending on desired robustness, you might want to return empty lists
        # or re-raise the exception. For now, re-raising to make issues visible.
        raise

async def main():
    """Example usage for the embedding service."""
    sample_texts = [
        "This is the first sentence for testing.",
        "Here is another piece of text to embed.",
        "Context-aware chunking helps in semantic search.",
        "Large language models are powerful."
    ]

    logger.info("--- Testing Embedding Service ---")
    
    # Generate embeddings
    vectors = create_embeddings(sample_texts)

    if vectors:
        logger.info(f"Successfully generated {len(vectors)} vectors.")
        for i, vector in enumerate(vectors):
            # Print the first 5 dimensions of each vector for verification
            logger.info(f"Vector {i+1} (first 5 dims): {vector[:5]}")
            logger.info(f"Vector dimension: {len(vector)}")
    else:
        logger.error("Failed to generate any vectors.")

if __name__ == '__main__':
    # Setup basic logging for standalone execution
    import sys
    logger.add(sys.stdout, level="DEBUG")
    asyncio.run(main())