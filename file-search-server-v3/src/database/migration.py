"""
Database migration script to update schema according to user requirements.
Adds missing fields and ensures compatibility with existing data.
"""

import sqlite3
import json
from pathlib import Path
from loguru import logger

DB_FILE = Path(__file__).parent / "filebrowser.db"

def migrate_database():
    """
    Migrate database to include all required fields according to user specifications:
    - UUID (already exists)
    - MD5 hash (already exists)
    - File path, filename (path exists, need to extract filename)
    - Creation/modification dates (already exist)
    - Markdown content reference (already exists)
    - Meta information: summary, categories, persons, places, dates, file references
    """

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        logger.info("Starting database migration...")

        # Check current schema
        cursor.execute("PRAGMA table_info(documents)")
        current_columns = {row[1] for row in cursor.fetchall()}
        logger.info(f"Current columns: {current_columns}")

        # Add missing columns
        migrations = []

        if 'filename' not in current_columns:
            migrations.append("ALTER TABLE documents ADD COLUMN filename TEXT")

        if 'extension' not in current_columns:
            migrations.append("ALTER TABLE documents ADD COLUMN extension TEXT")

        if 'persons' not in current_columns:
            migrations.append("ALTER TABLE documents ADD COLUMN persons TEXT")  # JSON array

        if 'places' not in current_columns:
            migrations.append("ALTER TABLE documents ADD COLUMN places TEXT")  # JSON array

        if 'mentioned_dates' not in current_columns:
            migrations.append("ALTER TABLE documents ADD COLUMN mentioned_dates TEXT")  # JSON array

        if 'file_references' not in current_columns:
            migrations.append("ALTER TABLE documents ADD COLUMN file_references TEXT")  # JSON array

        if 'document_type' not in current_columns:
            migrations.append("ALTER TABLE documents ADD COLUMN document_type TEXT")  # email, Behörde, Steuer, etc.

        # Execute migrations
        for migration in migrations:
            logger.info(f"Executing: {migration}")
            cursor.execute(migration)

        # Update existing records to populate filename and extension
        cursor.execute("SELECT id, file_path FROM documents WHERE filename IS NULL OR filename = ''")
        records = cursor.fetchall()

        for doc_id, file_path in records:
            if file_path:
                path = Path(file_path)
                filename = path.name
                extension = path.suffix.lower()

                cursor.execute(
                    "UPDATE documents SET filename = ?, extension = ? WHERE id = ?",
                    (filename, extension, doc_id)
                )
                logger.debug(f"Updated document {doc_id}: filename={filename}, extension={extension}")

        # Update FTS table to include new searchable fields
        logger.info("Updating FTS table...")
        cursor.execute("DROP TABLE IF EXISTS documents_fts")
        cursor.execute("""
            CREATE VIRTUAL TABLE documents_fts USING fts5(
                content,
                markdown_content,
                summary,
                categories,
                entities,
                persons,
                places,
                document_type,
                tokenize='unicode61'
            )
        """)

        # Repopulate FTS table
        cursor.execute("""
            INSERT INTO documents_fts (rowid, content, markdown_content, summary, categories, entities, persons, places, document_type)
            SELECT id, content, markdown_content, summary, categories, entities, persons, places, document_type
            FROM documents
        """)

        conn.commit()
        logger.info("Database migration completed successfully!")

        # Show final schema
        cursor.execute("PRAGMA table_info(documents)")
        final_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"Final columns: {final_columns}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def verify_migration():
    """Verify the migration was successful."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Check all required columns exist
        cursor.execute("PRAGMA table_info(documents)")
        columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            'id', 'uuid', 'file_path', 'filename', 'extension', 'md5_hash',
            'mime_type', 'created_at', 'modified_at', 'indexed_at', 'file_size',
            'content', 'markdown_content', 'summary', 'categories', 'entities',
            'persons', 'places', 'mentioned_dates', 'file_references', 'document_type'
        }

        missing = required_columns - columns
        if missing:
            logger.error(f"Missing columns after migration: {missing}")
            return False

        logger.info("✅ All required columns present")

        # Check FTS table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents_fts'")
        if not cursor.fetchone():
            logger.error("❌ FTS table missing")
            return False

        logger.info("✅ FTS table present")

        # Check data integrity
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents_fts")
        fts_count = cursor.fetchone()[0]

        if doc_count != fts_count:
            logger.warning(f"Document count mismatch: documents={doc_count}, fts={fts_count}")
        else:
            logger.info(f"✅ Data integrity verified: {doc_count} documents")

        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
    verify_migration()