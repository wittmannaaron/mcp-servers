# Deployment Notes - Critical Path Updates

## 🚨 Wichtige Pfad-Anpassungen für neuen Mac

### MCP JSON Konfiguration
**Datei:** `.mcp.json`

**Anzupassende Pfade:**
```json
{
  "mcpServers": {
    "sqlite-filebrowser": {
      "args": [
        "--directory",
        "/PFAD/ZUM/NEUEN/VERZEICHNIS/src/sqlite",  // <- Anpassen!
        "run",
        "mcp-server-sqlite",
        "--db-path",
        "/PFAD/ZUR/DATENBANK/filebrowser.db"      // <- Anpassen!
      ]
    }
  }
}
```

### Nach der Migration auf neuen Mac:

1. **Projekt-Pfad anpassen:**
   ```bash
   # Beispiel: Wenn kopiert nach /Users/newuser/Documents/file-catalog-v1
   sed -i '' 's|/Users/aaron/Projects/mcp-servers/file-catalog-v1|/Users/newuser/Documents/file-catalog-v1|g' .mcp.json
   ```

2. **Datenbank-Pfad anpassen:**
   ```bash
   # Beispiel: Auf lokale Datenbank zeigen
   sed -i '' 's|/Users/aaron/Projects/mcp-servers/file-search-server-v3/data/filebrowser.db|./data/filecatalog.db|g' .mcp.json
   ```

## 🧹 Bereinigungen durchgeführt

### Entfernte Duplikate:
- ❌ `src/src/mcp_server_sqlite/` (Duplikat)
- ❌ `src/pyproject.toml` (Duplikat)
- ❌ `src/README.md` (Duplikat)
- ❌ `src/Dockerfile` (Duplikat)

### Behaltene Struktur:
- ✅ `src/sqlite/src/mcp_server_sqlite/` (Korrekt)
- ✅ `src/sqlite/pyproject.toml` (Korrekt)
- ✅ `src/sqlite/README.md` (Korrekt)

## 📊 Finale Statistiken

- **Größe:** 284 KB (nochmals optimiert)
- **Dateien:** 27 Dateien (von 32 reduziert)
- **Python-Dateien:** 17 Dateien (von 21 reduziert)
- **Verzeichnisse:** 9 Verzeichnisse (sauber strukturiert)

## ✅ Bereit für Deployment

Das Verzeichnis ist jetzt:
- **Duplikat-frei** (keine doppelten MCP-Server)
- **Minimal** (nur notwendige Dateien)
- **Konfiguriert** (MCP-Pfade korrekt)
- **Dokumentiert** (vollständige Anleitung)

**Nächster Schritt:** Auf neuen Mac kopieren und Pfade anpassen.