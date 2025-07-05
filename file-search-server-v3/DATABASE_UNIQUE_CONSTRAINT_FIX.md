# Database UNIQUE Constraint Fix für EML/Archive Processing

## Problem
Die aktuelle Datenbankstruktur hat eine `UNIQUE` Constraint auf der `file_path` Spalte, was verhindert, dass mehrere Einträge für dieselbe Datei gespeichert werden können. Dies ist problematisch für:
- EML-Dateien mit Attachments
- ZIP-Archive mit mehreren Dokumenten
- Andere Container-Formate

## Lösung
Entfernen der `UNIQUE` Constraint von `file_path`. Nur `uuid` sollte UNIQUE bleiben.

## Erforderliche Änderungen

### 1. Database Schema Update
In `src/database/database.py`, Zeile 32:
```sql
-- ALT:
file_path TEXT UNIQUE NOT NULL,

-- NEU:
file_path TEXT NOT NULL,
```

### 2. Migration Script
Da die Datenbank bereits existiert, benötigen wir ein Migrations-Script:

```sql
-- Backup der existierenden Daten
CREATE TABLE documents_backup AS SELECT * FROM documents;

-- Lösche die alte Tabelle
DROP TABLE documents;

-- Erstelle neue Tabelle ohne UNIQUE constraint auf file_path
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

-- Kopiere Daten zurück
INSERT INTO documents SELECT * FROM documents_backup;

-- Lösche Backup
DROP TABLE documents_backup;
```

## Auswirkungen

### Positive Effekte:
1. **EML-Verarbeitung funktioniert**: Eine EML-Datei mit 2 Attachments erzeugt 3 Einträge
2. **ZIP-Verarbeitung funktioniert**: Ein ZIP mit 10 Dokumenten erzeugt 11 Einträge
3. **Korrekte Dateiverwaltung**: Alle Einträge zeigen auf die Container-Datei

### Unterscheidung der Einträge:
- **UUID**: Jeder Eintrag hat eine eindeutige UUID
- **MD5-Hash**: Unterschiedlicher Content = unterschiedlicher Hash
- **Content**: `original_text` und `markdown_content` sind unterschiedlich
- **Summary**: Beschreibt den spezifischen Inhalt
- **Document Type**: Unterscheidet zwischen Email/PDF/etc.

## Test-Szenario

Für "Ihring._.Ihring 5.eml" mit 2 PDF-Attachments:

```sql
SELECT id, uuid, filename, md5_hash, document_type, LENGTH(original_text) as text_len
FROM documents 
WHERE file_path LIKE '%Ihring._.Ihring 5.eml%';
```

Erwartetes Ergebnis:
```
id | uuid     | filename              | md5_hash | document_type | text_len
---+----------+-----------------------+----------+---------------+---------
1  | uuid-001 | Ihring._.Ihring 5.eml | hash-eml | email         | 500
2  | uuid-002 | Ihring._.Ihring 5.eml | hash-pd1 | pdf           | 2000  
3  | uuid-003 | Ihring._.Ihring 5.eml | hash-pd2 | pdf           | 3000
```

## Implementierung ohne source_type

Da wir kein `source_type` Feld hinzufügen, nutzen wir vorhandene Felder:
- **document_type**: Zeigt den tatsächlichen Dokumenttyp (email, pdf, etc.)
- **summary**: Enthält kontextuelle Information ("Email from...", "Attachment 'doc.pdf' from...")
- **md5_hash**: Eindeutig für jeden unterschiedlichen Inhalt