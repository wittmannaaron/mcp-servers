#!/usr/bin/env python3
"""
Test script to validate the JSON parsing fixes.
Tests the simplified JSON extraction with various response formats.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.ingestion_mcp_client import IngestionMCPClient
from src.core.llm_prompts import get_error_fallback_metadata

def test_json_extraction():
    """Test the simplified JSON extraction method."""
    client = IngestionMCPClient()
    
    # Test cases with different JSON response formats
    test_cases = [
        # Case 1: Complete valid JSON
        {
            "name": "Complete JSON",
            "response": '''
            {
                "summary": "Test document summary",
                "document_type": "Rechtsstreit",
                "categories": ["Technik"],
                "entities": [],
                "persons": ["Max Mustermann"],
                "places": ["Berlin"],
                "mentioned_dates": ["2024-01-15"],
                "file_references": ["test.pdf"],
                "language": "de",
                "sentiment": "neutral",
                "complexity": "medium",
                "word_count_estimate": 150
            }
            ''',
            "should_succeed": True
        },
        
        # Case 2: JSON with extra text (like the error case)
        {
            "name": "JSON with trailing text",
            "response": '''
            {
                "summary": "Test document summary",
                "document_type": "Rechtsstreit",
                "categories": ["Technik"],
                "entities": [],
                "persons": ["Max Mustermann"],
                "places": ["Berlin"],
                "mentioned_dates": ["2024-01-15"],
                "file_references": ["test.pdf"],
                "language": "de",
                "sentiment": "neutral",
                "complexity": "medium",
                "word_count_estimate": 150
            }
            
            Some additional text that should be ignored.
            ''',
            "should_succeed": True
        },
        
        # Case 3: Truncated JSON (like the original error)
        {
            "name": "Truncated JSON",
            "response": '''
            {
                "summary": "Test document summary",
                "document_type": "Rechtsstreit",
                "categories": ["Technik"],
                "entities": [],
                "persons": ["Max Mustermann"],
                "places": ["Berlin"],
                "mentioned_dates": ["2024-01-15"],
                "file_references": ["test.pdf"],
                "language": "de",
                "sentiment": "neutral",
                "complexity": "medium",
                "word_count_estimate": 150...
            ''',
            "should_succeed": False  # This should fail and use fallback
        },
        
        # Case 4: JSON with trailing comma
        {
            "name": "JSON with trailing comma",
            "response": '''
            {
                "summary": "Test document summary",
                "document_type": "Rechtsstreit",
                "categories": ["Technik"],
                "entities": [],
                "persons": ["Max Mustermann"],
                "places": ["Berlin"],
                "mentioned_dates": ["2024-01-15"],
                "file_references": ["test.pdf"],
                "language": "de",
                "sentiment": "neutral",
                "complexity": "medium",
                "word_count_estimate": 150,
            }
            ''',
            "should_succeed": True  # Should be cleaned up
        }
    ]
    
    print("Testing JSON extraction methods...")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 30)
        
        try:
            result = client._extract_json_simple(test_case['response'], f"test_{i}.pdf")
            
            if result is not None:
                print("✅ JSON extraction successful")
                print(f"   Summary: {result.get('summary', 'N/A')}")
                print(f"   Document type: {result.get('document_type', 'N/A')}")
                print(f"   Categories: {result.get('categories', [])}")
                
                if test_case['should_succeed']:
                    print("✅ Expected success - PASSED")
                else:
                    print("❌ Expected failure but succeeded - UNEXPECTED")
            else:
                print("❌ JSON extraction failed")
                if test_case['should_succeed']:
                    print("❌ Expected success but failed - FAILED")
                else:
                    print("✅ Expected failure - PASSED")
                    
        except Exception as e:
            print(f"❌ Exception during extraction: {e}")
            if test_case['should_succeed']:
                print("❌ Expected success but got exception - FAILED")
            else:
                print("✅ Expected failure - PASSED")
    
    print("\n" + "=" * 50)
    print("JSON extraction tests completed!")

def test_fallback_metadata():
    """Test the fallback metadata generation."""
    print("\nTesting fallback metadata...")
    print("-" * 30)
    
    fallback = get_error_fallback_metadata("/test/path/document.pdf", "document.pdf")
    
    required_fields = [
        'summary', 'document_type', 'categories', 'entities', 'persons',
        'places', 'mentioned_dates', 'file_references', 'language',
        'sentiment', 'complexity', 'word_count_estimate'
    ]
    
    all_present = True
    for field in required_fields:
        if field not in fallback:
            print(f"❌ Missing field: {field}")
            all_present = False
        else:
            print(f"✅ Field present: {field} = {fallback[field]}")
    
    if all_present:
        print("✅ All required fields present in fallback metadata")
    else:
        print("❌ Some required fields missing in fallback metadata")

if __name__ == "__main__":
    print("JSON Parsing Fix Validation Test")
    print("=" * 50)
    
    test_json_extraction()
    test_fallback_metadata()
    
    print("\nTest completed!")