# File Catalog - Deployment Guide

## 🚀 Deployment auf neuen Mac

### Was wurde kopiert:
- **Kompletter Quellcode** (`src/` Verzeichnis)
- **Konfigurationsdateien** (`.env.example`, `.gitignore`, `.mcp.json`)
- **Dokumentation** (`README.md`, `Database-Administration-Handbook.md`)
- **Setup-Skripte** (`setup.sh`, `full_ingestion_test.py`)
- **Dependencies** (`requirements.txt`)
- **Verzeichnisstruktur** (`data/`, `logs/`)

### Was NICHT kopiert wurde (automatisch erstellt):
- **Virtual Environment** (`venv/`) - wird neu erstellt
- **Build-Artefakte** (`dist/`, `*.whl`, `uv.lock`) - nicht benötigt 
- **Python-Cache** (`__pycache__/`) - wird automatisch erstellt
- **Datenbank-Dateien** (`data/*.db`) - werden beim ersten Lauf erstellt
- **Log-Dateien** (`logs/*.log`) - werden beim ersten Lauf erstellt
- **Temporäre Dateien** (`.DS_Store`)
- **Lokale Konfiguration** (`.env`) - muss aus `.env.example` erstellt werden

### 🧹 Bereinigungen durchgeführt:
- **Entfernt:** `src/sqlite/.venv/` (alter MCP-Server venv)
- **Entfernt:** `src/.venv/` (duplikate venv)
- **Entfernt:** `dist/` Verzeichnisse mit Build-Artefakten
- **Entfernt:** `uv.lock` Dateien (werden neu generiert)
- **Entfernt:** `__pycache__/` Verzeichnisse

## 📋 Setup-Schritte auf neuem Mac

### 1. Voraussetzungen installieren
```bash
# Homebrew (falls nicht vorhanden)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.13 (falls nicht vorhanden)
brew install python@3.13

# Pandoc
brew install pandoc

# ExifTool (optional, für Bildmetadaten)
brew install exiftool

# Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Ollama-Modelle installieren
```bash
# Ollama starten
ollama serve

# In neuem Terminal:
# Embedding-Modell
ollama pull bge-m3

# LLM-Modell
ollama pull llama3.2:latest
```

### 3. Projekt einrichten
```bash
# In das kopierte Verzeichnis wechseln
cd /path/to/file-catalog-v1

# Umgebungskonfiguration erstellen
cp .env.example .env

# Automatisches Setup ausführen
chmod +x setup.sh
./setup.sh
```

### 4. Erste Tests
```bash
# Virtual Environment aktivieren
source venv/bin/activate

# Tool-Verfügbarkeit prüfen
python full_ingestion_test.py --check-tools

# Kleiner Test (10 Dateien)
python full_ingestion_test.py -c 10
```

## ⚠️ Wichtige Anpassungen

### Pfade anpassen
Die folgenden Pfade müssen eventuell angepasst werden:
- **Testverzeichnis** in `full_ingestion_test.py`
- **Dokumentenpfade** in Konfigurationsdateien
- **Ollama-Host** falls nicht localhost

### Modell-Verfügbarkeit prüfen
```bash
# Ollama-Modelle prüfen
ollama list

# Sollte anzeigen:
# - bge-m3:latest
# - llama3.2:latest
```

### Memory-Einstellungen (wichtig für Apple Silicon)
Das System ist bereits für Apple Silicon optimiert:
- PyTorch MPS-Warnungen unterdrückt
- Docling ohne Vision-Modelle konfiguriert
- Memory-effiziente Einstellungen

## 🔧 Konfiguration

### .env-Datei anpassen
```bash
# Beispiel-Konfiguration
LOG_LEVEL="INFO"
OLLAMA_HOST="http://localhost:11434"
OLLAMA_MODEL="llama3.2:latest"
MAX_FILE_SIZE_MB="100"
```

### Erste Ingestion testen
```bash
# Kleiner Test mit eigenem Verzeichnis
python full_ingestion_test.py -d /Users/$(whoami)/Documents/test_docs -c 5

# Vollständiger Test
python full_ingestion_test.py
```

## 🎯 Erfolgskriterien

Das Deployment ist erfolgreich wenn:
- ✅ `python full_ingestion_test.py --check-tools` zeigt alle Tools als verfügbar
- ✅ Ollama-Modelle sind geladen (`ollama list`)
- ✅ Erste Testdateien werden erfolgreich verarbeitet
- ✅ Datenbank wird erstellt (`data/filecatalog.db`)
- ✅ Keine PyTorch MPS-Warnungen in den Logs

## 📞 Troubleshooting

### Häufige Probleme:
1. **Ollama nicht erreichbar** → `ollama serve` prüfen
2. **Modelle nicht gefunden** → `ollama pull` Kommandos wiederholen
3. **Python-Version** → Python 3.13+ erforderlich
4. **Pandoc-Fehler** → `brew install pandoc` überprüfen
5. **Memory-Probleme** → Docling Vision-Modelle sind bereits deaktiviert

## 🚀 Produktionsbereitschaft

Das System ist produktionsbereit wenn:
- Alle Dependencies installiert sind
- Ollama-Modelle verfügbar sind
- Testdateien erfolgreich verarbeitet werden
- Keine Fehler in den Logs
- Apple Silicon Optimierungen aktiv

---

**Hinweis:** Diese Deployment-Kopie enthält alle notwendigen Dateien für eine vollständige Migration auf einen neuen Mac.