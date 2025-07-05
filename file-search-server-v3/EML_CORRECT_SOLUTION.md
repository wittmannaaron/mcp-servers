# Korrekte Lösung für EML-Datei Verarbeitung

## Anforderungen (vom Benutzer bestätigt)

1. **Dateiname in DB**: Muss immer der EML-Dateiname sein (z.B. "Ihring._.Ihring 5.eml")
2. **Dateipfad in DB**: Muss immer auf die EML-Datei zeigen
3. **Email Summary**: Muss die Liste der Attachments enthalten
4. **Attachment-Unterscheidung**: Erfolgt über andere Felder, nicht über Dateiname

## Implementierungsstrategie

### 1. Datenbank-Schema Anpassung
Wir nutzen vorhandene Felder kreativ:
- `filename`: Immer der EML-Dateiname
- `file_path`: Immer der Pfad zur EML-Datei
- `source_type`: Unterscheidet zwischen 'email_file' und 'email_attachment'
- `summary`: Enthält bei EML die Attachment-Liste, bei Attachments deren Inhalt
- Neues virtuelles Feld oder Nutzung eines vorhandenen Feldes für den tatsächlichen Attachment-Namen

### 2. Email-Extraktor Anpassung

```python
def _create_email_summary(self, email_metadata: dict, email_body: str, attachment_list: list) -> str:
    """Create a comprehensive summary for an email file including body and attachments."""
    sender = email_metadata.get('from', 'Unknown sender')
    recipient = email_metadata.get('to', 'Unknown recipient')
    subject = email_metadata.get('subject', 'No subject')
    
    summary = f"Email from {sender} to {recipient}\n"
    summary += f"Subject: {subject}\n\n"
    
    # Add email body preview (first 200 chars)
    if email_body:
        body_preview = email_body[:200].strip()
        if len(email_body) > 200:
            body_preview += "..."
        summary += f"Message: {body_preview}\n\n"
    
    # Add attachment information
    if attachment_list:
        summary += f"Attachments ({len(attachment_list)}):\n"
        for att in attachment_list:
            summary += f"  - {att}\n"
    else:
        summary += "No attachments\n"
    
    return summary
```

### 3. Ingestion Pipeline Anpassung

```python
# Für EML-Datei selbst
eml_doc_data = {
    'file_path': str(file_path),
    'filename': file_path.name,  # z.B. "Ihring._.Ihring 5.eml"
    'extension': file_path.suffix.lower(),
    'size': file_stats.st_size,
    'mime_type': 'message/rfc822',
    'md5_hash': md5_hash,
    'original_text': eml_data.get('email_body', ''),
    'markdown_content': eml_data.get('email_body', ''),
    'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
    'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
    'source_type': 'email_file'
}

# AI-Metadata mit erweitertem Summary
ai_metadata['summary'] = self._create_email_summary(
    email_metadata, 
    eml_data.get('email_body', ''),
    attachment_list
)

# Für jedes Attachment
for attachment_data in processed_attachments:
    actual_attachment_name = attachment_data.get('attachment_filename', 'unknown')
    
    doc_data = {
        'file_path': str(file_path),  # Zeigt auf EML-Datei
        'filename': file_path.name,    # EML-Dateiname!
        'extension': file_path.suffix.lower(),  # .eml
        'size': file_stats.st_size,    # EML-Dateigröße
        'mime_type': 'message/rfc822',
        'md5_hash': md5_hash,          # EML-Hash
        'original_text': attachment_data.get('original_text', ''),
        'markdown_content': attachment_data.get('markdown_content', ''),
        'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
        'updated_at': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
        'source_type': 'email_attachment'
    }
    
    # Speichere den tatsächlichen Attachment-Namen im document_type oder einem anderen Feld
    # Option 1: Nutze document_type
    ai_metadata['document_type'] = f"Email Attachment: {actual_attachment_name}"
    
    # Option 2: Erweitere das Summary
    ai_metadata['summary'] = f"Attachment '{actual_attachment_name}' from email {file_path.name}. Content: {ai_metadata.get('summary', '')}"
```

### 4. Suchfunktionalität

Bei der Suche können wir dann:
1. Nach Email-Inhalten suchen (findet EML + alle Attachments)
2. Nach spezifischen Attachment-Inhalten suchen
3. Über `source_type` filtern

### 5. ZIP-Dateien (gleiche Strategie)

Für ZIP-Dateien verwenden wir das gleiche Prinzip:
- `filename`: Immer der ZIP-Dateiname
- `file_path`: Immer der Pfad zur ZIP-Datei
- `source_type`: 'zip_file' oder 'zip_content'
- `summary`: Bei ZIP enthält Dateiliste, bei Inhalten deren Text

## Vorteile dieser Lösung

1. **Korrekte Anwendungsöffnung**: Email-Client öffnet sich für alle Email-bezogenen Einträge
2. **Vollständige Durchsuchbarkeit**: Alle Inhalte sind im Katalog
3. **Klare Unterscheidung**: Über `source_type` wissen wir, was was ist
4. **Konsistente Implementierung**: Gleiche Logik für EML, ZIP und andere Archive

## Datenbank-Abfragen

```sql
-- Alle Einträge für eine EML-Datei
SELECT id, filename, source_type, summary 
FROM documents 
WHERE file_path = '/path/to/Ihring._.Ihring 5.eml'
ORDER BY source_type, id;

-- Nur Email-Dateien (ohne Attachments)
SELECT * FROM documents WHERE source_type = 'email_file';

-- Nur Email-Attachments
SELECT * FROM documents WHERE source_type = 'email_attachment';
```

## Erwartetes Ergebnis

Für "Ihring._.Ihring 5.eml" mit 2 PDFs:
```
ID | filename              | source_type      | summary
---+----------------------+-----------------+----------------------------------
1  | Ihring._.Ihring 5.eml | email_file      | Email from X to Y. Attachments: doc1.pdf, doc2.pdf
2  | Ihring._.Ihring 5.eml | email_attachment | Attachment 'doc1.pdf' from email...
3  | Ihring._.Ihring 5.eml | email_attachment | Attachment 'doc2.pdf' from email...
```

Alle drei Einträge haben denselben Dateinamen und Pfad, aber unterschiedliche Inhalte und source_type.