# File Catalog - Enhanced Document Ingestion System

**Version 0.1** | **🍎 macOS-optimiert** | **🐍 Python 3.13+ erforderlich**

Ein fokussiertes **Dokument-Ingestion-System** mit KI-gestützter Analyse, erweiterten Extraktions-Tools und vollständiger MCP-Unterstützung.

## 🚀 Features

### Kern-Funktionalitäten
- **📄 Erweiterte Dokumentenextraktion** - Unterstützung für markitdown, pandoc und docling
- **🤖 Ollama LLM Integration** - Lokale KI-Metadaten-Extraktion
- **📊 Multi-Format Support** - PDF (docling), Office-Dokumente (markitdown), Markup (pandoc), Bilder (docling OCR)
- **⚡ Embedding-Generation** - BGE-M3 Vektorembeddings über Ollama
- **🧠 Intelligente Bildverarbeitung** - OCR + Layout-Analyse mit Docling (Apple Silicon optimiert)
- **📧 E-Mail & Archive Support** - EML-Dateien und ZIP-Archive
- **🔍 Volltext-Suche** - FTS5 mit automatischer Synchronisation
- **🗃️ MCP-Datenbank** - Vollständige Model Context Protocol Unterstützung

### Technische Highlights
- **Intelligente Tool-Auswahl** - Automatische Wahl des besten Extraktions-Tools
- **Ollama-Integration** - Lokale LLM-Analyse ohne externe API-Abhängigkeiten
- **MCP Protocol** - Kompatibilität mit Model Context Protocol
- **SQLite mit Vektoren** - Effiziente Speicherung von Embeddings
- **Robuste Verarbeitung** - Fehlerbehandlung und Fallback-Mechanismen
- **Fuzzy-Suche** - Personen- und Ortssuche mit phonetischer Ähnlichkeit
- **Trigger-basierte FTS** - Automatische Volltext-Index-Aktualisierung

## 🏗️ Tool-Prioritäten

| Dateityp | Primäres Tool | Fallback | Zweck |
|----------|---------------|-----------|--------|
| **PDF** | docling | markitdown, pandoc | Optimiert für PDFs |
| **Office-Dokumente** | markitdown | pandoc | DOCX, XLSX, PPTX, etc. |
| **Markup** | pandoc | markitdown | HTML, RTF, EPUB |
| **Bilder** | docling (OCR) | exiftool | OCR + Layout-Analyse |
| **Code** | direct read | - | Syntax-Preservation |
| **Text** | direct read | - | TXT, MD, CSV, JSON |

## 📦 Installation

### 🚀 Automatische Installation (Empfohlen)

Das Setup-Skript prüft alle Voraussetzungen, erstellt die Umgebung und konfiguriert das System automatisch:

```bash
cd /Users/aaron/Projects/mcp-servers/file-catalog
chmod +x setup.sh
./setup.sh
```

**Voraussetzungen (müssen vorher installiert sein):**
- **🍎 macOS** (Linux-Portierung geplant)
- **🐍 Python 3.13+** (getestet mit 3.13)
- **Ollama** mit Modellen: `llama3.2:latest` und `bge-m3`
- **pandoc** (via Homebrew: `brew install pandoc`)

### ⚙️ Manuelle Installation (Alternative)

Falls das automatische Setup nicht gewünscht ist:

1. **Virtual Environment erstellen:**
   ```bash
   cd /Users/aaron/Projects/mcp-servers/file-catalog
   python3.13 -m venv venv  # Python 3.13 empfohlen
   source venv/bin/activate
   ```

2. **Dependencies installieren:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Externe Tools installieren:**
   ```bash
   # pandoc (macOS via Homebrew)
   brew install pandoc
   
   # exiftool (optional, für Bildmetadaten)
   brew install exiftool
   ```

4. **Ollama einrichten:**
   ```bash
   # Ollama installieren (macOS)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # BGE-M3 Modell herunterladen
   ollama pull bge-m3
   
   # LLaMA-Modell für Textanalyse
   ollama pull llama3.2:latest
   ```

5. **Umgebung konfigurieren:**
   ```bash
   # .env Datei erstellen (falls nicht vorhanden)
   cp .env.example .env
   
   # Verzeichnisse erstellen
   mkdir -p data logs
   ```

## 🔧 Konfiguration

### Umgebungsvariablen
```bash
# Logging
LOG_LEVEL="INFO"
LOG_TO_FILE="true"

# Ollama Configuration
OLLAMA_HOST="http://localhost:11434"
OLLAMA_MODEL="llama3.2:latest"

# Processing Preferences
PREFER_MARKITDOWN="true"
PREFER_PANDOC="true"
USE_DOCLING_PDF_ONLY="true"

# File Processing
MAX_FILE_SIZE_MB="100"
```

