# MCP Servers - Fork mit eigenen Erweiterungen

> Fork von [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) mit eigenen MCP-Servern fuer lokale Dokumenten-Suche und -Katalogisierung.

Dieses Repository erweitert die offiziellen MCP-Server um ein vollstaendiges Dokumenten-Management-System mit KI-gestuetzter Ingestion, semantischer Suche und nativer macOS-App.

## Eigene Projekte

### file-catalog (Dokument-Ingestion-System)

**Pfad:** `file-catalog/`

Ein fokussiertes Dokument-Ingestion-System mit KI-gestuetzter Analyse:

- **Multi-Tool-Extraktion:** Intelligente Auswahl zwischen docling, markitdown und pandoc je nach Dateityp
- **Ollama LLM Integration:** Lokale KI-Metadaten-Extraktion (Zusammenfassungen, Kategorien, Entitaeten)
- **BGE-M3 Vektorembeddings:** Semantische Suche ueber 1024-dimensionale Vektoren
- **FTS5 Volltext-Suche:** Trigger-basierte automatische Index-Synchronisation
- **Fuzzy-Suche:** Phonetische Aehnlichkeitssuche (Soundex) fuer Personen- und Ortsnamen
- **Multi-Format-Support:** PDF, Office (DOCX, XLSX, PPTX), Apple Pages, E-Mail (EML), ZIP-Archive, Bilder (OCR via Docling)
- **macOS-optimiert:** Apple Pages via AppleScript, Hidden-File-Filterung

### file-search-server (MCP-Such-Server)

**Pfad:** `file-search-server/`

MCP-Server mit 9 spezialisierten Such-Tools fuer die Dokumentensuche:

| Tool | Funktion |
|------|----------|
| `search_file_content` | Inhaltssuche ueber mehrere Felder |
| `search_by_category` | Kategorie-Filter (Familie, Bewerbung, etc.) |
| `search_by_person` | Personensuche mit Fuzzy-Matching |
| `search_files_by_date` | Datumsbereich-Filterung |
| `find_duplicate_files` | Duplikat-Erkennung |
| `search_by_filename` | Dateinamen-Muster |
| `search_by_extension` | Dateityp-Filter |
| `get_file_details` | Vollstaendige Metadaten |
| `get_database_stats` | Datenbank-Statistiken |

### file-search-server-v2 (Erweiterte Suche)

**Pfad:** `file-search-server-v2/`

Erweitert v1 um 9 spezialisierte Such-Tools, optimiert fuer deutsche Dokumente. Fuzzy-Suche fuer Personen/Orte (mit OCR-Fehlerkorrektur), semantische Suche, Tool-Chaining fuer komplexe Abfragen. Nativer macOS WebKit-Client.

### file-search-server-v2.1 (Native macOS App)

**Pfad:** `file-search-server-v2.1/`

Vollstaendige native macOS-Anwendung:

- **React-Frontend** mit klickbaren Tabellen (Datei oeffnen, Ordner oeffnen, Markdown-Vorschau)
- **Flask-Backend** mit LLM-gestuetzter Keyword-Extraktion
- **PyWebView-Integration** fuer native macOS-App
- **Chat-Interface** und Sortierung nach Relevanz/Name/Datum

### file-search-server-v3 (Semantic Search Engine)

**Pfad:** `file-search-server-v3/`

Vollstaendige Semantic Search Engine:

- **BGE-M3 Embeddings:** 1024-dimensionale Vektorsuche
- **Automatische Dateierkennung** und KI-Metadaten-Extraktion
- **Markdown-bewusstes Chunking**
- **Multi-Format-Support:** PDF, DOCX, EML, ZIP, Bilder
- **Docling OCR:** Bildverarbeitung mit Layout-Analyse

### file-search-server-v3.1 (Ingestion Pipeline)

**Pfad:** `file-search-server-v3.1/`

Fokussierte Dokument-Ingestion-Pipeline:

- **Vision-LLM-Unterstuetzung:** Qwen2.5VL
- **Remote-Ollama-Backend**
- **Native macOS GUI** fuer Ingestion

## Voraussetzungen

- **macOS** (Linux-Portierung moeglich, Apple-spezifische Features entfallen)
- **Python 3.13+**
- **Ollama** mit Modellen: `llama3.2:latest`, `bge-m3`
- **pandoc** (`brew install pandoc`)
- **Node.js** (fuer React-Frontend in v2.1)

## Entwicklungsverlauf

Das Projekt entwickelte sich iterativ:

```
file-search-server (v1)    - MCP-Server mit 9 Such-Tools
       |
file-search-server-v2      - Deutsche Sprachoptimierung, Fuzzy-Suche
       |
file-search-server-v2.1    - React/Flask/PyWebView Native App
       |
file-search-server-v3      - Semantic Search mit BGE-M3
       |
file-search-server-v3.1    - Ingestion Pipeline, Vision-LLM
       |
file-catalog               - Konsolidiertes Ingestion-System (aktuell)
```

## Upstream-Server

Die Original-MCP-Server aus dem Upstream-Repository sind weiterhin unter `src/` verfuegbar:

- `src/filesystem` - Dateisystem-Zugriff
- `src/sqlite` - SQLite-Datenbank
- `src/brave-search` - Brave Web-Suche
- `src/github` - GitHub-Integration
- Und weitere (siehe [Original-Dokumentation](https://github.com/modelcontextprotocol/servers))

## Lizenz

Siehe [LICENSE](LICENSE) (MIT License, uebernommen vom Upstream-Repository).
