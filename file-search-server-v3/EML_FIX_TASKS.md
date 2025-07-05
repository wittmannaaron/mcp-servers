# EML Attachment Processing Fix - Task List

## Übersicht
Die EML-Datei-Verarbeitung speichert Attachments nicht korrekt in der Datenbank. Attachments müssen mit dem EML-Dateinamen gespeichert werden, damit das Email-Programm korrekt geöffnet wird.

## Tasks

### Task 1: Fix Attachment Filename in Ingestion Pipeline
**Priorität**: Hoch  
**Datei**: `src/core/ingestion.py`  
**Methode**: `_handle_email_file`  
**Zeile**: ~196  

**Änderung**:
```python
# ALT (FALSCH):
'filename': attachment_data.get('attachment_filename', 'unknown'),

# NEU (KORREKT):
'filename': file_path.name,  # Verwende EML-Dateiname statt Attachment-Name
```

**Kontext**: Der Attachment-Name soll im Summary gespeichert werden, nicht als Dateiname.

---

### Task 2: Update Email Summary Creation
**Priorität**: Mittel  
**Datei**: `src/core/ingestion.py`  
**Methode**: `_create_email_summary`  
**Zeile**: ~351  

**Änderung**: Erweitere die Summary-Erstellung um Email-Body Preview:
```python
def _create_email_summary(self, email_metadata: dict, email_body: str, attachment_list: list) -> str:
    """Create a summary for an email file including body preview."""
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
    
    if attachment_list:
        summary += f"Attachments ({len(attachment_list)}):\n"
        for att in attachment_list:
            summary += f"  - {att}\n"
    else:
        summary += "No attachments\n"
    
    return summary
```

**Aufruf anpassen** (Zeile ~149):
```python
email_summary = self._create_email_summary(
    email_metadata, 
    eml_data.get('email_body', ''),  # NEU: Email-Body hinzufügen
    attachment_list
)
```

---

### Task 3: Fix Attachment Summary
**Priorität**: Mittel  
**Datei**: `src/core/ingestion.py`  
**Methode**: `_handle_email_file`  
**Zeile**: ~227  

**Änderung**: Attachment-Name im Summary erwähnen:
```python
# Erweitere das Summary für Attachments
attachment_name = attachment_data.get('attachment_filename', 'unknown')
original_summary = ai_metadata.get('summary', '')
ai_metadata['summary'] = f"Attachment '{attachment_name}' from email {file_path.name}. Content: {original_summary}"
```

---

### Task 4: Add Logging for Debugging
**Priorität**: Niedrig  
**Datei**: `src/core/ingestion.py`  
**Methode**: `_handle_email_file`  

**Hinzufügen nach Zeile 136**:
```python
logger.info(f"Processing EML file with {len(processed_attachments)} attachments")
```

**Hinzufügen nach Zeile 233**:
```python
logger.info(f"Stored attachment '{doc_data['filename']}' with ID {doc_id}")
```

---

## Test-Anweisungen

1. **Datenbank leeren**:
   ```bash
   python3 clear_database.py
   ```

2. **Test-EML verarbeiten**:
   ```bash
   # Einzelne EML-Datei testen
   python3 test_email_only.py
   ```

3. **Ergebnis prüfen**:
   ```sql
   -- In der Datenbank prüfen
   SELECT id, filename, source_type, summary 
   FROM documents 
   WHERE filename LIKE '%.eml%'
   ORDER BY id;
   ```

4. **Erwartetes Ergebnis**:
   - Für eine EML mit 2 Attachments: 3 Datenbankeinträge
   - Alle mit gleichem `filename` (EML-Name)
   - Unterscheidung über `source_type`

## Test-Dateien
Verfügbare EML-Dateien zum Testen:
- `/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958/Ihring._.Ihring 5.eml` (6MB - hat Attachments)
- `/Users/aaron/Documents/Anke_docs_bak_19-07-24-0958/Ihring._.Ihring 4.eml` (17MB - große Datei)

## Erfolgskriterien
- [ ] Alle EML-bezogenen Einträge haben den EML-Dateinamen
- [ ] Attachments werden als separate Einträge gespeichert
- [ ] Email-Summary enthält Attachment-Liste
- [ ] Attachment-Summary enthält den tatsächlichen Attachment-Namen
- [ ] Doppelklick auf DB-Eintrag öffnet Email-Client