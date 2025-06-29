# SQLite MCP Server

## Übersicht

Der SQLite MCP Server ermöglicht die Interaktion mit SQLite-Datenbanken über das Model Context Protocol. Mit diesem Server kann Claude SQL-Abfragen ausführen, Daten analysieren und Geschäftseinblicke generieren.

## Installation

Um den SQLite MCP Server zu verwenden, müssen Sie zuerst das Python-Tool `uv` installieren, das für die Ausführung des Servers benötigt wird:

```bash
# Installation von uv
curl -sSf https://astral.sh/uv/install.sh | bash
```

Anschließend können Sie den SQLite MCP Server installieren:

```bash
uvx mcp-server-sqlite
```

## Konfiguration

Um den SQLite MCP Server mit Claude Desktop zu verwenden, müssen Sie die `claude_desktop_config.json` aktualisieren. Eine Beispielkonfiguration finden Sie in der Datei `configs/claude-desktop/sqlite_config_example.json`.

Die Konfiguration sieht wie folgt aus:

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "uvx",
      "args": [
        "mcp-server-sqlite",
        "--db-path",
        "/Users/aaron/Projects/mcp-servers/shared/data/example.db"
      ]
    }
  }
}
```

## Funktionen

Der SQLite MCP Server bietet folgende Funktionen:

### Abfrage-Tools

- **read_query**: Führt SELECT-Abfragen aus, um Daten aus der Datenbank zu lesen
- **write_query**: Führt INSERT-, UPDATE- oder DELETE-Abfragen aus
- **create_table**: Erstellt neue Tabellen in der Datenbank

### Schema-Tools

- **list_tables**: Gibt eine Liste aller Tabellen in der Datenbank zurück
- **describe-table**: Zeigt Schema-Informationen für eine bestimmte Tabelle an

### Analyse-Tools

- **append_insight**: Fügt neue Geschäftseinblicke zum Memo-Resource hinzu

## Verwendung

Nachdem Sie den Server konfiguriert haben, können Sie Claude bitten, SQL-Abfragen auszuführen, Tabellen zu erstellen oder Daten zu analysieren. Zum Beispiel:

- "Erstelle eine Tabelle für Kundendaten"
- "Zeige mir alle Tabellen in der Datenbank"
- "Führe eine Abfrage aus, um alle Kunden zu finden, die mehr als 1000€ ausgegeben haben"

## Beispiel-Datenbank

Sie können eine Beispiel-Datenbank erstellen, indem Sie Claude bitten, eine Tabelle zu erstellen und Daten einzufügen. Zum Beispiel:

```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO customers (name, email) VALUES
    ('Max Mustermann', 'max@example.com'),
    ('Erika Musterfrau', 'erika@example.com');
```

## Weitere Informationen

Weitere Informationen finden Sie in der offiziellen Dokumentation des SQLite MCP Servers im [MCP Servers Repository](https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite).