## 🧪 Testing

### System-Prüfung
```bash
# Tool-Verfügbarkeit prüfen
python full_ingestion_test.py --check-tools
```

### Vollständiger Ingestion-Test
```bash
# Standard-Test mit allen Dateien
python full_ingestion_test.py

# Test mit begrenzter Dateizahl
python full_ingestion_test.py -c 10

# Test mit eigenem Verzeichnis
python full_ingestion_test.py -d /path/to/your/documents

# Ohne Datenbank-Reset (inkrementell)
python full_ingestion_test.py --no-clear
```

## 📊 Unterstützte Dateiformate

### Dokumente mit intelligenter Tool-Auswahl
- **📄 PDFs**: `docling` → `markitdown` → `pandoc`
- **📝 Office**: `markitdown` → `pandoc` (DOCX, XLSX, PPTX, ODT, ODS, ODP)
- **📄 Pages**: AppleScript → `markitdown` → `pandoc` (macOS only)
- **🌐 Markup**: `pandoc` → `markitdown` (HTML, HTM, RTF, EPUB)
- **🖼️ Bilder**: `docling` (OCR) → `exiftool` → basic (JPEG, JPG, PNG, BMP, GIF, TIFF, WEBP)
- **💻 Code**: Direct read (PY, JS, TS, JAVA, GO, SH, CPP, C, H, CSS)
- **📋 Text**: Direct read (TXT, MD, MARKDOWN, CSV, JSON, XML)

### Spezialformate
- **📧 E-Mails**: EML-Dateien mit Anhang-Extraktion
- **🗜️ Archive**: ZIP-Dateien mit rekursiver Verarbeitung

### Vollständige Liste der unterstützten Dateitypen

#### Dokument-Extractor
- **PDFs**: `.pdf`
- **Office**: `.docx`, `.pptx`, `.xlsx`, `.odt`, `.ods`, `.odp`
- **Pages (macOS)**: `.pages` (via AppleScript conversion)
- **Markup**: `.html`, `.htm`, `.rtf`, `.epub`
- **Bilder**: `.jpeg`, `.jpg`, `.png`, `.bmp`, `.gif`, `.tiff`, `.webp`
- **Code**: `.py`, `.js`, `.ts`, `.java`, `.go`, `.sh`, `.cpp`, `.c`, `.h`, `.css`
- **Text**: `.txt`, `.md`, `.markdown`, `.csv`, `.json`, `.xml`

#### E-Mail-Extractor
- **E-Mails**: `.eml`
- **Anhänge**: `.pdf`, `.doc`, `.docx`, `.txt`, `.rtf`, `.odt`, `.ppt`, `.pptx`, `.xls`, `.xlsx`, `.zip`

#### ZIP-Extractor
- **Archive**: `.zip`
- **Interne Dokumente**: `.pdf`, `.doc`, `.docx`, `.txt`, `.rtf`, `.odt`, `.ppt`, `.pptx`, `.xls`, `.xlsx`, `.md`, `.html`

## 🔧 Extraktions-Pipeline

### 1. Dokument-Extractor (`document_extractor.py`)
**Zweck**: Haupt-Extraktions-Engine für alle Dokumenttypen mit Multi-Tool-Unterstützung

**Funktionalität**:
- **Tool-Erkennung**: Automatische Verfügbarkeitsprüfung für `docling`, `markitdown`, `pandoc`, `exiftool`
- **Strategie-Auswahl**: Intelligente Prioritätsreihenfolge je nach Dateityp
- **Syntax-Erhaltung**: Code-Dateien mit Syntax-Highlighting in Markdown
- **Metadaten-Extraktion**: Umfassende EXIF-Daten für Bilder
- **Timeout-Schutz**: Verhindert Hängenbleiben bei problematischen Dateien

**Verarbeitung**:
- PDFs: `docling` → `markitdown` → `pandoc`
- Office: `markitdown` → `pandoc` (konfigurierbar)
- Pages (macOS): AppleScript Export zu DOCX → `markitdown` → `pandoc`
- Bilder: `docling` (OCR + Layout-Analyse) → `exiftool` für Metadaten
- Code/Text: Direktes Lesen mit Formatierung

### 1.1. Pages-Converter (`pages_converter.py`)
**Zweck**: Spezielle Behandlung von Apple Pages-Dateien auf macOS-Systemen

