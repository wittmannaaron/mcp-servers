"""
Ollama LLM Service for file-catalog.
Handles document analysis using local Ollama models.
"""

import json
import httpx
from typing import Dict, Any
from loguru import logger

from src.core.simple_config import settings
from src.core.llm_prompts import (
    get_document_analysis_prompt, 
    get_ollama_system_prompt,
    get_error_fallback_metadata
)


class OllamaLLMService:
    """Service for interacting with local Ollama models."""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.llm_request_timeout
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
    
    async def analyze_document(self, file_path: str, filename: str, extension: str, text_content: str) -> Dict[str, Any]:
        """
        Analyze document content using Ollama LLM.
        
        Args:
            file_path: Full path to the document
            filename: Name of the file
            extension: File extension
            text_content: Extracted text content
            
        Returns:
            Dict containing AI-generated metadata
        """
        try:
            logger.debug(f"Starting LLM analysis for {filename}")
            
            # Generate the analysis prompt
            user_prompt = get_document_analysis_prompt(file_path, filename, extension, text_content)
            system_prompt = get_ollama_system_prompt()
            
            # Make request to Ollama
            response = await self._make_ollama_request(system_prompt, user_prompt)
            
            if response:
                # Parse and validate the JSON response
                metadata = self._parse_and_validate_response(response, filename)
                logger.debug(f"Successfully analyzed {filename} with LLM")
                return metadata
            else:
                logger.warning(f"Empty response from LLM for {filename}")
                return get_error_fallback_metadata(file_path, filename)
                
        except Exception as e:
            logger.error(f"LLM analysis failed for {filename}: {e}")
            return get_error_fallback_metadata(file_path, filename)
    
    async def _make_ollama_request(self, system_prompt: str, user_prompt: str) -> str:
        """Make HTTP request to Ollama API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                }
                
                logger.debug(f"Making Ollama request to {self.base_url}/api/chat")
                
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message_content = result.get("message", {}).get("content", "")
                    return message_content.strip()
                else:
                    logger.error(f"Ollama request failed with status {response.status_code}: {response.text}")
                    return ""
                    
        except httpx.TimeoutException:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            return ""
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return ""
    
    def _parse_and_validate_response(self, response: str, filename: str) -> Dict[str, Any]:
        """Parse and validate LLM JSON response."""
        try:
            # Clean response - remove any markdown formatting
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Parse JSON
            metadata = json.loads(cleaned_response)
            
            # Validate required fields
            required_fields = [
                'summary', 'document_type', 'categories', 'entities',
                'persons', 'places', 'mentioned_dates', 'file_references',
                'language', 'sentiment', 'complexity', 'word_count_estimate'
            ]
            
            for field in required_fields:
                if field not in metadata:
                    logger.warning(f"Missing field '{field}' in LLM response for {filename}")
                    metadata[field] = self._get_default_value(field)
            
            # Ensure lists are actually lists
            list_fields = ['categories', 'entities', 'persons', 'places', 'mentioned_dates', 'file_references']
            for field in list_fields:
                if not isinstance(metadata[field], list):
                    metadata[field] = []
            
            # Validate and truncate summary length
            if len(metadata.get('summary', '')) > 300:
                metadata['summary'] = metadata['summary'][:297] + "..."
            
            logger.debug(f"Successfully parsed and validated LLM response for {filename}")
            return metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response for {filename}: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
            return get_error_fallback_metadata("", filename)
        except Exception as e:
            logger.error(f"Failed to validate LLM response for {filename}: {e}")
            return get_error_fallback_metadata("", filename)
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields."""
        defaults = {
            'summary': 'Dokumenteninhalt konnte nicht analysiert werden',
            'document_type': 'Dokument',
            'categories': [],
            'entities': [],
            'persons': [],
            'places': [],
            'mentioned_dates': [],
            'file_references': [],
            'language': 'unbekannt',
            'sentiment': 'neutral',
            'complexity': 'medium',
            'word_count_estimate': 0
        }
        return defaults.get(field, "")
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available and model is loaded."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return False
                
                # Check if our model is available
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                if self.model in model_names:
                    logger.info(f"Ollama model {self.model} is available")
                    return True
                else:
                    logger.warning(f"Ollama model {self.model} not found. Available models: {model_names}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False


# Global service instance
_ollama_service = None

def get_ollama_service() -> OllamaLLMService:
    """Get global Ollama service instance."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaLLMService()
    return _ollama_service


async def main():
    """Test the Ollama LLM service."""
    service = get_ollama_service()
    
    # Health check
    if await service.health_check():
        logger.info("Ollama service is healthy")
        
        # Test document analysis
        test_text = """
        Dies ist ein Testdokument für die LLM-Analyse.
        Es enthält Informationen über Max Mustermann aus Berlin.
        Das Dokument wurde am 15.12.2024 erstellt.
        """
        
        result = await service.analyze_document(
            "/test/path/document.txt",
            "document.txt", 
            ".txt",
            test_text
        )
        
        logger.info("Test analysis result:")
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        logger.error("Ollama service is not available")


if __name__ == "__main__":
    import asyncio
    import sys
    
    # Setup logging for testing
    logger.add(sys.stdout, level="DEBUG")
    asyncio.run(main())