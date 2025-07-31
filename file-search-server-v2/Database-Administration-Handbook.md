# Database Administration Handbook
## File Catalog - SQLite Database Management

### Inhaltsverzeichnis
1. [Datenbankübersicht](#datenbankübersicht)
2. [Tabellenspezifikationen](#tabellenspezifikationen)
3. [FTS5 Full-Text Search](#fts5-full-text-search)
4. [SQL-Kommando-Referenz](#sql-kommando-referenz)
5. [Wartung und Optimierung](#wartung-und-optimierung)
6. [Troubleshooting](#troubleshooting)

---

## Datenbankübersicht

**Datenbankpfad:** `/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db`

### Haupttabellen
- `documents` - Haupttabelle für alle Dokumente
- `chunks` - Dokumentchunks für Embedding-basierte Suche
- `chunk_vectors` - Embedding-Vektoren (JSON-Format)
- `persons_fuzzy` - Fuzzy-Suche für Personennamen
- `places_fuzzy` - Fuzzy-Suche für Ortsnamen

### FTS5-Tabellen
- `documents_fts` - Haupt-FTS-Tabelle für Volltextsuche

---

## Tabellenspezifikationen

### 1. documents (Haupttabelle)
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

### 2. chunks (Dokumentchunks)
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

### 3. chunk_vectors (Embedding-Vektoren)
```sql
CREATE TABLE chunk_vectors (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    embedding_json TEXT NOT NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);
```

### 4. persons_fuzzy (Fuzzy-Personensuche)
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

### 5. places_fuzzy (Fuzzy-Ortssuche)
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

### 6. documents_fts (Haupt-FTS5-Tabelle)
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

---

## FTS5 Full-Text Search

### Automatische Synchronisation (vereinfacht für file-catalog)

Da file-catalog sich nur auf Ingestion fokussiert, sind die FTS-Trigger vereinfacht:

#### INSERT-Trigger
```sql
CREATE TRIGGER documents_fts_insert
AFTER INSERT ON documents
BEGIN
    INSERT INTO documents_fts (rowid, original_text, markdown_content, summary, document_type, categories, entities, persons, places, mentioned_dates, file_references)
    VALUES (NEW.id, 
            COALESCE(NEW.original_text, ''), 
            COALESCE(NEW.markdown_content, ''), 
            COALESCE(NEW.summary, ''), 
            COALESCE(NEW.document_type, ''), 
            COALESCE(NEW.categories, ''), 
            COALESCE(NEW.entities, ''), 
            COALESCE(NEW.persons, ''), 
            COALESCE(NEW.places, ''), 
            COALESCE(NEW.mentioned_dates, ''), 
            COALESCE(NEW.file_references, ''));
END;
```

---

## SQL-Kommando-Referenz

### Datenbankverbindung
```bash
# Datenbankverbindung herstellen
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db
```

### Grundlegende Abfragen

#### Tabellenübersicht
```sql
-- Alle Tabellen anzeigen
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

-- Tabellenstruktur anzeigen
PRAGMA table_info(documents);
```

#### Dokumentanzahl prüfen
```sql
-- Anzahl Dokumente in Haupttabelle
SELECT COUNT(*) FROM documents;

-- Synchronisationsstatus prüfen
SELECT 
    'documents' as table_name, COUNT(*) as count FROM documents
UNION ALL
SELECT 
    'documents_fts' as table_name, COUNT(*) as count FROM documents_fts;
```

#### Extraktions-Tool-Analyse
```sql
-- Verwendete Extraktions-Tools analysieren
SELECT 
    CASE 
        WHEN original_text LIKE '%extraction_tool%' THEN 'Tool erkannt'
        ELSE 'Standard'
    END as extraction_method,
    extension,
    COUNT(*) as count
FROM documents 
GROUP BY extension, extraction_method
ORDER BY count DESC;

-- Dateitypen-Verteilung
SELECT extension, COUNT(*) as count 
FROM documents 
GROUP BY extension 
ORDER BY count DESC;
```

### Embeddings und Chunks analysieren

#### Chunk-Statistiken
```sql
-- Chunks pro Dokument
SELECT 
    d.filename,
    COUNT(c.id) as chunk_count,
    AVG(c.char_count) as avg_chunk_size
FROM documents d
LEFT JOIN chunks c ON d.id = c.document_id
GROUP BY d.id, d.filename
ORDER BY chunk_count DESC;

-- Embedding-Coverage prüfen
SELECT 
    'chunks' as table_name, COUNT(*) as count FROM chunks
UNION ALL
SELECT 
    'chunk_vectors' as table_name, COUNT(*) as count FROM chunk_vectors;
```

### FTS-Suche testen

#### Einfache Volltextsuche
```sql
-- Suche in allen Feldern
SELECT 
    d.filename,
    d.file_path,
    d.summary
FROM documents_fts fts
JOIN documents d ON d.id = fts.rowid
WHERE documents_fts MATCH 'suchbegriff'
LIMIT 5;
```

### Ollama LLM Metadaten analysieren

#### AI-Metadaten-Qualität prüfen
```sql
-- Dokumente mit AI-Metadaten
SELECT 
    document_type,
    COUNT(*) as count,
    AVG(LENGTH(summary)) as avg_summary_length
FROM documents 
WHERE summary IS NOT NULL AND summary != ''
GROUP BY document_type
ORDER BY count DESC;

-- Kategorien-Verteilung
SELECT 
    categories,
    COUNT(*) as count
FROM documents 
WHERE categories IS NOT NULL AND categories != '[]'
GROUP BY categories
ORDER BY count DESC
LIMIT 10;
```

---

## Wartung und Optimierung

### Regelmäßige Wartungsaufgaben

#### 1. FTS-Index optimieren
```sql
-- FTS-Index optimieren
INSERT INTO documents_fts(documents_fts) VALUES('optimize');
```

#### 2. Chunk-Embedding-Konsistenz prüfen
```sql
-- Prüfen ob alle Chunks Embeddings haben
SELECT 
    c.id as chunk_id,
    c.content,
    CASE WHEN cv.chunk_id IS NULL THEN 'Missing' ELSE 'Present' END as embedding_status
FROM chunks c
LEFT JOIN chunk_vectors cv ON c.id = cv.chunk_id
WHERE cv.chunk_id IS NULL;
```

#### 3. Datenbankgröße analysieren
```bash
# Dateigröße prüfen
ls -lh /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db
```

#### 4. Vacuum (Datenbankbereinigung)
```sql
-- Datenbankbereinigung (komprimiert die Datei)
VACUUM;
```

### Performance-Monitoring

#### Embedding-Performance analysieren
```sql
-- Durchschnittliche Embedding-Größe (JSON)
SELECT 
    AVG(LENGTH(embedding_json)) as avg_embedding_size,
    MIN(LENGTH(embedding_json)) as min_size,
    MAX(LENGTH(embedding_json)) as max_size
FROM chunk_vectors;
```

---

## Troubleshooting

### Häufige Probleme und Lösungen

#### 1. "no such table: documents_fts"
**Problem:** FTS-Tabelle existiert nicht
**Lösung:** FTS-Tabelle neu erstellen:
```sql
CREATE VIRTUAL TABLE documents_fts USING fts5(
    original_text, markdown_content, summary, document_type,
    categories, entities, persons, places, mentioned_dates,
    file_references, tokenize='unicode61'
);
```

#### 2. Chunk-Embedding-Mismatch
**Problem:** Ungleiche Anzahl Chunks vs. Embeddings
**Lösung:**
```sql
-- Problematische Chunks finden
SELECT c.id, c.document_id, c.content
FROM chunks c
LEFT JOIN chunk_vectors cv ON c.id = cv.chunk_id
WHERE cv.chunk_id IS NULL;
```

#### 3. Ollama-Integration-Probleme
**Problem:** Fehlende oder unvollständige AI-Metadaten
**Lösung:**
```sql
-- Dokumente ohne AI-Metadaten finden
SELECT filename, file_path
FROM documents 
WHERE summary IS NULL OR summary = '' OR summary = 'Dokument: ' || filename;
```

#### 4. Extraktions-Tool-Probleme
**Problem:** Dokumente mit Extraktionsfehlern
**Lösung:**
```sql
-- Dokumente mit wenig oder keinem Text finden
SELECT filename, extension, LENGTH(original_text) as text_length
FROM documents 
WHERE LENGTH(original_text) < 100
ORDER BY text_length;
```

### Tool-Verfügbarkeit prüfen

#### Extraktions-Tools testen
```bash
# Im file-catalog Verzeichnis
python full_ingestion_test.py --check-tools
```

#### Ollama-Status prüfen
```bash
# Ollama Service Status
curl -s http://localhost:11434/api/tags | jq '.'

# Verfügbare Modelle
ollama list
```

---

## Nützliche Befehle für file-catalog

```bash
# Schnelle Dokumentanzahl prüfen
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT COUNT(*) FROM documents;"

# Extraktions-Tool-Verteilung
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT extension, COUNT(*) FROM documents GROUP BY extension;"

# Embedding-Coverage prüfen
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT 'chunks', COUNT(*) FROM chunks UNION SELECT 'vectors', COUNT(*) FROM chunk_vectors;"

# FTS-Suche testen
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'test';"

# Tabellenübersicht
sqlite3 /Users/aaron/Projects/mcp-servers/file-catalog/data/filecatalog.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
```

---

**Erstellt:** 17. Juli 2025  
**Version:** 1.0 (file-catalog)  
**Fokus:** Reine Ingestion-Pipeline mit erweiterten Extraktions-Tools und Ollama-Integration