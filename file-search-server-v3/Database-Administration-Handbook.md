# Database Administration Handbook
## File Search Server v3 - SQLite Database Management

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
- `documents_fts` - Haupt-FTS-Tabelle
- `documents_fts_extended` - Erweiterte FTS-Tabelle (Client-kompatibel)
- `documents_fts_*` - Automatisch generierte FTS5-Hilfstabellen

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

### 7. documents_fts_extended (Erweiterte FTS5-Tabelle)
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

---

## FTS5 Full-Text Search

### Automatische Synchronisation (Trigger)

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
    
    INSERT INTO documents_fts_extended (rowid, filename, file_path, original_text, markdown_content, summary, document_type, categories, entities, persons, places, mentioned_dates)
    VALUES (NEW.id, 
            COALESCE(NEW.filename, ''),
            COALESCE(NEW.file_path, ''),
            COALESCE(NEW.original_text, ''), 
            COALESCE(NEW.markdown_content, ''), 
            COALESCE(NEW.summary, ''), 
            COALESCE(NEW.document_type, ''), 
            COALESCE(NEW.categories, ''), 
            COALESCE(NEW.entities, ''), 
            COALESCE(NEW.persons, ''), 
            COALESCE(NEW.places, ''), 
            COALESCE(NEW.mentioned_dates, ''));
END;
```

#### UPDATE-Trigger
```sql
CREATE TRIGGER documents_fts_update
AFTER UPDATE ON documents
BEGIN
    UPDATE documents_fts SET 
        original_text = COALESCE(NEW.original_text, ''),
        markdown_content = COALESCE(NEW.markdown_content, ''),
        summary = COALESCE(NEW.summary, ''),
        document_type = COALESCE(NEW.document_type, ''),
        categories = COALESCE(NEW.categories, ''),
        entities = COALESCE(NEW.entities, ''),
        persons = COALESCE(NEW.persons, ''),
        places = COALESCE(NEW.places, ''),
        mentioned_dates = COALESCE(NEW.mentioned_dates, ''),
        file_references = COALESCE(NEW.file_references, '')
    WHERE rowid = NEW.id;
    
    UPDATE documents_fts_extended SET 
        filename = COALESCE(NEW.filename, ''),
        file_path = COALESCE(NEW.file_path, ''),
        original_text = COALESCE(NEW.original_text, ''),
        markdown_content = COALESCE(NEW.markdown_content, ''),
        summary = COALESCE(NEW.summary, ''),
        document_type = COALESCE(NEW.document_type, ''),
        categories = COALESCE(NEW.categories, ''),
        entities = COALESCE(NEW.entities, ''),
        persons = COALESCE(NEW.persons, ''),
        places = COALESCE(NEW.places, ''),
        mentioned_dates = COALESCE(NEW.mentioned_dates, '')
    WHERE rowid = NEW.id;
END;
```

#### DELETE-Trigger
```sql
CREATE TRIGGER documents_fts_delete
AFTER DELETE ON documents
BEGIN
    DELETE FROM documents_fts WHERE rowid = OLD.id;
    DELETE FROM documents_fts_extended WHERE rowid = OLD.id;
END;
```

---

## SQL-Kommando-Referenz

### Datenbankverbindung
```bash
# Datenbankverbindung herstellen
sqlite3 /Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db
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
    'documents_fts' as table_name, COUNT(*) as count FROM documents_fts
UNION ALL
SELECT 
    'documents_fts_extended' as table_name, COUNT(*) as count FROM documents_fts_extended;
```

#### Trigger-Status prüfen
```sql
-- Alle Trigger anzeigen
SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name;
```

### FTS-Suche

#### Standard-Client-Query
```sql
-- Hauptsuchquery (wie vom Client verwendet)
SELECT 
    d.created_at,
    d.filename,
    d.file_path,
    SUBSTR(COALESCE(d.original_text, d.markdown_content, ''), 1, 200) as content_preview
FROM documents_fts_extended fts
JOIN documents d ON d.id = fts.rowid
WHERE documents_fts_extended MATCH ?
LIMIT 100;
```

#### Beispiel-Suchen
```sql
-- Suche nach spezifischem Begriff
SELECT 
    d.filename,
    d.file_path
FROM documents_fts_extended fts
JOIN documents d ON d.id = fts.rowid
WHERE documents_fts_extended MATCH 'Kreissparkasse'
LIMIT 5;

-- Suche in bestimmten Feldern
SELECT 
    d.filename,
    d.file_path
FROM documents_fts_extended fts
JOIN documents d ON d.id = fts.rowid
WHERE documents_fts_extended MATCH 'filename:pdf'
LIMIT 5;
```

### Wartung und Synchronisation

#### FTS-Tabellen leeren
```sql
-- FTS-Tabellen komplett leeren
DELETE FROM documents_fts;
DELETE FROM documents_fts_extended;
```

#### FTS-Tabellen neu befüllen
```sql
-- documents_fts neu befüllen
INSERT INTO documents_fts (rowid, original_text, markdown_content, summary, document_type, categories, entities, persons, places, mentioned_dates, file_references)
SELECT id, 
       COALESCE(original_text, ''), 
       COALESCE(markdown_content, ''), 
       COALESCE(summary, ''), 
       COALESCE(document_type, ''), 
       COALESCE(categories, ''), 
       COALESCE(entities, ''), 
       COALESCE(persons, ''), 
       COALESCE(places, ''), 
       COALESCE(mentioned_dates, ''), 
       COALESCE(file_references, '')
FROM documents;

