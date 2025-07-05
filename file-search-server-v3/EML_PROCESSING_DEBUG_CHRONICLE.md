# Fehleranalyse und Lösungs-Chronik: EML-Verarbeitung

Dieses Dokument beschreibt den schrittweisen Prozess zur Identifizierung und Behebung des Problems bei der Verarbeitung von EML-Dateien mit Anhängen.

## 1. Ursprüngliche Problembeschreibung

- **Problem:** EML-Dateien mit Anhängen werden nicht korrekt in der Datenbank katalogisiert. Es wird nur ein einziger Eintrag für die EML-Datei selbst erstellt, die Anhänge fehlen.
- **Anforderung:** Alle Teile einer EML-Datei (die E-Mail selbst und jeder Anhang) müssen als separate Einträge in der Datenbank gespeichert werden, aber alle mit demselben `file_path` und `filename`, der auf die ursprüngliche EML-Datei verweist.

## 2. Hypothese 1: Falsche Dateinamen-Zuweisung

- **Annahme:** Das System speichert Anhänge mit ihrem eigenen Dateinamen, was gegen die Anforderung verstößt.
- **Aktion:** Anpassung in `src/core/ingestion.py`, um sicherzustellen, dass für Anhänge der `file_path` der übergeordneten EML-Datei verwendet wird.
- **Ergebnis:** Das Problem bestand weiterhin. Die Datenbank akzeptierte keine weiteren Einträge für denselben `file_path`.

## 3. Hypothese 2: Fehlende Spalte zur Unterscheidung

- **Annahme:** Die Datenbank benötigt eine zusätzliche Spalte (`source_type`), um zwischen einer E-Mail und ihren Anhängen zu unterscheiden.
- **Aktion:** Ich habe `source_type` zur `CREATE TABLE`-Anweisung in `src/database/database.py` hinzugefügt.
- **Ergebnis:** Der Test schlug fehl, weil die Spalte in der existierenden Datenbank nicht vorhanden war. Der Benutzer bestätigte zudem, dass keine Schema-Änderungen in Form von neuen Spalten erwünscht sind. **Diese Hypothese war falsch.**

## 4. Hypothese 3: `UNIQUE`-Constraint auf `file_path`

- **Annahme:** Die eigentliche Ursache ist eine `UNIQUE`-Beschränkung auf der `file_path`-Spalte, die naturgemäß verhindert, dass mehrere Einträge mit demselben Pfad existieren.
- **Aktion:**
    1.  Entfernen der `UNIQUE`-Beschränkung in der `CREATE TABLE`-Anweisung in `src/database/database.py`.
    2.  Entfernen der fälschlicherweise hinzugefügten `source_type`-Spalte aus derselben Datei.
    3.  Erstellung eines Migrations-Skripts (`migrate_database.py`), um die Änderung auf die bestehende Datenbank anzuwenden.
- **Ergebnis:** Der Test schlug immer noch fehl, diesmal mit einem `UNIQUE constraint failed`-Fehler, obwohl die Migration erfolgreich schien. Dies deutete darauf hin, dass die Einträge sich gegenseitig überschreiben oder die Schema-Änderung im Testlauf nicht wirksam wird.

## 5. Hypothese 4: `INSERT OR REPLACE` überschreibt Einträge

- **Annahme:** Die Verwendung von `INSERT OR REPLACE` führt dazu, dass neue Einträge (Anhänge) alte Einträge (die E-Mail) mit demselben `file_path` überschreiben.
- **Aktion:**
    1.  Änderung von `INSERT OR REPLACE` zu `INSERT` in `src/database/database.py`.
    2.  Anpassung der Logik zur Abfrage der `id` nach dem Einfügen, um die eindeutige `uuid` anstelle des mehrdeutigen `file_path` zu verwenden.
- **Ergebnis:** Der Test schlug weiterhin mit einem `UNIQUE constraint failed`-Fehler fehl.

## 6. Hypothese 5: Testumgebung wird nicht korrekt zurückgesetzt

- **Annahme:** Die `CREATE TABLE IF NOT EXISTS`-Logik verhindert, dass das Schema in Testläufen aktualisiert wird. Die alte Tabellenstruktur bleibt trotz der Code-Änderungen bestehen.
- **Aktion:** Anpassung von `clear_database.py`, sodass es `DROP TABLE` anstelle von `DELETE FROM` verwendet. Dies erzwingt bei jedem Testlauf eine Neuerstellung der Tabellen mit dem aktuellen Schema aus dem Code.
- **Ergebnis:** Der Test schlug immer noch mit `UNIQUE constraint failed` fehl.

## 7. Finale Diagnose: Schema-Definition an der falschen Stelle geändert

- **Erkenntnis:** Die bisherigen Änderungen wurden hauptsächlich in `src/database/database.py` vorgenommen. Der Ingestion-Prozess, der im Test aufgerufen wird, verwendet jedoch eine separate Client-Klasse: `src/core/ingestion_mcp_client.py`. Diese Klasse hat ihre **eigene** `_ensure_initialized`-Methode mit einer hartcodierten `CREATE TABLE`-Anweisung. Die Änderungen in `database.py` waren für den Testlauf irrelevant.
- **Kernfehler:** Die `UNIQUE`-Beschränkung wurde in der für den Testprozess relevanten Datei (`ingestion_mcp_client.py`) nie entfernt.

## 8. Finale und erfolgreiche Lösung

- **Aktion 1:** Anpassung der `CREATE TABLE`-Anweisung in **`src/core/ingestion_mcp_client.py`**, um die `UNIQUE`-Beschränkung von `file_path` zu entfernen.
- **Aktion 2:** Anpassung der `store_document_metadata`-Methode in derselben Datei, um `INSERT` statt `INSERT OR REPLACE` zu verwenden und die `id` über die `uuid` abzurufen (dies war bereits aus Hypothese 4 teilweise umgesetzt).
- **Aktion 3:** Sicherstellung, dass `clear_database.py` die Tabellen vor dem Test löscht (`DROP TABLE`).
- **Ergebnis:** Nach diesen gezielten Änderungen an der korrekten Stelle war der Test erfolgreich. Die Datenbank akzeptiert nun mehrere Einträge für denselben `file_path`, wodurch E-Mails und ihre Anhänge korrekt katalogisiert werden.

Der Task ist nun angehalten.