# File Search Server V2 - Technische Spezifikation

## Überblick

Dieses Dokument spezifiziert die Implementierung eines erweiterten MCP File Search Servers mit hybridem Suchansatz. Das System kombiniert FTS (Full-Text Search), Fuzzy-Matching für Schreibfehler und optional Vektor-basierte semantische Suche.

## Aktueller Stand

### Vorhandene Datenbank-Struktur

**Haupt-Tabelle: `documents`**
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    file_path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT,
    size INTEGER,
    mime_type TEXT,
    md5_hash TEXT NOT NULL,
    original_text TEXT,
    markdown_content TEXT,
    summary TEXT,
    document_type TEXT,
    categories TEXT,           -- JSON Array: ["Kategorie1", "Kategorie2"]
    entities TEXT,             -- JSON Array: ["Entity1", "Entity2"]  
    persons TEXT,              -- JSON Array: ["Person1", "Person2"]
    places TEXT,               -- JSON Array: ["Ort1", "Ort2"]
    mentioned_dates TEXT,      -- JSON Array: ["2024-01-01", "2024-02-15"]
    file_references TEXT,      -- JSON Array: ["file1.pdf", "file2.docx"]
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Aktueller Datenbankstand:**
- 88 Dokumente vollständig indexiert
- Reichhaltige Metadaten (Personen, Orte, Kategorien) bereits extrahiert
- Keine Duplikate, gute Datenqualität

### Bereits implementierte FTS-Tabellen

**Status:** ✅ Bereits erstellt und befüllt
```sql
-- Basis FTS-Tabelle
CREATE VIRTUAL TABLE documents_fts USING fts5(
    original_text,
    markdown_content, 
    summary,
    document_type,
    categories,
    entities,
    persons,
    places,
    mentioned_dates,
    file_references
);

-- Erweiterte FTS-Tabelle (mit Dateinamen/Pfaden)
CREATE VIRTUAL TABLE documents_fts_extended USING fts5(
    id UNINDEXED,
    filename,
    file_path,
    original_text,
    markdown_content,
    summary,
    document_type,
    categories,
    entities,
    persons,
    places,
    mentioned_dates
);
```

### Bereits implementierte Trigger

**Status:** ✅ Bereits erstellt und getestet

**INSERT Trigger:**
```sql
CREATE TRIGGER documents_fts_insert 
AFTER INSERT ON documents
BEGIN
    INSERT INTO documents_fts (...) VALUES (NEW.*);
    INSERT INTO documents_fts_extended (...) VALUES (NEW.*);
END;
```

**UPDATE Trigger:**
```sql
CREATE TRIGGER documents_fts_update 
AFTER UPDATE ON documents
BEGIN
    UPDATE documents_fts SET [...] WHERE rowid = OLD.id;
    UPDATE documents_fts_extended SET [...] WHERE id = OLD.id;
END;
```

**DELETE Trigger:**
```sql
CREATE TRIGGER documents_fts_delete 
AFTER DELETE ON documents
BEGIN
    DELETE FROM documents_fts WHERE rowid = OLD.id;
    DELETE FROM documents_fts_extended WHERE id = OLD.id;
END;
```

## Geplante Erweiterungen

### 1. Fuzzy-Matching System

**Ziel:** Behandlung von Schreibfehlern in Namen und Orten

#### Neue Tabellen (zu erstellen)

```sql
-- Normalisierte Personennamen für Fuzzy-Matching
CREATE TABLE persons_fuzzy (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    original_name TEXT,
    soundex_code TEXT,
    normalized_name TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Normalisierte Ortsnamen für Fuzzy-Matching  
CREATE TABLE places_fuzzy (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    original_place TEXT,
    soundex_code TEXT,
    normalized_place TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Indizes für Performance
CREATE INDEX idx_persons_soundex ON persons_fuzzy(soundex_code);
CREATE INDEX idx_persons_normalized ON persons_fuzzy(normalized_name);
CREATE INDEX idx_places_soundex ON places_fuzzy(soundex_code);
CREATE INDEX idx_places_normalized ON places_fuzzy(normalized_place);
```

#### Neue Trigger (zu erstellen)

