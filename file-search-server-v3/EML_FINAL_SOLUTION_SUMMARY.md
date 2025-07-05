# EML Processing - Finale Lösung

## Problem-Zusammenfassung
EML-Dateien mit Attachments werden nicht korrekt in der Datenbank katalogisiert. Die Hauptursache ist die UNIQUE-Constraint auf der `file_path` Spalte, die verhindert, dass mehrere Einträge für dieselbe Datei gespeichert werden können.

## Lösung

### 1. Datenbank-Schema Anpassung
- **Entfernen** der UNIQUE-Constraint von `file_path` 
- **Entfernen** der fälschlich hinzugefügten `source_type` Spalte
- **Beibehalten** der UNIQUE-Constraint nur auf `uuid`

### 2. Bereits implementierte Fixes in ingestion.py
Die Änderungen in `src/core/ingestion.py` sind bereits korrekt:
- Zeile 196: `filename: file_path.name,` stellt sicher, dass alle Einträge den EML-Dateinamen verwenden
- Die Email-Summary enthält eine Vorschau des Email-Bodys
- Attachment-Summaries sind korrekt formatiert

### 3. Keine weiteren Code-Änderungen nötig
Die existierenden Felder reichen aus, um Einträge zu unterscheiden:
- **uuid**: Eindeutig für jeden Eintrag
- **md5_hash**: Unterschiedlich für verschiedene Inhalte
- **document_type**: Zeigt den tatsächlichen Typ (email, pdf, etc.)
- **summary**: Enthält kontextuelle Information
- **original_text/markdown_content**: Der eigentliche Inhalt

## Implementierungsschritte

1. **Datenbank-Migration durchführen** (siehe DATABASE_MIGRATION_STEPS.md)
2. **Code in database.py anpassen**:
   - Zeile 32: `file_path TEXT NOT NULL,` (ohne UNIQUE)
   - Zeile 42: Komplett entfernen (source_type)
   - Zeilen 79, 87: source_type aus INSERT entfernen

3. **Testen mit eml_ingestion_test.py**

## Erwartetes Verhalten

Für "Ihring._.Ihring 5.eml" mit 2 PDF-Attachments:
- 3 Datenbank-Einträge werden erstellt
- Alle haben denselben `file_path` und `filename`
- Jeder hat eine eigene UUID und unterschiedlichen md5_hash
- Der Email-Eintrag hat document_type="email"
- Die Attachment-Einträge haben document_type="pdf"

## Vorteile dieser Lösung

1. **Minimale Änderungen**: Nur die Datenbank-Constraint wird geändert
2. **Keine neuen Spalten**: Nutzt existierende Felder optimal
3. **Korrekte Dateiverwaltung**: Alle Einträge zeigen auf die EML-Datei
4. **Skalierbar**: Funktioniert auch für ZIP-Archive und andere Container

## Test-Verifikation

```sql
-- Zeige alle Dateien mit mehreren Einträgen
SELECT file_path, COUNT(*) as entries 
FROM documents 
GROUP BY file_path 
HAVING COUNT(*) > 1
ORDER BY entries DESC;

-- Details für eine spezifische EML-Datei
SELECT id, uuid, document_type, LENGTH(original_text) as content_length
FROM documents 
WHERE file_path LIKE '%Ihring._.Ihring 5.eml%';
```

## Nächste Schritte

Nach erfolgreicher EML-Implementierung kann dasselbe Prinzip für ZIP-Archive angewendet werden:
- ZIP-Datei = 1 Eintrag für das Archiv + N Einträge für enthaltene Dokumente
- Alle Einträge zeigen auf die ZIP-Datei
- Unterscheidung durch document_type und Inhalt