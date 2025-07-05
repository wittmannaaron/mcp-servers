# Claude Developer Context

## 🎯 Projekt-Übersicht
**Projektname:** File Search Server V3 - Universal Document Processing Pipeline  
**Beschreibung:** Umfassende Verarbeitungslinie für alle Arten von Dateien auf macOS mit KI-basierter Metadaten-Generierung und Embedding-Pipeline  
**Aktueller Status:** Development - Server-Komponenten extrahiert, Email-Pipeline und Embeddings in Entwicklung  
**Version:** 3.0-dev

## 🏗️ Technische Basis
**Haupttechnologien:**
- Sprache: Python 3.13
- Framework: FastAPI + MCP Protocol
- Datenbank: SQLite mit FTS5 für Volltext-Suche
- Environment: .venv (Virtual Environment)
- Dependencies: requirements.txt

**Architektur-Prinzipien:**
- **KISS Principle**: Keep It Simple Stupid - Einfache, verständliche Lösungen bevorzugen
- Modularer Aufbau (Code-Files max. 300 Zeilen)
- MCP-compliant: Alle DB/LLM-Calls über MCP Protocol
- Aktuelle Software-Versionen verwenden
- Clean Code & Separation of Concerns
- Async/Await Pattern für Performance

## 🎯 Projekt-Scope
**Fokus: Nur Dokumente aller Art**
- ✅ **Dokumente**: PDF, Word, Excel, PowerPoint, Pages, Text, Markdown, etc.
- ✅ **Email-Dokumente**: .eml Dateien mit Dokumenten-Attachments
- ✅ **Archive**: ZIP-Dateien mit Dokumenten (recursive processing)
- ✅ **Versteckte Dokumente**: In Email-Attachments oder ZIP-Archiven
- ❌ **Nicht im Scope**: Fotos, Videos, Musik, andere Medien-Dateien

**Typische Anwendung:**
- Computer mit vielen Dokumenten an verschiedenen Orten
- Gleiche Dokumente möglicherweise mehrfach vorhanden
- Dokumente versteckt in Email-Attachments oder ZIP-Archiven
- Lokale Dateisysteme (nicht Cloud/Remote)

## 📁 Projekt-Struktur
```
file-search-server-v3/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── .mcp.json                  # MCP server configuration
├── src/
│   ├── api/                   # FastAPI server + MCP endpoints
│   ├── core/                  # Business logic (file watcher, ingestion)
│   ├── database/              # MCP-compliant database operations
│   ├── extractors/            # Text extraction engines
│   └── utils/                 # AppleScript converter & utilities
├── config/                    # Configuration files (empty)
├── logs/                      # Log files (empty)
└── data/                      # Database files (empty)
```

## 🛠️ Development Workflow

### MCP-Server Requirements
Claude soll folgende MCP-Server verwenden:
- **taskmaster-ai**: Für Task-Management und Projektplanung
- **project-memory**: Für persistente Wissensspeicherung
- **context7**: Für aktuelle Software-Dokumentation
- **project-filesystem**: Für Dateizugriff (automatisch verfügbar)

### Git-Workflow
- **Lokales Git**: Derzeit nur lokale Repositories
- **Commit-Convention**: Conventional Commits (feat:, fix:, docs:, chore:)
- **Branch-Strategie**: Feature-Branches für neue Entwicklungen
- **Dokumentation**: Alle Änderungen in CHANGELOG.md dokumentieren

### Code-Standards
- **Datei-Größe**: Max. 300 Zeilen pro Code-File (strikt einhalten!)
- **MCP-Compliance**: Keine direkten DB/LLM-Calls, nur über MCP Protocol
- **Async Pattern**: Alle I/O-Operationen asynchron
- **Type Hints**: Vollständige Type Annotations
- **Logging**: Strukturiertes Logging mit loguru

## 📋 Aktuelle Prioritäten

