# Email Processing Pipeline Tests

This directory contains comprehensive tests for the email processing functionality.

## Test Scripts

### 1. `test_email_only.py`
Simple test that processes .eml files and shows extracted attachments without database operations.

**Usage:**
```bash
cd tests
python test_email_only.py
```

**Output:**
- List of all .eml files processed
- Number of attachments found per file
- Content previews of extracted documents
- Summary of ZIP file contents

### 2. `test_database_storage.py`
Tests the complete pipeline including database storage of processed email attachments.

**Usage:**
```bash
cd tests
python test_database_storage.py
```

**Output:**
- Creates `../data/test_email_processing.db`
- Stores extracted email attachments in database
- Shows stored records with search examples

### 3. `test_email_processing.py`
Comprehensive test that processes both .eml and .zip files through the full ingestion pipeline.

**Usage:**
```bash
cd tests
python test_email_processing.py
```

**Output:**
- `test_results.json` - Detailed JSON results
- `test_summary.txt` - Human-readable summary

### 4. `query_database.py`
Demonstrates how to query the email processing database.

**Usage:**
```bash
cd tests
python query_database.py
```

**Features:**
- Shows database statistics
- Lists all stored documents
- Example searches by content, sender, file type
- MCP query examples

## Test Data

The tests use email files from: `/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958/`

### Email Files Tested:
- `Ihring ._. Ihring.eml` - Contains 1 PDF attachment (legal document)
- `Ihring ._. Ihring, 3 F 248_24 (Strreitwert).eml` - Contains 1 PDF attachment (court decision)
- 6 other .eml files - No document attachments found

### ZIP Files Tested:
- `Polizeiliche Mitteilung.zip` - 4 PDF documents (police reports)
- `Beschluss 3 F 893:23.zip` - 3 PDF documents (court decisions)
- `Terminmitteilung 3 F 89323.zip` - 2 PDF documents (court notifications)
- `Gerichtstermin elterliche Sorge.zip` - 2 PDF documents (court appointments)
- `Amtsgericht Esslingen 3 F 893:23.zip` - 4 PDF documents (court files)

## Database Schema

The tests create an `email_documents` table with:

```sql
CREATE TABLE email_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    eml_file_path TEXT NOT NULL,
    attachment_filename TEXT,
    content_text TEXT,
    email_from TEXT,
    email_to TEXT,
    email_subject TEXT,
    email_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Search Examples

After running the tests, you can search the database:

```bash
# Open database directly
sqlite3 ../data/test_email_processing.db

# Example queries
SELECT * FROM email_documents WHERE content_text LIKE '%court%';
SELECT COUNT(*), email_from FROM email_documents GROUP BY email_from;
SELECT attachment_filename FROM email_documents WHERE email_subject LIKE '%Ihring%';
```

## Test Results Summary

**Email Processing:**
- ✅ 8 .eml files processed
- ✅ 2 files with attachments found
- ✅ 2 PDF attachments extracted and processed
- ✅ Email metadata preserved (from, to, subject, date)
- ✅ Content extraction working (4,216 and 3,312 characters)

**ZIP Processing:**
- ✅ 5 .zip files processed  
- ✅ 15 PDF documents found and processed
- ✅ Temporary extraction and cleanup working
- ✅ Recursive directory processing working
- ✅ MacOS metadata files (._*) properly ignored

**Database Storage:**
- ✅ SQLite database creation working
- ✅ Document insertion working
- ✅ Search functionality working
- ✅ Email metadata properly stored
- ✅ Content indexing for full-text search

## Integration with Main Pipeline

The email processing is integrated into the main ingestion pipeline in `src/core/ingestion.py`:

1. **File Detection**: `.eml` files are detected by extension
2. **Email Processing**: Routed to `_handle_email_file()` method
3. **Attachment Extraction**: Each attachment processed as separate document
4. **Database Storage**: Stored with reference to original .eml file
5. **MCP Integration**: Uses MCP protocol for database operations

## Known Issues

1. **MCP Connection**: Some tests fall back to direct SQLite due to MCP server connection issues
2. **MacOS Metadata**: `._*` files in ZIP archives cause processing warnings (expected behavior)
3. **Large Files**: Some .eml files are large but contain no extractable attachments

## Future Enhancements

1. **Email Body Processing**: Currently only processes attachments, could also index email body text
2. **Inline Images**: Could extract and process inline images from emails
3. **Nested ZIP Files**: Could add support for ZIP files within ZIP files
4. **Chunking**: Integration with planned chunking and embedding pipeline