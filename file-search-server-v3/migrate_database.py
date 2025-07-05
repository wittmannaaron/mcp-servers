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
    if not DB_FILE.exists():
        logger.warning(f"Database file not found at {DB_FILE}. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Check if backup table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_backup'")
        if cursor.fetchone():
            logger.warning("Backup table 'documents_backup' already exists. Cleaning up before migration.")
            cursor.execute("DROP TABLE documents_backup")

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
        logger.success("Migration completed successfully!")
        
        # Verify
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='documents'")
        schema = cursor.fetchone()[0]
        logger.info(f"New schema:\n{schema}")
        
    except sqlite3.OperationalError as e:
        if "no such column: source_type" in str(e):
             logger.warning("Column 'source_type' not found in original table. The migration might have been partially applied before. Retrying without it.")
             conn.rollback()
             # Retry without source_type in backup
             cursor.execute("BEGIN TRANSACTION")
             cursor.execute("""
                CREATE TABLE documents_backup AS 
                SELECT id, uuid, file_path, filename, extension, size, mime_type, 
                    md5_hash, original_text, markdown_content, summary, document_type,
                    categories, entities, persons, places, mentioned_dates, 
                    file_references, created_at, updated_at, indexed_at
                FROM documents
             """)
             cursor.execute("DROP TABLE documents")
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
             cursor.execute("INSERT INTO documents SELECT * FROM documents_backup")
             cursor.execute("DROP TABLE documents_backup")
             conn.commit()
             logger.success("Migration completed successfully on retry!")
        else:
            logger.error(f"Migration failed: {e}")
            conn.rollback()
            raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # Add a backup step before running the migration
    if DB_FILE.exists():
        backup_path = DB_FILE.with_suffix('.db.backup')
        logger.info(f"Creating a backup of the database at {backup_path}")
        import shutil
        shutil.copy(DB_FILE, backup_path)
    
    migrate_database()