**Funktionalität**:
- **macOS-AppleScript-Integration**: Nutzt Pages-App zum Export als DOCX
- **Automatische Verfügbarkeitsprüfung**: Erkennt macOS und Pages-Installation
- **Temporäre Dateiverwaltung**: Sichere Erstellung und Bereinigung von DOCX-Dateien
- **Fallback-Mechanismus**: Graceful degradation auf Nicht-macOS-Systemen

**Verarbeitungsschritte**:
1. **Verfügbarkeitsprüfung**: Prüft macOS und Pages-App-Installation
2. **AppleScript-Automation**: Öffnet Pages, exportiert als DOCX, schließt ohne Speichern
3. **Content-Extraktion**: Temporäre DOCX wird mit `markitdown` oder `pandoc` verarbeitet
4. **Aufräumen**: Automatische Bereinigung der temporären DOCX-Datei

**Systemkompatibilität**:
- **macOS**: Vollständige Pages-Content-Extraktion via AppleScript
- **Andere Systeme**: Katalogisierung mit Hinweis auf fehlende macOS-Unterstützung

### 2. E-Mail-Extractor (`email_extractor.py`)
**Zweck**: Spezialisiert auf `.eml` E-Mail-Dateien mit Anhang-Verarbeitung

**Funktionalität**:
- **E-Mail-Parsing**: Nutzt Python's `email.policy.default`
- **Metadaten-Extraktion**: From, To, Subject, Date, Message-ID
- **Body-Verarbeitung**: Bevorzugt Plain-Text über HTML
- **Anhang-Verarbeitung**: Extraktion und Verarbeitung von Dokumenten
- **System-Datei-Filterung**: Überspringt `.DS_Store`, `._*`, `__MACOSX`

**Besonderheiten**:
- Verschachtelte ZIP-Unterstützung in Anhängen
- Temporäre Verzeichnisse mit automatischer Bereinigung
- HTML-Fallback durch Tag-Entfernung
- Separate Rückgabe von E-Mail-Daten und Anhängen

### 3. ZIP-Extractor (`zip_extractor.py`)
**Zweck**: Verarbeitung von ZIP-Archiven mit rekursiver Dokumentenverarbeitung

**Funktionalität**:
- **Archiv-Validierung**: Überprüfung auf gültiges ZIP-Format
- **Inhalts-Extraktion**: Alle Dateien in temporäres Verzeichnis
- **Datei-Filterung**: Überspringt System-Metadaten-Dateien
- **Rekursive Verarbeitung**: Verschachtelte Verzeichnisse
- **Metadaten-Tracking**: Erhält Dateihierarchie und ZIP-Pfade

**Besonderheiten**:
- Fehlerresistenz bei einzelnen Dateien
- Statistik-Tracking (Gesamt vs. verarbeitete Dateien)
- Aussagekräftige Anzeigenamen mit ZIP-Herkunft
- Sichere temporäre Verzeichnisse

## 🛡️ Robuste Verarbeitung

### Intelligente Tool-Auswahl
- Automatische Erkennung verfügbarer Tools
- Fallback-Mechanismen bei Tool-Fehlern
- Optimale Tool-Zuordnung nach Dateityp

### Fehlerbehandlung
- Graceful Degradation bei fehlenden Tools
- Ollama-Fallback mit Basis-Metadaten
- Umfassende Logging und Monitoring
- Hidden-File-Filterung (macOS-kompatibel)

### Gemeinsame Design-Patterns
- **Temporäre Verzeichnisse**: Sichere Auto-Bereinigung mit `tempfile`
- **Fehlerbehandlung**: Umfassende Try-Catch-Blöcke mit detailliertem Logging
- **System-Datei-Filterung**: Überspringt versteckte und System-Dateien
- **Modulares Design**: Unabhängige Verwendung oder Teil des Systems
- **Metadaten-Erhaltung**: Quelldatei-Beziehungen und Extraktions-Kontext
- **Logging-Integration**: Konsistente, strukturierte Logs mit Loguru

## 🔗 Ollama Integration

Dieses System ist für die Verwendung mit lokalen Ollama-Modellen optimiert:

```yaml
LLM-Pipeline:
  Dokumentanalyse: llama3.2:latest
  Embeddings: bge-m3
  Fallback: Basis-Metadaten ohne LLM
```

### Ollama-Setup
```bash
# Modelle installieren
ollama pull llama3.2:latest
ollama pull bge-m3

# Service starten
ollama serve

# Gesundheitscheck
curl http://localhost:11434/api/tags
```

## 📈 Performance