### Hauptfokus: Erweiterte Dateiverarbeitung
**Phase 1 - Email Processing Pipeline:**
- .eml Dateien parsen und verarbeiten
- Attachment-Extraktion (PDFs, ZIPs mit PDFs/Dokumenten)
- Recursive Processing von verschachtelten Attachments
- Integration in bestehende Ingestion-Pipeline

**Phase 2 - Chunking & Embeddings Pipeline:**
- Markdown-Content aus documents-Tabelle chunken
- Embeddings mit lokalem Ollama bge-m3:latest generieren
- Integration in bestehende Datenbankstruktur
- Chunk-basierte Suche implementieren

### Bekannte Issues/Verbesserungen:
- Email-Parser für .eml Dateien fehlt
- Chunking-Algorithmus für optimale Embedding-Segmente
- Embedding-Speicherung in SQLite optimieren

### Nächste Schritte:
1. Email-Extractor in `src/extractors/` implementieren
2. Chunking-Service in `src/core/` erstellen
3. Embedding-Pipeline mit Ollama bge-m3 aufbauen
4. Tests für neue Komponenten schreiben

## 🔧 Development Setup
**Installation:**
```bash
cd /Users/aaron/Projects/mcp-servers/file-search-server-v3
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Environment:**
```bash
cp .env.example .env
# SQLITE_DB_PATH=./data/filebrowser.db
# OLLAMA_BASE_URL=http://localhost:11434
# EMBEDDING_MODEL=bge-m3:latest
```

**Run Server:**
```bash
python main.py
```

## 📖 Für Claude wichtig

### Arbeitsweise
- **Memory-First**: Immer zuerst project-memory nach ähnlichen Lösungen durchsuchen
- **KISS-First**: Einfachste Lösung wählen, die funktioniert - Komplexität vermeiden
- **MCP-First**: Alle Database/LLM-Operationen nur über MCP Protocol
- **Documentation**: Alle Änderungen dokumentieren (README, Code-Kommentare)
- **Git-Integration**: Commits für jeden wichtigen Arbeitsschritt
- **TaskMaster**: Komplexe Aufgaben in kleinere Tasks aufteilen

### Spezielle Patterns
- **KISS Implementation**: Funktionalität vor Eleganz - Readable Code vor Clever Code
- **Async Context Managers**: `async with get_mcp_client() as client:`
- **Error Handling**: Graceful degradation mit detailliertem Logging
- **File Size Limit**: Strikt 300 Zeilen pro File (bei Überschreitung aufteilen)
- **Modular Extractors**: Jeder Dateityp hat eigenen Extractor
- **Pipeline Architecture**: File Watcher → Extractor → Ingestion → Database

### Aktuelle Architektur-Constraints
- **Kein direkter SQLite-Zugriff**: Nur über MCP sqlite-server
- **Kein direkter Ollama-Zugriff**: Über MCP-Integration
- **Async/Await Pattern**: Für alle I/O-Operationen
- **Type Safety**: Vollständige Type Hints erforderlich

### Email Processing Requirements
- **Unterstützte Formate**: .eml mit MIME-parsing
- **Attachment-Typen**: PDF, ZIP (mit PDFs/Docs), Office-Dokumente, Images
- **Recursive Processing**: ZIPs mit weiteren ZIPs/Dokumenten
- **Metadata-Erhaltung**: Email-Headers, Attachment-Namen, Timestamps

### Embedding Pipeline Requirements
- **Chunking-Strategie**: Markdown-aware, semantische Grenzen beachten
- **Chunk-Größe**: Optimal für bge-m3 (512 tokens empfohlen)
- **Overlap**: 50-100 Token Überlappung zwischen Chunks
- **Metadata**: Chunk-Position, Parent-Document, Embedding-Timestamp

### Context-Updates
- **Letzte Aktualisierung:** 4. Juli 2025
- **Status:** Email-Pipeline vollständig implementiert und getestet, ZIP-Pipeline implementiert aber nicht getestet
- **Nächste Review:** Nach Abschluss und Test der ZIP-Pipeline

---
*Diese Datei wird bei wichtigen Architektur-Änderungen aktualisiert.*