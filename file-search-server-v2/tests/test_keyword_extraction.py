#!/usr/bin/env python3
"""
Test script to iterate on LLM keyword extraction from German sentences
"""
import requests
import json

def test_ollama_keyword_extraction():
    ollama_url = "http://localhost:11434"
    model_name = "llama3.2:latest"
    
    # Test sentences
    test_sentences = [
        "Bitte liste alle Dateien auf, die das Wort Ihring beinhalten.",
        "Finde Dateien über BMW.",
        "Suche nach Dokumenten mit Anke oder Familie.",
        "Zeige mir alle Dokumente von 2024.",
        "Welche Dateien enthalten Baltmannsweiler?",
        "Ich brauche alle PDF-Dateien mit Esslingen."
    ]
    
    # Different system prompts to test
    system_prompts = [
        # Prompt 1: Simple extraction
        """Du bist ein Keyword-Extraktor. Extrahiere aus deutschen Sätzen nur die wichtigen Suchbegriffe (Namen, Orte, Begriffe). 
Antworte nur mit den extrahierten Begriffen, getrennt durch Kommas. Keine weiteren Erklärungen.""",
        
        # Prompt 2: JSON format
        """Du bist ein Keyword-Extraktor. Analysiere deutsche Sätze und extrahiere wichtige Suchbegriffe (Namen, Orte, spezifische Begriffe).
Antworte nur im JSON-Format: {"keywords": ["begriff1", "begriff2"]}""",
        
        # Prompt 3: Explicit instructions
        """Aufgabe: Extrahiere aus deutschen Suchanfragen die relevanten Suchbegriffe.
Regeln:
- Extrahiere Namen von Personen (z.B. Ihring, Anke)
- Extrahiere Ortsnamen (z.B. Baltmannsweiler, Esslingen) 
- Extrahiere wichtige Begriffe (z.B. BMW, Familie)
- Ignoriere Füllwörter (Bitte, liste, alle, Dateien, etc.)
- Antworte nur mit den Begriffen, getrennt durch Kommas""",
        
        # Prompt 4: Examples
        """Du extrahierst Suchbegriffe aus deutschen Sätzen.

Beispiele:
Input: "Bitte liste alle Dateien auf, die das Wort Ihring beinhalten"
Output: Ihring

Input: "Finde Dateien über BMW und Mercedes"  
Output: BMW, Mercedes

Input: "Suche Dokumente mit Anke aus Esslingen"
Output: Anke, Esslingen

Extrahiere nur die wichtigen Suchbegriffe, keine Füllwörter."""
    ]
    
    print("=" * 80)
    print("🔍 Testing LLM Keyword Extraction")
    print("=" * 80)
    
    for i, system_prompt in enumerate(system_prompts, 1):
        print(f"\n📝 PROMPT {i}:")
        print("-" * 40)
        print(system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt)
        print("-" * 40)
        
        for sentence in test_sentences:
            try:
                full_prompt = f"{system_prompt}\n\nInput: {sentence}\nOutput:"
                
                ollama_request = {
                    "model": model_name,
                    "prompt": full_prompt,
                    "stream": False
                }
                
                response = requests.post(
                    f"{ollama_url}/api/generate",
                    json=ollama_request,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    extracted = result.get("response", "").strip()
                    
                    print(f"Input:  {sentence}")
                    print(f"Output: {extracted}")
                    print()
                else:
                    print(f"Error: {response.status_code}")
                    
            except Exception as e:
                print(f"Error with sentence '{sentence}': {e}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    test_ollama_keyword_extraction()