```sql
-- Erweiterte Trigger für automatische Fuzzy-Tabellen-Updates
CREATE TRIGGER documents_fuzzy_insert 
AFTER INSERT ON documents
BEGIN
    -- Persons normalisieren
    INSERT INTO persons_fuzzy (document_id, original_name, soundex_code, normalized_name)
    SELECT 
        NEW.id,
        json_extract(value, '$'),
        soundex(json_extract(value, '$')),
        lower(trim(json_extract(value, '$')))
    FROM json_each(NEW.persons)
    WHERE json_extract(value, '$') != '';
    
    -- Places normalisieren
    INSERT INTO places_fuzzy (document_id, original_place, soundex_code, normalized_place)
    SELECT 
        NEW.id,
        json_extract(value, '$'),
        soundex(json_extract(value, '$')),
        lower(trim(json_extract(value, '$')))
    FROM json_each(NEW.places)
    WHERE json_extract(value, '$') != '';
END;

-- Entsprechende UPDATE und DELETE Trigger für Fuzzy-Tabellen
CREATE TRIGGER documents_fuzzy_update 
AFTER UPDATE ON documents
BEGIN
    DELETE FROM persons_fuzzy WHERE document_id = OLD.id;
    DELETE FROM places_fuzzy WHERE document_id = OLD.id;
    
    -- Neue Einträge einfügen (analog zu INSERT)
    [...]
END;

CREATE TRIGGER documents_fuzzy_delete 
AFTER DELETE ON documents
BEGIN
    DELETE FROM persons_fuzzy WHERE document_id = OLD.id;
    DELETE FROM places_fuzzy WHERE document_id = OLD.id;
END;
```

### 2. Vektor-Store System (Optional/Zukunft)

**Technologie:** BGE-m3 via Ollama
**Ziel:** Semantische Ähnlichkeitssuche

#### Neue Tabelle (zu erstellen)

```sql
CREATE TABLE document_embeddings (
    document_id INTEGER PRIMARY KEY,
    content_embedding BLOB,          -- BGE-m3 Vektor für Inhalt
    metadata_embedding BLOB,         -- BGE-m3 Vektor für Entitäten/Personen
    summary_embedding BLOB,          -- BGE-m3 Vektor für Zusammenfassung
    embedding_model TEXT DEFAULT 'bge-m3',
    embedding_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX idx_embeddings_model ON document_embeddings(embedding_model);
```

## Neue MCP-Tools Spezifikation

### Haupttool: `getData`

**Zweck:** Hybrid-Suche mit mehreren Strategien

```python
@mcp.tool()
async def getData(
    search_terms: List[str],                    # ["BMW", "Ihring", "2024"]
    search_modes: List[str] = ["fts", "fuzzy"], # Aktivierte Suchmodi
    fuzzy_tolerance: float = 0.8,               # Fuzzy-Matching Schwelle
    max_results: int = 20,                      # Maximale Ergebnisse
    date_filter: Optional[str] = None           # "2024", "2024-03" etc.
) -> List[Dict[str, Any]]:
    """
    Natürlichsprachliche Dokumentensuche mit Hybrid-Strategien
    
    Args:
        search_terms: Liste von Suchbegriffen
        search_modes: ["fts", "fuzzy", "vector"] - Welche Suchmethoden verwenden
        fuzzy_tolerance: Ähnlichkeits-Schwelle für Fuzzy-Matching (0.0-1.0)
        max_results: Maximale Anzahl zurückgegebener Dokumente
        date_filter: Optional Datumsfilter (Jahr oder Jahr-Monat)
    
    Returns:
        Liste von Dokumenten mit Relevanz-Scores und Match-Typ
    """
```

### Interne Such-Strategien

#### 1. FTS-Suche (bereits implementiert)
```sql
-- Exakte Treffer in FTS-Tabelle
SELECT d.id, d.filename, d.file_path, 
       SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 300) as content_preview,
       'fts' as match_type,
       rank as relevance_score
FROM documents_fts_extended fts
JOIN documents d ON d.id = fts.id
WHERE documents_fts_extended MATCH ?
ORDER BY rank
```

#### 2. Fuzzy-Suche (zu implementieren)
```sql
-- Schreibfehler-tolerante Suche in Personen
SELECT DISTINCT d.id, d.filename, d.file_path,
       SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 300) as content_preview,
       'fuzzy_person' as match_type,
       similarity(pf.normalized_name, ?) as relevance_score
FROM persons_fuzzy pf
JOIN documents d ON d.id = pf.document_id
WHERE pf.soundex_code = soundex(?)
   OR similarity(pf.normalized_name, lower(?)) > ?

-- Analoge Abfrage für Orte in places_fuzzy
```

