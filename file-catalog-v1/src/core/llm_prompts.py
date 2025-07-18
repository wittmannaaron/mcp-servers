"""
LLM Prompts for file-catalog Document Analysis.
Contains prompts for AI-powered metadata generation and document analysis.
"""

def get_document_analysis_prompt(file_path: str, filename: str, extension: str, original_text: str) -> str:
    """
    Generate a prompt for LLM to analyze document content and extract structured metadata.

    Args:
        file_path: Full path to the document
        filename: Name of the file
        extension: File extension
        original_text: Extracted text content from the document

    Returns:
        Formatted prompt string for LLM analysis
    """

    prompt = f"""Du bist ein Dokumentenanalyst. Analysiere den folgenden Dokumenteninhalt und extrahiere strukturierte Metadaten.

DOKUMENT INFORMATIONEN:
- Dateiname: {filename}
- Dateipfad: {file_path}
- Dateierweiterung: {extension}

DOKUMENTENINHALT:
{original_text[:50000]}

AUFGABE:
Erstelle strukturierte Metadaten. Antworte EXAKT mit diesem JSON-Format (VOLLSTÄNDIG und OHNE Abkürzungen):

{{
    "summary": "Kurze Zusammenfassung des Inhalts",
    "document_type": "Rechtsstreit",
    "categories": ["Kategorie1"],
    "entities": [],
    "persons": [],
    "places": [],
    "mentioned_dates": [],
    "file_references": [],
    "language": "de",
    "sentiment": "neutral",
    "complexity": "medium",
    "word_count_estimate": 100
}}

REGELN:
- summary: Maximal 300 Zeichen
- document_type: Wähle: email, Rechtsstreit, Familie, Finanzamt, Gericht, Bewerbung, Finanzen, Vertrag, Entwurf, Bericht, Bilanzen, Hauseigentum
- categories: 1-3 Kategorien (Business, Technik, Verwaltung, Finanz, etc.)
- entities: Firmen, Organisationen (KEINE Personen)
- persons: Vollständige Namen von Personen
- places: Orte, Adressen, Städte
- mentioned_dates: Daten im Format YYYY-MM-DD oder DD.MM.YYYY
- file_references: Erwähnte Dateinamen
- language: de, en, fr, it
- sentiment: neutral, positive, negative
- complexity: low, medium, high
- word_count_estimate: Zahl (geschätzte Wortanzahl)

KRITISCH WICHTIG:
- Antworte NUR mit dem vollständigen JSON-Objekt
- KEINE zusätzlichen Texte oder Erklärungen
- Das JSON MUSS vollständig und gültig sein
- ALLE Felder müssen vorhanden sein
- Verwende leere Arrays [] wenn keine Werte vorhanden
"""

    return prompt

def get_ollama_system_prompt() -> str:
    """
    System prompt for Ollama to ensure consistent JSON responses.
    """
    return """Du bist ein JSON-Generator für Dokumentenanalyse.
WICHTIG: Antworte AUSSCHLIESSLICH mit vollständigem, gültigem JSON.
KEINE zusätzlichen Texte, Erklärungen oder Formatierungen.
Das JSON muss vollständig sein und alle erforderlichen Felder enthalten."""

def get_error_fallback_metadata(file_path: str, filename: str) -> dict:
    """
    Fallback metadata when LLM analysis fails.

    Args:
        file_path: Full path to the document
        filename: Name of the file

    Returns:
        Basic metadata dictionary
    """
    return {
        "summary": f"Dokument: {filename}",
        "document_type": "Dokument",
        "categories": ["Unbekannt"],
        "entities": [],
        "persons": [],
        "places": [],
        "mentioned_dates": [],
        "file_references": [],
        "language": "unbekannt",
        "sentiment": "neutral",
        "complexity": "medium",
        "word_count_estimate": 0
    }