-- documents_fts_extended neu befüllen
INSERT INTO documents_fts_extended (rowid, filename, file_path, original_text, markdown_content, summary, document_type, categories, entities, persons, places, mentioned_dates)
SELECT id, 
       COALESCE(filename, ''),
       COALESCE(file_path, ''),
       COALESCE(original_text, ''), 
       COALESCE(markdown_content, ''), 
       COALESCE(summary, ''), 
       COALESCE(document_type, ''), 
       COALESCE(categories, ''), 
       COALESCE(entities, ''), 
       COALESCE(persons, ''), 
       COALESCE(places, ''), 
       COALESCE(mentioned_dates, '')
FROM documents;
```

#### Nicht benötigte Tabellen entfernen
```sql
-- Tabelle löschen (falls nicht mehr benötigt)
DROP TABLE IF EXISTS ai_strategies;
```

### Datenanalyse

#### Beispieldokumente anzeigen
```sql
-- Erste 5 Dokumente mit Metadaten
SELECT id, filename, file_path, 
       LENGTH(COALESCE(original_text, '')) as text_length 
FROM documents 
LIMIT 5;

-- Dokumente nach Dateityp
SELECT extension, COUNT(*) as count 
FROM documents 
GROUP BY extension 
ORDER BY count DESC;
```

#### FTS-Performance testen
```sql
-- Einfache Suche testen
SELECT COUNT(*) 
FROM documents_fts_extended 
WHERE documents_fts_extended MATCH 'test';

-- Komplexe Suche testen
SELECT 
    d.filename,
    snippet(documents_fts_extended, 2, '<b>', '</b>', '...', 32) as snippet
FROM documents_fts_extended fts
JOIN documents d ON d.id = fts.rowid
WHERE documents_fts_extended MATCH 'Sparkasse OR Bank'
LIMIT 10;
```

---

## Wartung und Optimierung

### Regelmäßige Wartungsaufgaben

#### 1. FTS-Index optimieren
```sql
-- FTS-Index optimieren (sollte regelmäßig ausgeführt werden)
INSERT INTO documents_fts(documents_fts) VALUES('optimize');
INSERT INTO documents_fts_extended(documents_fts_extended) VALUES('optimize');
```

#### 2. Datenbankgröße prüfen
```bash
# Dateigröße prüfen
ls -lh /Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db
```

#### 3. Vacuum (Datenbankbereinigung)
```sql
-- Datenbankbereinigung (komprimiert die Datei)
VACUUM;
```

#### 4. Statistiken aktualisieren
```sql
-- Datenbankstatistiken aktualisieren
ANALYZE;
```

### Performance-Monitoring

#### Abfrage-Performance messen
```sql
-- Query-Plan anzeigen
EXPLAIN QUERY PLAN 
SELECT d.filename 
FROM documents_fts_extended fts
JOIN documents d ON d.id = fts.rowid
WHERE documents_fts_extended MATCH 'test';
```

---

## Troubleshooting

### Häufige Probleme und Lösungen

#### 1. "no such table: documents_fts_extended"
**Problem:** FTS-Tabelle existiert nicht
**Lösung:** FTS-Tabellen neu erstellen (siehe Tabellenspezifikationen)

#### 2. Synchronisationsprobleme
**Problem:** Unterschiedliche Anzahl Einträge in documents vs. FTS-Tabellen
**Lösung:** 
```sql
-- Synchronisation prüfen
SELECT 
    'documents' as table_name, COUNT(*) as count FROM documents
UNION ALL
SELECT 
    'documents_fts_extended' as table_name, COUNT(*) as count FROM documents_fts_extended;

-- Bei Abweichungen: FTS-Tabellen neu befüllen (siehe Wartung)
```

#### 3. Trigger funktionieren nicht
**Problem:** Neue Dokumente werden nicht automatisch in FTS-Tabellen eingefügt
**Lösung:**
```sql
-- Trigger-Status prüfen
SELECT name FROM sqlite_master WHERE type='trigger';

-- Falls Trigger fehlen: Trigger neu erstellen (siehe FTS5-Sektion)
```

#### 4. Langsame Suche
**Problem:** FTS-Suche ist langsam
**Lösung:**
```sql
-- FTS-Index optimieren
INSERT INTO documents_fts_extended(documents_fts_extended) VALUES('optimize');

-- Datenbankstatistiken aktualisieren
ANALYZE;
```

### Notfall-Wiederherstellung

#### Backup wiederherstellen
```bash
# Backup-Datei verwenden
cp /Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db_bak \
   /Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db
```

#### Komplette FTS-Neuinitialisierung
```sql
-- 1. Alte FTS-Tabellen löschen
DROP TABLE IF EXISTS documents_fts;
DROP TABLE IF EXISTS documents_fts_extended;

-- 2. FTS-Tabellen neu erstellen (siehe Tabellenspezifikationen)
-- 3. Trigger neu erstellen (siehe FTS5-Sektion)
-- 4. Daten neu befüllen (siehe Wartung)
```

---

## Nützliche Befehle für schnelle Tests

```bash
# Schnelle Dokumentanzahl prüfen
sqlite3 /Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db "SELECT COUNT(*) FROM documents;"

# Schnelle FTS-Suche testen
sqlite3 /Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db "SELECT COUNT(*) FROM documents_fts_extended WHERE documents_fts_extended MATCH 'test';"

# Trigger-Status schnell prüfen
sqlite3 /Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db "SELECT name FROM sqlite_master WHERE type='trigger';"

# Tabellenübersicht
sqlite3 /Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
```

---

**Erstellt:** 6. Juli 2025  
**Version:** 1.0  
**Letzte Aktualisierung:** Nach FTS5-Optimierung