#### 3. Vektor-Suche (Zukunft)
```sql
-- Semantische Ähnlichkeitssuche
SELECT d.id, d.filename, d.file_path,
       SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 300) as content_preview,
       'vector' as match_type,
       cosine_similarity(de.content_embedding, ?) as relevance_score
FROM document_embeddings de
JOIN documents d ON d.id = de.document_id
WHERE cosine_similarity(de.content_embedding, ?) > 0.7
ORDER BY relevance_score DESC
```

### Hybrid-Ranking-Algorithmus

```python
def combine_and_rank_results(fts_results, fuzzy_results, vector_results=None):
    """
    Kombiniert und rankt Ergebnisse aus verschiedenen Suchstrategien
    
    Gewichtung:
    - FTS: 1.0 (exakte Treffer höchste Priorität)
    - Fuzzy: 0.8 (Schreibfehler-Korrekturen)  
    - Vector: 0.6 (semantische Ähnlichkeit)
    """
    combined = {}
    
    # FTS-Ergebnisse (höchste Gewichtung)
    for result in fts_results:
        doc_id = result['id']
        combined[doc_id] = {
            **result,
            'combined_score': result['relevance_score'] * 1.0,
            'match_types': ['fts']
        }
    
    # Fuzzy-Ergebnisse hinzufügen
    for result in fuzzy_results:
        doc_id = result['id']
        fuzzy_score = result['relevance_score'] * 0.8
        
        if doc_id in combined:
            # Bestehenden Score verbessern
            combined[doc_id]['combined_score'] += fuzzy_score * 0.5
            combined[doc_id]['match_types'].append(result['match_type'])
        else:
            # Neues Ergebnis
            combined[doc_id] = {
                **result,
                'combined_score': fuzzy_score,
                'match_types': [result['match_type']]
            }
    
    # Sortieren nach combined_score
    return sorted(combined.values(), 
                 key=lambda x: x['combined_score'], 
                 reverse=True)
```

## System-Prompt Optimierung

### Ollama Modelfile

**Datei:** `fuzzy_search_llama.modelfile`
```dockerfile
FROM llama3.2:3b

SYSTEM """You are a document search function caller.

BEHAVIOR:
- When users ask to find, search, or locate documents, call getData immediately
- Extract key terms from queries: names, places, topics, dates
- Use separate search terms rather than phrases
- After receiving results, provide natural German summaries

EXAMPLES:
"BMW Dokumente von Ihring" → getData(["BMW", "Ihring"])
"Hausbegehung 2024" → getData(["Hausbegehung", "2024"])
"Dateien über Baltmannsweiler" → getData(["Baltmannsweiler"])

FORBIDDEN:
- Never explain function syntax
- Never show JSON examples
- Never say "you can call getData like this"

ACT, don't explain."""

PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
```

### MCP-Tool System-Prompt

```python
SYSTEM_PROMPT = """Sie sind ein Dokumentensuch-Spezialist.

VERHALTEN:
- Bei Such-Anfragen: getData-Funktion sofort aufrufen
- Suchbegriffe extrahieren: Namen, Orte, Themen, Daten
- Nach Ergebnissen: Natürliche deutsche Zusammenfassung
- Keine Syntax-Erklärungen oder JSON-Beispiele

SUCHBEGRIFF-EXTRAKTION:
- Schlüsselwörter aus Benutzer-Anfragen
- Namen auch mit Tippfehlern (Ihring, Ihrings, Ihringer)
- Orte und Adressen
- Jahreszahlen und Daten
- Themen und Kategorien

Nach getData-Aufruf: Ergebnisse natürlich auf Deutsch zusammenfassen."""
```

## Implementierungsreihenfolge

### Phase 1: Fuzzy-Matching Basis
1. **Fuzzy-Tabellen erstellen** (`persons_fuzzy`, `places_fuzzy`)
2. **Erweiterte Trigger implementieren** (Fuzzy-Updates)
3. **Bestehende Daten migrieren** (alle 88 Dokumente in Fuzzy-Tabellen)
4. **getData v1 erweitern** (FTS + Fuzzy)

### Phase 2: Tool-Calling Optimierung  
1. **Ollama Modelfile erstellen** und testen
2. **System-Prompt optimieren** für Llama 3.2:3B
3. **MCP-Client erweitern** mit verbessertem Tool-Handling
4. **End-to-End Tests** mit realen Suchanfragen

