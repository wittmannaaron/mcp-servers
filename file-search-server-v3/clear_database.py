"""
Utility to clear the database file for a fresh start.
"""
import os
from pathlib import Path
from loguru import logger

DB_FILE = Path(__file__).parent / "data" / "filebrowser.db"

def clear_database_file():
    """Deletes the SQLite database file if it exists."""
    try:
        if DB_FILE.exists():
            os.remove(DB_FILE)
            logger.info(f"Successfully deleted existing database file: {DB_FILE}")
        else:
            logger.info("Database file not found, no action needed.")
    except Exception as e:
        logger.error(f"Error deleting database file: {e}")
        raise

if __name__ == "__main__":
    clear_database_file()
