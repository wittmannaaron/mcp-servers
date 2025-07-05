# Database Migration Steps - Remove UNIQUE Constraint

## Sofortige Änderungen in src/database/database.py

### 1. Entfernen Sie die UNIQUE Constraint von file_path (Zeile 32)
```python
# ALT (Zeile 32):
file_path TEXT UNIQUE NOT NULL,

# NEU (Zeile 32):
file_path TEXT NOT NULL,
```

### 2. Entfernen Sie die source_type Spalte (Zeile 42)
Diese Zeile wurde fälschlicherweise hinzugefügt und sollte komplett entfernt werden:
```python
# ENTFERNEN (Zeile 42):
source_type TEXT,
```

### 3. Aktualisieren Sie die INSERT-Anweisung (Zeilen 76-82)
Entfernen Sie `source_type` aus der INSERT-Anweisung:

```python
# ALT (Zeilen 76-82):
insert_query = """
    INSERT OR REPLACE INTO documents
    (uuid, file_path, filename, extension, size, mime_type, md5_hash,
     original_text, markdown_content, summary, document_type, source_type, categories, entities,
     persons, places, mentioned_dates, file_references, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# NEU (Zeilen 76-82):
insert_query = """
    INSERT OR REPLACE INTO documents
    (uuid, file_path, filename, extension, size, mime_type, md5_hash,
     original_text, markdown_content, summary, document_type, categories, entities,
     persons, places, mentioned_dates, file_references, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""
```

### 4. Aktualisieren Sie die Parameter-Liste (Zeilen 83-92)
Entfernen Sie den source_type Parameter:

```python
# ALT (Zeile 87):
ai_metadata.get('summary'), ai_metadata.get('document_type'), doc_data.get('source_type'),

# NEU (Zeile 87):
ai_metadata.get('summary'), ai_metadata.get('document_type'),
```

## Migration für existierende Datenbank

Erstellen Sie eine neue Datei `migrate_database.py`:

```python
#!/usr/bin/env python3
"""
Migrate database to remove UNIQUE constraint from file_path
and remove source_type column.
"""
import sqlite3
from pathlib import Path
from loguru import logger

DB_FILE = Path(__file__).parent / "src/database/filebrowser.db"

def migrate_database():
    """Remove UNIQUE constraint from file_path column."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Create backup table
        logger.info("Creating backup of documents table...")
        cursor.execute("""
            CREATE TABLE documents_backup AS 
            SELECT id, uuid, file_path, filename, extension, size, mime_type, 
                   md5_hash, original_text, markdown_content, summary, document_type,
                   categories, entities, persons, places, mentioned_dates, 
                   file_references, created_at, updated_at, indexed_at
            FROM documents
        """)
        
        # Drop old table
        logger.info("Dropping old documents table...")
        cursor.execute("DROP TABLE documents")
        
        # Create new table without UNIQUE on file_path and without source_type
        logger.info("Creating new documents table without UNIQUE constraint...")
        cursor.execute("""
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
            )
        """)
        
        # Copy data back
        logger.info("Copying data back to new table...")
        cursor.execute("""
            INSERT INTO documents 
            SELECT * FROM documents_backup
        """)
        
        # Drop backup table
        logger.info("Dropping backup table...")
        cursor.execute("DROP TABLE documents_backup")
        
        # Commit transaction
        conn.commit()
        logger.info("Migration completed successfully!")
        
        # Verify
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='documents'")
        schema = cursor.fetchone()[0]
        logger.info(f"New schema:\n{schema}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
```

## Ausführungsreihenfolge

1. **Stoppen Sie alle laufenden Prozesse**, die die Datenbank verwenden
2. **Backup erstellen**: `cp src/database/filebrowser.db src/database/filebrowser.db.backup`
3. **Migration ausführen**: `python migrate_database.py`
4. **Code-Änderungen** in `src/database/database.py` durchführen (siehe oben)
5. **Testen** mit `python eml_ingestion_test.py`

## Erwartetes Ergebnis

Nach der Migration sollte die Datenbank mehrere Einträge für dieselbe EML-Datei speichern können:

```sql
-- Test-Query
SELECT COUNT(*) as entries, file_path 
FROM documents 
GROUP BY file_path 
HAVING COUNT(*) > 1;
```

Dies sollte EML-Dateien mit ihren Attachments zeigen, alle mit demselben `file_path`.