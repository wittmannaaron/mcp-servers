# MCP Servers Konfiguration

Dieses Repository enthält die Konfiguration für verschiedene MCP (Model Context Protocol) Server, die mit Claude und anderen KI-Assistenten verwendet werden können.

## Verzeichnisstruktur

```
/Users/aaron/Projects/mcp-servers/
├── configs/                  # Konfigurationsdateien für verschiedene Clients
│   ├── claude-desktop/       # Claude Desktop Konfigurationen
│   │   └── claude_desktop_config.json
│   ├── cline/                # Cline (VS Code Extension) Konfigurationen
│   │   └── cline_mcp_settings.json
│   └── andere-clients/       # Konfigurationen für andere Clients
│       └── client_config.json
├── servers/                  # Spezifische Server-Konfigurationen und Code
│   ├── filesystem/           # Filesystem Server
│   ├── sqlite/               # SQLite Server
│   └── andere-server/        # Weitere Server
└── shared/                   # Gemeinsam genutzte Ressourcen
    └── data/                 # Gemeinsam genutzte Daten
```

## Aktuell konfigurierte Server

### Filesystem Server

Der Filesystem Server ermöglicht den Zugriff auf Dateien und Verzeichnisse im Pfad `/Users/aaron/Projects/mcp-file-server`.

Funktionen:
- Dateien lesen und schreiben
- Verzeichnisse erstellen, auflisten und löschen
- Dateien/Verzeichnisse verschieben
- Dateien suchen
- Metadaten von Dateien abrufen

## Symbolische Links

Um die Konfigurationen zu verwenden, wurden symbolische Links erstellt:

```bash
# Für Claude Desktop
ln -sf /Users/aaron/Projects/mcp-servers/configs/claude-desktop/claude_desktop_config.json "/Users/aaron/Library/Application Support/Claude/claude_desktop_config.json"
```

## Hinzufügen neuer Server

Um einen neuen MCP-Server hinzuzufügen:

1. Erstellen Sie ein neues Verzeichnis unter `servers/` für den Server
2. Aktualisieren Sie die entsprechende Konfigurationsdatei unter `configs/`
3. Starten Sie den Client neu, um die Änderungen zu übernehmen

### Beispiel: Hinzufügen eines SQLite Servers

Um einen SQLite Server hinzuzufügen, würden Sie die `claude_desktop_config.json` wie folgt aktualisieren:

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
    },
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--database", "/path/to/your/database.db"]
    }
  }
}
```

## Unterstützte Clients

- **Claude Desktop**: Die offizielle Desktop-Anwendung von Anthropic
- **Cline**: Eine VS Code-Erweiterung für Claude
- **ChatMCP**: Eine plattformübergreifende Desktop-Anwendung
- **MCPHub**: Eine Desktop-Anwendung für macOS und Windows
