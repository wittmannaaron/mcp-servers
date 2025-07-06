# File Search Server v3 - Semantic Search Engine

Ein vollständig funktionsfähiger **Semantic Search Server** mit KI-gestützter Dokumentenanalyse und Vektorsuche.

## 🚀 Features

### Kern-Funktionalitäten
- **📁 Automatische Dateierkennung** - Überwacht Verzeichnisse und verarbeitet neue Dateien automatisch
- **🔍 Semantic Search** - Vektorbasierte Ähnlichkeitssuche mit BGE-M3 Embeddings
- **🤖 KI-Metadaten** - Automatische Extraktion von Zusammenfassungen, Kategorien und Entitäten
- **📄 Multi-Format Support** - PDF, DOCX, EML, ZIP, Bilder, Text-Dateien
- **⚡ Echtzeit-Verarbeitung** - Sofortige Indizierung neuer Dokumente

### Technische Highlights
- **Vektorsuche** mit 1024-dimensionalen BGE-M3 Embeddings
- **Markdown-bewusste Chunking** für optimale Textaufteilung
- **MCP Protocol Integration** für KI-Services
- **SQLite mit JSON-Vektoren** für effiziente Speicherung
- **Robuste Parameter-Behandlung** für sichere SQL-Operationen

## 🏗️ Architektur

| Komponente | Zweck | Technologie |
|------------|-------|-------------|
| **File Watcher** | Überwacht Dateisystem-Änderungen | Python + watchdog |
| **Text Extractor** | Extrahiert Text aus Dateien | Docling + AppleScript |
| **Embedding Service** | Erstellt Vektorrepräsentationen | BGE-M3 (1024 dim) |
| **Chunking Service** | Teilt Texte semantisch auf | Markdown-aware splitting |
| **Ingestion Engine** | Verarbeitet und speichert Dokumente | Python + SQLite |
| **MCP API Server** | KI-Metadaten-Generierung | FastAPI + MCP Protocol |
| **Semantic Search** | Vektorbasierte Ähnlichkeitssuche | Cosine Similarity |
| **Database Layer** | Dokumentenspeicherung | SQLite + JSON Vectors |

## 📦 Installation

1. **Virtual Environment erstellen:**
   ```bash
   cd /Users/aaron/Projects/mcp-servers/file-search-server-v3
   python -m venv venv
   source venv/bin/activate
   ```

2. **Dependencies installieren:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Umgebung konfigurieren:**
   ```bash
   cp .env.example .env
   # .env mit Ihren Einstellungen bearbeiten
   ```

4. **Server starten:**
   ```bash
   python main.py
   ```

## 🔧 Konfiguration

### Logging
Das Log-Level kann in der `.env` Datei konfiguriert werden:
```bash
# Verfügbare Log-Level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL="WARNING"
```

### KI-Services
Für die automatische Metadaten-Extraktion werden MCP-kompatible KI-Services benötigt.

## 🧪 Testing

### Vollständiger Ingestion-Test
```bash
python full_ingestion_test.py
```
- Verarbeitet alle Dateien in einem Verzeichnis
- Automatische Fehlererkennnung
- Detaillierte Statistiken und Berichte

### Datenbank zurücksetzen
```bash
python clear_database.py
```

## 📊 Semantic Search Pipeline

### 1. Dokumenten-Ingestion
```
Datei → Text-Extraktion → KI-Analyse → Chunking → Embeddings → Datenbank
```

### 2. Semantic Search
```
Query → Embedding → Vektorsuche → Ähnlichkeits-Ranking → Ergebnisse
```

### 3. Datenbank-Schema
```sql
-- Dokumente
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    filename TEXT,
    content TEXT,
    summary TEXT,
    categories JSON,
    entities JSON,
    -- ... weitere Metadaten
);

-- Text-Chunks
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    content TEXT,
    chunk_index INTEGER,
    char_count INTEGER
);

-- Vektor-Embeddings
CREATE TABLE chunk_vectors (
    chunk_id INTEGER PRIMARY KEY,
    embedding_json TEXT  -- 1024-dim BGE-M3 Vektor
);
```

## 🔍 Unterstützte Dateiformate

- **📄 Dokumente**: PDF, DOCX, TXT, MD
- **📧 E-Mails**: EML (mit Anhängen)
- **🗜️ Archive**: ZIP (rekursive Verarbeitung)
- **🖼️ Bilder**: JPEG, PNG (OCR mit Docling)
- **💻 Code**: Python, JavaScript, etc.

## 🛡️ Robuste Verarbeitung

### Hidden File Filtering
Automatisches Filtern von System-Dateien:
- **macOS**: `.DS_Store`, `._*` Dateien, `__MACOSX/` Verzeichnisse
- **Windows**: `Thumbs.db`, `desktop.ini`
- **Version Control**: `.git/`, `.svn/` Verzeichnisse
- **Generisch**: Alle Punkt-Dateien und versteckte Verzeichnisse

### Fehlerbehandlung
- Sichere SQL-Parameter-Substitution
- Robuste JSON-Parsing
- Automatische Wiederherstellung bei Fehlern
- Umfassende Logging und Monitoring

## 🔗 MCP Integration

Dieser Server ist für die Zusammenarbeit mit MCP (Model Context Protocol) Servern konzipiert und enthält einen integrierten SQLite MCP Server:

```
file-search-server-v3/
├── src/core/                  ← Kern-Funktionalitäten
│   ├── document_store.py      ← Dokumentenverwaltung
│   ├── mcp_client.py          ← MCP Client Integration
│   └── ...
├── src/sqlite/                ← Integrierter SQLite MCP Server
│   ├── src/mcp_server_sqlite/ ← MCP Server Implementation
│   └── pyproject.toml         ← Server Dependencies
├── data/                      ← Zentrale Datenspeicherung
│   └── filebrowser.db         ← SQLite Datenbank
└── ...
```

### Konsolidierte Architektur
- **Einheitliche Projektstruktur** - Alle Komponenten in einem Verzeichnis
- **Zentrale Datenspeicherung** - Datenbank im `data/` Verzeichnis
- **Integrierter MCP Server** - SQLite Server direkt im Projekt enthalten
- **Vereinfachte Konfiguration** - Konsistente Pfade in allen Komponenten

## 📈 Performance

### Benchmark-Ergebnisse
- **144 Dateien** in 29 Minuten verarbeitet
- **162 Datenbank-Einträge** (inkl. E-Mail-Anhänge)
- **100% Erfolgsrate** bei der Verarbeitung
- **Perfekte Chunk/Vektor-Zuordnung** (1:1)

### Optimierungen
- Batch-Verarbeitung von Embeddings
- Effiziente SQLite-Indizierung
- Speicher-optimierte Vektoroperationen
- Parallele Verarbeitung von Dokumenten

## 🚀 Produktions-Status

✅ **PRODUCTION READY** - Vollständig getestet und einsatzbereit

- Alle kritischen Bugs behoben
- Umfassende Tests durchgeführt
- Robuste Fehlerbehandlung implementiert
- Performance optimiert
- Dokumentation vollständig

---

**Entwickelt für professionelle Semantic Search Anwendungen mit KI-Integration.**