### Phase 3: Vektor-Store (Optional)
1. **Embedding-Pipeline** mit BGE-m3/Ollama
2. **Background-Service** für asynchrone Embedding-Erstellung
3. **getData v2** mit Vektor-Suche
4. **Performance-Optimierung** und Caching

## Test-Szenarien

### Fuzzy-Matching Tests
```python
test_cases = [
    ("BMW von Ihrig", ["BMW", "Ihring"]),        # Schreibfehler in Namen
    ("Dokumente Baltmansweiler", ["Baltmannsweiler"]),  # Schreibfehler in Orten
    ("Auto Ihrings", ["Auto", "Ihring"]),        # Possessiv-Formen
    ("Hausbegehung 2024", ["Hausbegehung", "2024"])  # Kombiniert
]
```

### Tool-Calling Tests
```python
llm_test_queries = [
    "Finde BMW Dokumente",                    # Einfache Suche
    "Zeige mir Dateien von Herrn Ihring",   # Person mit Titel
    "Hausbegehung Baltmannsweiler 2024",    # Multi-Term mit Ort
    "Was für Dateien hast du über Autos?"   # Thematische Suche
]
```

## Performance-Anforderungen

- **Suchzeit:** < 2 Sekunden für Hybrid-Suche
- **Fuzzy-Matching:** > 0.8 Accuracy für Namen/Orte
- **Tool-Calling:** > 95% Success Rate mit Llama 3.2:3B
- **Datenbank:** Unterstützung für bis zu 100.000 Dokumente

## Fehlerbehandlung

### Fuzzy-Matching Fallbacks
1. Soundex-Matching fehlgeschlagen → Levenshtein-Distanz
2. Keine Fuzzy-Treffer → Fallback auf FTS mit Wildcards
3. Alle Strategien fehlgeschlagen → Benutzer-Feedback für Suchbegriffe

### Tool-Calling Fallbacks
1. Llama 3.2 erklärt statt aufruft → System-Prompt-Anpassung
2. JSON-Parsing fehlgeschlagen → Regex-Extraction
3. MCP-Server nicht erreichbar → Direkte SQLite-Abfrage

## Dateipfade und Konfiguration

### Wichtige Dateien
- **Datenbank:** `/Users/aaron/Projects/Simple_MCP_DB/filebrowser.db`
- **MCP-Server:** `server.py` (aktuell)
- **Client:** `mcp_client_terminal.py` (aktuell)
- **System-Prompt:** `system_prompt.txt` (aktuell)
- **Ollama Model:** `fuzzy_search_llama` (zu erstellen)

### Ollama-Konfiguration
- **Basis-Modell:** `llama3.2:3b`
- **API-Endpoint:** `http://localhost:11434`
- **BGE-m3 Model:** `bge-m3:latest` (für Vektor-Store)

## Abhängigkeiten

### Python-Packages (bereits vorhanden)
```python
# Aktuelle Abhängigkeiten
from mcp.server.fastmcp import FastMCP
import sqlite3
import json
import requests
import subprocess

# Zusätzlich benötigt für Fuzzy-Matching
import difflib  # Für Ähnlichkeits-Berechnung
import re      # Für String-Normalisierung

# Zukünftig für Vektor-Store
import numpy as np    # Für Vektor-Operationen
import ollama        # Für BGE-m3 Embeddings
```

### Externe Tools
- **Ollama:** Bereits installiert und laufend
- **SQLite:** Bereits konfiguriert mit FTS5
- **BGE-m3:** Bereits in Ollama verfügbar

## Erfolgs-Metriken

### Funktionale Tests
- [ ] Fuzzy-Tabellen korrekt befüllt (88 Dokumente)
- [ ] Trigger funktionieren bei INSERT/UPDATE/DELETE
- [ ] getData-Tool findet Dokumente mit Schreibfehlern
- [ ] Llama 3.2 ruft Tools auf (keine Erklärungen)
- [ ] Hybrid-Ranking liefert relevante Ergebnisse

### Performance-Tests  
- [ ] Suchzeit < 2s für 20 Ergebnisse
- [ ] Memory Usage < 500MB für Client+Server
- [ ] 100% Tool-Call Success Rate über 50 Tests

---

**Autor:** Claude & Aaron  
**Datum:** 29. Juni 2025  
**Version:** 1.0  
**Status:** Bereit für Claude Code Implementierung
