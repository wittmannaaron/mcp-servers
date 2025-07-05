# EML Processing Analysis and Solution

## Current Problem

The system is not properly cataloging EML file attachments in the database. When an EML file contains attachments (e.g., 2 PDFs), only the EML file itself is being stored in the database, not the individual attachments.

### Expected Behavior
- 1 EML file with 2 attachments = 3 database entries:
  1. The EML file itself
  2. Attachment 1 (with file_path pointing to the EML file)
  3. Attachment 2 (with file_path pointing to the EML file)

### Current Behavior
- 1 EML file with 2 attachments = 1 database entry (only the EML file)

## Root Cause Analysis

### 1. Email Extractor (`src/extractors/email_extractor.py`)
The email extractor correctly:
- Extracts attachments from EML files
- Processes each attachment using Docling
- Returns both `eml_data` and `attachments` array

### 2. Ingestion Pipeline (`src/core/ingestion.py`)
The `_handle_email_file` method has the correct logic:
- Stores the EML file first
- Iterates through attachments and stores each one

However, there's a critical issue in the attachment storage logic:

```python
# Line 196-197: The filename is incorrectly set
'filename': attachment_data.get('attachment_filename', 'unknown'),
```

The attachment data doesn't have an `attachment_filename` key at this point. Looking at the email extractor, it sets this key during processing (line 211), but the key name might be getting lost or overwritten.

### 3. Database Storage Issue
The attachment documents are being created with:
- `file_path`: Correctly points to the EML file
- `filename`: Potentially incorrect (defaulting to 'unknown')
- Missing proper MD5 hash for attachments

## Solution Proposal

### 1. Fix the Email Extractor Return Structure
Ensure the attachment data structure is consistent and includes all necessary fields:

```python
# In email_extractor.py, _process_document method
processed_data['attachment_filename'] = display_filename
processed_data['md5_hash'] = self._calculate_attachment_md5(file_path)
```

### 2. Update Ingestion Pipeline
Fix the attachment processing in `_handle_email_file`:

```python
# Correct the filename extraction
'filename': f"{file_path.name}:{attachment_data.get('attachment_filename', 'unknown')}",
```

This creates a composite filename showing both the EML file and the attachment name.

### 3. Add Proper MD5 Calculation
Each attachment should have its own MD5 hash based on its content, not the EML file's hash.

### 4. Improve Logging
Add detailed logging to track:
- Number of attachments found
- Each attachment being processed
- Success/failure of each database insertion

## Implementation Steps

1. **Update `email_extractor.py`**:
   - Add MD5 calculation for each attachment
   - Ensure attachment_filename is properly set
   - Add logging for attachment extraction

2. **Update `ingestion.py`**:
   - Fix the filename field for attachments
   - Calculate proper MD5 for each attachment
   - Add detailed logging for debugging
   - Ensure all attachment metadata is preserved

3. **Add Validation**:
   - After processing an EML file, validate that the number of database entries equals 1 + number of attachments
   - Log warnings if the count doesn't match

## Testing Strategy

1. Create test EML files with known attachments
2. Process them through the pipeline
3. Query the database to verify:
   - Total count of entries
   - Each attachment has file_path pointing to the EML file
   - Each attachment has a unique filename and MD5 hash
   - Source_type is correctly set ('email_file' for EML, 'email_attachment' for attachments)

## Database Query for Verification

```sql
-- Check all entries for a specific EML file
SELECT id, filename, file_path, source_type, md5_hash 
FROM documents 
WHERE file_path LIKE '%Ihring._.Ihring 5.eml%';

-- Count entries by source type
SELECT source_type, COUNT(*) 
FROM documents 
GROUP BY source_type;