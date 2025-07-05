"""
LLM Prompts for FileBrowser Document Analysis.
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
{original_text[:150000]}  # Begrenzt auf 150000 Zeichen für llama3.2 Token-Window

AUFGABE:
Analysiere den Dokumenteninhalt und erstelle strukturierte Metadaten. Antworte EXAKT in diesem JSON-Format:

{{
    "summary": "Eine prägnante 2-3 Satz Zusammenfassung des Dokumenteninhalts",
    "document_type": "Bewerbung",
    "categories": ["Kategorie1", "Kategorie2"],
    "entities": ["Organisation1", "Konzept1"],
    "persons": ["Max Mustermann", "Dr. Maria Schmidt"],
    "places": ["Berlin", "Deutschland", "Musterstraße 123"],
    "mentioned_dates": ["2024-01-15", "15.01.2024"],
    "file_references": ["dokument.pdf", "anhang.xlsx"],
    "language": "de",
    "sentiment": "neutral",
    "complexity": "medium",
    "word_count_estimate": 150
}}

RICHTLINIEN:
- summary: Maximal 200 Zeichen, fokussiert auf Hauptinhalt
- document_type: Wähle EINEN Typ: email, Behörde, Steuer, Bewerbung, Finance, Job, Vertrag, Rechnung, Brief, Notizen, Bericht, Anleitung
- categories: 2-4 thematische Kategorien (z.B. "Business", "Technik", "Verwaltung")
- entities: Organisationen, Firmen, Konzepte, Produkte (KEINE Personen oder Orte)
- persons: Alle erwähnten Personen mit vollständigen Namen
- places: Orte, Adressen, Länder, Städte
- mentioned_dates: Alle Daten im Format YYYY-MM-DD oder DD.MM.YYYY
- file_references: Erwähnte Dateinamen mit Erweiterung
- language: Hauptsprache (de, en, fr, it)
- sentiment: neutral, positive oder negative
- complexity: low, medium oder high
- word_count_estimate: Geschätzte Anzahl Wörter als Zahl

WICHTIG: Verwende nur gültiges JSON ohne Kommentare oder zusätzliche Zeichen!

WICHTIG:
- Antworte NUR mit dem JSON-Objekt
- Keine zusätzlichen Erklärungen oder Formatierung
- Alle Strings in Anführungszeichen
- Arrays auch bei nur einem Element verwenden
- Bei unklarem Inhalt verwende "unbekannt" oder leere Arrays
"""

    return prompt

def get_ollama_system_prompt() -> str:
    """
    System prompt for Ollama to ensure consistent JSON responses.
    """
    return """Du bist ein Dokumentenanalyst, der strukturierte JSON-Metadaten erstellt.
Antworte IMMER nur mit gültigem JSON ohne zusätzliche Erklärungen oder Formatierung.
Verwende deutsche Begriffe für Kategorien und Themen, aber englische Schlüssel im JSON."""

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