### Systemanforderungen
```bash
# macOS-spezifische Optimierungen
- Hidden-File-Filterung (._* Dateien)
- .DS_Store Behandlung
- Homebrew-Package-Manager
- macOS-optimierte Pfade
```

### Benchmark-Richtwerte
- **PDF-Extraktion**: docling (~2-10s pro Dokument)
- **Office-Dokumente**: markitdown (~1-5s pro Dokument)
- **LLM-Analyse**: ~5-15s pro Dokument (je nach Länge)
- **Embedding-Generation**: ~1-3s pro Chunk-Batch

### Optimierungen
- Lokale LLM-Verarbeitung (keine API-Limits)
- Effiziente Tool-Auswahl
- Batch-Embedding-Generation
- Speicher-optimierte Vektoroperationen

## 🗄️ Datenbankschema

**Datenbankpfad:** `data/filecatalog.db`

### Haupttabellen
- `documents` - Haupttabelle für alle Dokumente
- `chunks` - Dokumentchunks für Embedding-basierte Suche
- `chunk_vectors` - Embedding-Vektoren (JSON-Format)
- `persons_fuzzy` - Fuzzy-Suche für Personennamen
- `places_fuzzy` - Fuzzy-Suche für Ortsnamen

### FTS5-Tabellen
- `documents_fts` - Haupt-FTS-Tabelle
- `documents_fts_extended` - Erweiterte FTS-Tabelle (Client-kompatibel)
- `documents_fts_*` - Automatisch generierte FTS5-Hilfstabellen

### Tabellenspezifikationen

#### 1. documents (Haupttabelle)
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    uuid TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT,
    size INTEGER,
    mime_type TEXT,
    md5_hash TEXT NOT NULL,
    original_text TEXT,
    markdown_content TEXT,
    summary TEXT,
    document_type TEXT,
    categories TEXT,
    entities TEXT,
    persons TEXT,
    places TEXT,
    mentioned_dates TEXT,
    file_references TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. chunks (Dokumentchunks)
```sql
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

#### 3. chunk_vectors (Embedding-Vektoren)
```sql
CREATE TABLE chunk_vectors (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    embedding_json TEXT NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);
```

#### 4. persons_fuzzy (Fuzzy-Personensuche)
```sql
CREATE TABLE persons_fuzzy (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    soundex_code TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Indizes für Performance
CREATE INDEX idx_persons_soundex ON persons_fuzzy(soundex_code);
CREATE INDEX idx_persons_normalized ON persons_fuzzy(normalized_name);
```

#### 5. places_fuzzy (Fuzzy-Ortssuche)
```sql
CREATE TABLE places_fuzzy (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL,
    original_place TEXT NOT NULL,
    soundex_code TEXT NOT NULL,
    normalized_place TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Indizes für Performance
CREATE INDEX idx_places_soundex ON places_fuzzy(soundex_code);
CREATE INDEX idx_places_normalized ON places_fuzzy(normalized_place);
```

#### 6. documents_fts (Haupt-FTS5-Tabelle)
```sql
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
    file_references, 
    tokenize='unicode61'
);
```

#### 7. documents_fts_extended (Erweiterte FTS5-Tabelle)
```sql
CREATE VIRTUAL TABLE documents_fts_extended USING fts5(
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
    mentioned_dates,
    tokenize='unicode61'
);
```

### FTS5 Automatische Synchronisation (Trigger)

Das System verwendet Trigger für automatische Synchronisation zwischen der Haupttabelle und den FTS5-Tabellen:

- **INSERT-Trigger**: Automatisches Hinzufügen neuer Dokumente zu FTS-Tabellen
- **UPDATE-Trigger**: Synchronisation bei Dokumentenänderungen
- **DELETE-Trigger**: Entfernung aus FTS-Tabellen bei Löschung

### MCP-Protokoll Integration

Die Datenbank wird über das **Model Context Protocol (MCP)** verwaltet:
- SQLite MCP Server für Datenbankoperationen
- Automatische Schema-Initialisierung
- Sichere Transaktionen über MCP-Client
- Kompatibilität mit MCP-Standards

## 🚀 Produktions-Status

✅ **READY FOR PRODUCTION** - Fokussierte Ingestion-Pipeline

- Erweiterte Extraktions-Tools integriert
- Ollama LLM-Integration funktional
- Robuste Fehlerbehandlung implementiert
- Tool-Verfügbarkeitsprüfung
- Umfassende Tests und Dokumentation

---

**Entwickelt als fokussierte Ingestion-Pipeline mit erweiterten Extraktions-Möglichkeiten und lokaler KI-Integration.**