#!/usr/bin/env python3
"""
Test refined keyword extraction prompts based on Prompt 4 results
"""
import requests
import json

def test_refined_prompts():
    ollama_url = "http://localhost:11434"
    model_name = "catalog-browser"
    
    # Our critical test sentences
    test_sentences = [
        "Bitte liste alle Dateien auf, die das Wort Ihring beinhalten.",
        "Finde Dateien über BMW.",
        "Suche nach Dokumenten mit Anke oder Familie.", 
        "Welche Dateien enthalten Baltmannsweiler?",
        "Ich brauche alle PDF-Dateien mit Esslingen."
    ]
    
    # Refined prompts based on Prompt 4 success
    refined_prompts = [
        # Refined 1: More concise examples
        """Extrahiere nur die wichtigsten Suchbegriffe:

Beispiel:
"Bitte liste alle Dateien auf, die das Wort Ihring beinhalten" → Ihring
"Finde Dateien über BMW" → BMW  
"Suche nach Dokumenten mit Anke oder Familie" → Anke, Familie

Antworte nur mit den Begriffen, keine weiteren Worte.""",

        # Refined 2: Even more direct
        """Extrahiere Suchbegriffe aus deutschen Sätzen.

"Bitte liste alle Dateien auf, die das Wort Ihring beinhalten" → Ihring
"Finde Dateien über BMW" → BMW
"Suche nach Dokumenten mit Anke oder Familie" → Anke, Familie  
"Welche Dateien enthalten Baltmannsweiler?" → Baltmannsweiler

Antworte nur mit den Begriffen:""",

        # Refined 3: Emphasize pattern
        """Du bist ein Keyword-Extraktor. Folge dem Muster:

Input: "Bitte liste alle Dateien auf, die das Wort Ihring beinhalten"
Output: Ihring

Input: "Finde Dateien über BMW"  
Output: BMW

Input: "Suche nach Dokumenten mit Anke oder Familie"
Output: Anke, Familie

Extrahiere nur Namen, Orte und wichtige Begriffe. Antworte nur mit den Begriffen."""
    ]
    
    print("🔍 Testing Refined Keyword Extraction Prompts")
    print("=" * 60)
    
    for i, prompt in enumerate(refined_prompts, 1):
        print(f"\n📝 REFINED PROMPT {i}:")
        print("-" * 40)
        
        success_count = 0
        total_tests = len(test_sentences)
        
        for sentence in test_sentences:
            try:
                full_prompt = f"{prompt}\n\nInput: {sentence}\nOutput:"
                
                ollama_request = {
                    "model": model_name,
                    "prompt": full_prompt,
                    "stream": False
                }
                
                response = requests.post(
                    f"{ollama_url}/api/generate",
                    json=ollama_request,
                    timeout=15
                )
                
                if response.status_code == 200:
                    result = response.json()
                    extracted = result.get("response", "").strip()
                    
                    # Check if extraction looks good (short, no sentences)
                    is_good = len(extracted) < 50 and not extracted.startswith("Ich")
                    if is_good:
                        success_count += 1
                        
                    status = "✅" if is_good else "❌"
                    print(f"{status} {sentence[:50]}... → {extracted}")
                else:
                    print(f"❌ HTTP Error: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Exception: {e}")
        
        success_rate = (success_count / total_tests) * 100
        print(f"\n📊 Success Rate: {success_count}/{total_tests} ({success_rate:.1f}%)")
        print("=" * 60)

if __name__ == "__main__":
    test_refined_prompts()