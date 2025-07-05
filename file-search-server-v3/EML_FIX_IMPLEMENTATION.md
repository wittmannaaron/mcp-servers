# EML Processing Fix - Implementation Plan

## Issue Summary
EML files with attachments are not being properly cataloged. Only the EML file itself is stored in the database, while attachments are processed but not saved.

## Root Cause
After detailed analysis, the issue appears to be in the data flow between the email extractor and the ingestion pipeline. The attachments are being extracted and processed, but there's a mismatch in the data structure that prevents proper storage.

## Specific Problems Identified

### 1. Data Structure Mismatch
In `ingestion.py` line 196:
```python
'filename': attachment_data.get('attachment_filename', 'unknown'),
```
The code expects `attachment_filename` but the email extractor might not be providing this field correctly.

### 2. MD5 Hash Issue
Line 200 in `ingestion.py`:
```python
'md5_hash': attachment_data.get('md5_hash', ''),
```
The attachment data doesn't include an MD5 hash because it's not calculated for the attachment content.

### 3. Missing Size Information
The attachment is using the EML file's size instead of the actual attachment size.

## Proposed Solution

### Step 1: Update Email Extractor
Modify `src/extractors/email_extractor.py` to ensure proper data structure:

1. Add MD5 calculation for attachments
2. Ensure all required fields are present in the returned data
3. Add proper logging

### Step 2: Update Ingestion Pipeline
Modify `src/core/ingestion.py` to handle attachments correctly:

1. Fix the filename handling
2. Calculate proper sizes for attachments
3. Ensure all metadata is preserved

### Step 3: Add Validation
Add checks to ensure the correct number of documents are stored.

## Code Changes Required

### 1. Email Extractor (`email_extractor.py`)
```python
def _process_document(self, file_path: Path, original_eml_path: str, display_filename: str, email_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Process individual document file."""
    try:
        # Use existing document extractor
        processed_data = extract_and_preprocess(str(file_path))
        
        if "error" in processed_data:
            logger.error(f"Failed to extract content from {display_filename}: {processed_data['error']}")
            return None
        
        # Add email-specific metadata
        processed_data['email_metadata'] = email_metadata
        processed_data['original_eml_path'] = original_eml_path
        processed_data['attachment_filename'] = display_filename  # Ensure this is set
        processed_data['source_type'] = 'email_attachment'
        
        # Calculate MD5 for the attachment content
        if 'original_text' in processed_data:
            import hashlib
            processed_data['content_md5'] = hashlib.md5(
                processed_data['original_text'].encode()
            ).hexdigest()
        
        return processed_data
```

### 2. Ingestion Pipeline (`ingestion.py`)
Update the attachment processing section:

```python
# Process each attachment as a separate document
for attachment_data in processed_attachments:
    attachment_filename = attachment_data.get('attachment_filename', 'unknown')
    
    doc_data = {
        'file_path': str(file_path),  # Reference to original .eml file
        'filename': f"{file_path.name}#{attachment_filename}",  # Composite filename
        'extension': Path(attachment_filename).suffix.lower(),
        'size': len(attachment_data.get('original_text', '').encode()),  # Actual content size
        'mime_type': 'message/rfc822',  # Keep as EML mime type
        'md5_hash': attachment_data.get('content_md5', attachment_data.get('md5_hash', '')),
        'original_text': attachment_data.get('original_text', ''),
        'markdown_content': attachment_data.get('markdown_content', ''),
        'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
        'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
    }
```

## Testing Plan

1. Create test EML files with known attachments
2. Clear the database
3. Process the test files
4. Verify database entries:
   ```sql
   SELECT filename, file_path, source_type 
   FROM documents 
   WHERE file_path LIKE '%.eml%'
   ORDER BY id;
   ```

## Expected Results

For an EML file "test.eml" with 2 PDF attachments:
- Database should have 3 entries:
  1. `test.eml` (source_type: 'email_file')
  2. `test.eml#document1.pdf` (source_type: 'email_attachment')
  3. `test.eml#document2.pdf` (source_type: 'email_attachment')

All three entries should have `file_path` pointing to the original EML file location.

## Implementation Priority

1. **High Priority**: Fix the data structure mismatch (attachment_filename)
2. **Medium Priority**: Add proper MD5 and size calculation
3. **Low Priority**: Improve logging and validation

## Next Steps

1. Implement the changes in a feature branch
2. Test with sample EML files
3. Verify database integrity
4. Deploy to production