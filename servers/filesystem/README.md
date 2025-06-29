# Filesystem MCP Server

## Übersicht

Der Filesystem MCP Server ermöglicht den Zugriff auf Dateien und Verzeichnisse über das Model Context Protocol. Mit diesem Server kann Claude Dateien lesen und schreiben, Verzeichnisse erstellen und auflisten, Dateien suchen und vieles mehr.

## Installation

Der Filesystem MCP Server ist als NPM-Paket verfügbar und kann mit `npx` ausgeführt werden:

```bash
npx -y @modelcontextprotocol/server-filesystem /pfad/zum/verzeichnis
```

## Konfiguration

Um den Filesystem MCP Server mit Claude Desktop zu verwenden, müssen Sie die `claude_desktop_config.json` aktualisieren. Die aktuelle Konfiguration finden Sie in der Datei `configs/claude-desktop/claude_desktop_config.json`.

Die Konfiguration sieht wie folgt aus:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/aaron/Projects/mcp-file-server"
      ]
    }
  }
}
```

## Funktionen

Der Filesystem MCP Server bietet folgende Funktionen:

### Datei-Operationen

- **read_file**: Liest den Inhalt einer Datei
- **read_multiple_files**: Liest den Inhalt mehrerer Dateien gleichzeitig
- **write_file**: Erstellt eine neue Datei oder überschreibt eine bestehende Datei
- **edit_file**: Macht zeilenbasierte Änderungen an einer Textdatei
- **get_file_info**: Ruft detaillierte Metadaten über eine Datei oder ein Verzeichnis ab

### Verzeichnis-Operationen

- **create_directory**: Erstellt ein neues Verzeichnis
- **list_directory**: Listet den Inhalt eines Verzeichnisses auf
- **directory_tree**: Gibt eine rekursive Baumansicht von Dateien und Verzeichnissen zurück
- **move_file**: Verschiebt oder benennt Dateien und Verzeichnisse um
- **search_files**: Sucht rekursiv nach Dateien und Verzeichnissen, die einem Muster entsprechen
- **list_allowed_directories**: Gibt eine Liste der Verzeichnisse zurück, auf die der Server Zugriff hat

## Sicherheit

Der Filesystem MCP Server beschränkt den Zugriff auf die Verzeichnisse, die bei der Konfiguration angegeben wurden. In unserem Fall ist das `/Users/aaron/Projects/mcp-file-server`. Claude kann nur auf Dateien und Verzeichnisse innerhalb dieses Pfades zugreifen.

## Verwendung

Nachdem Sie den Server konfiguriert haben, können Sie Claude bitten, Dateien zu lesen oder zu schreiben, Verzeichnisse zu erstellen oder zu durchsuchen und vieles mehr. Zum Beispiel:

- "Erstelle eine neue Datei mit dem Namen 'beispiel.txt' und schreibe 'Hallo Welt' hinein"
- "Zeige mir den Inhalt des Verzeichnisses"
- "Suche nach allen Dateien, die 'wichtig' im Namen haben"

## Weitere Informationen

Weitere Informationen finden Sie in der offiziellen Dokumentation des Filesystem MCP Servers im [MCP Servers Repository](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem).
