# EML Attachment Datenfluss Analyse

## Das Problem im Detail

Der Datenfluss für ein EML-Attachment sieht so aus:

1. **Email Extractor** (`email_extractor.py`):
   - Extrahiert Attachment in temporäres Verzeichnis (z.B. `/tmp/xyz/doc1.pdf`)
   - Ruft `extract_and_preprocess()` mit dem **temporären Pfad** auf
   - Fügt nach der Verarbeitung Metadaten hinzu:
     ```python
     processed_data['original_eml_path'] = original_eml_path  # z.B. "/path/to/email.eml"
     processed_data['attachment_filename'] = display_filename  # z.B. "doc1.pdf"
     ```

2. **Docling Extractor** (`docling_extractor.py`):
   - Erhält nur den temporären Pfad (`/tmp/xyz/doc1.pdf`)
   - Weiß nichts von der EML-Datei
   - Extrahiert Text und erstellt eigene Metadaten

3. **Ingestion Pipeline** (`ingestion.py`):
   - Erhält die verarbeiteten Daten zurück
   - Muss die EML-Informationen aus den Metadaten rekonstruieren

## Der kritische Punkt

In `ingestion.py` Zeile 195-196:
```python
doc_data = {
    'file_path': str(file_path),  # Das ist die EML-Datei - KORREKT!
    'filename': attachment_data.get('attachment_filename', 'unknown'),  # FALSCH!
```

Das Problem: `filename` sollte der EML-Dateiname sein, nicht der Attachment-Name!

## Die Lösung

### Änderung in `ingestion.py` (_handle_email_file Methode):

```python
# Für jedes Attachment
for attachment_data in processed_attachments:
    # Speichere den tatsächlichen Attachment-Namen für später
    actual_attachment_name = attachment_data.get('attachment_filename', 'unknown')
    
    doc_data = {
        'file_path': str(file_path),  # EML-Pfad - KORREKT
        'filename': file_path.name,    # EML-Dateiname statt Attachment-Name!
        'extension': file_path.suffix.lower(),  # .eml
        'size': file_stats.st_size,
        'mime_type': 'message/rfc822',
        'md5_hash': md5_hash,  # EML-Hash
        'original_text': attachment_data.get('original_text', ''),
        'markdown_content': attachment_data.get('markdown_content', ''),
        'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
        'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
    }
    
    # Füge email-spezifische Metadaten hinzu
    email_metadata = attachment_data.get('email_metadata', {})
    doc_data.update({
        'email_from': email_metadata.get('from', ''),
        'email_to': email_metadata.get('to', ''),
        'email_subject': email_metadata.get('subject', ''),
        'email_date': email_metadata.get('date', ''),
        'source_type': 'email_attachment'  # Wichtig für die Unterscheidung!
    })
```

## Wie die Information erhalten bleibt

1. **Email Extractor** speichert die EML-Info in den processed_data:
   - `original_eml_path`: Der Pfad zur EML-Datei
   - `attachment_filename`: Der Name des Attachments

2. **Ingestion Pipeline** nutzt diese Info:
   - Verwendet `file_path` (die EML-Datei) für DB-Speicherung
   - Verwendet `file_path.name` als Dateiname
   - Speichert den Attachment-Namen im AI-Metadata Summary

## Zusammenfassung

Der Schlüssel ist in der `_handle_email_file` Methode:
- Zeile 195: `'file_path': str(file_path),` ✅ (bereits korrekt)
- Zeile 196: `'filename': file_path.name,` ❌ (muss geändert werden von `attachment_data.get('attachment_filename')`)

Die Information über die EML-Datei ist bereits vorhanden und wird korrekt durchgereicht. Wir müssen nur sicherstellen, dass wir sie richtig verwenden!