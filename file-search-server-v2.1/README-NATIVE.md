# Native macOS Document Search App

Eine native macOS-Anwendung für die Dokumentensuche, die das React/Flask-System in PyWebView integriert.

## Features

✅ **Native macOS Integration**
- Echte macOS-App mit nativen Menüs
- Tastenkürzel (Cmd+C, Cmd+V, Cmd+A)
- macOS-Dateisystem Integration
- Vibrancy-Effekte und Schatten

✅ **Vollständige Funktionalität**
- Suchfunktion mit LLM-Keyword-Extraktion
- Clickbare Tabellen (Datei öffnen, Ordner öffnen, Markdown-Vorschau)  
- Formatierte Markdown-Anzeige
- Chat-Assistent

✅ **Automatisches Server-Management**
- Startet Flask-Backend automatisch
- Startet React-Frontend automatisch
- Wartet auf Server-Bereitschaft
- Sauberes Cleanup beim Beenden

## Installation

1. **PyWebView installieren:**
```bash
pip install -r requirements-native.txt
```

2. **Abhängigkeiten prüfen:**
```bash
# React/Flask-Client muss existieren
ls file-search-client/
# Sollte zeigen: backend/, frontend/

# Node.js für React (falls noch nicht installiert)
cd file-search-client/frontend/
npm install
```

## Verwendung

**Native App starten:**
```bash
python native_app.py
```

Die App:
1. Startet automatisch Flask-Backend (Port 5001)
2. Startet automatisch React-Frontend (Port 3000)  
3. Öffnet native macOS-Fenster mit der Anwendung
4. Bereitet alle Menüs und Shortcuts vor

## Menü-Funktionen

**File**
- New Search: Suchfeld leeren und fokussieren
- Quit: App beenden

**Edit**  
- Copy/Paste/Select All: Standard-Textoperationen

**View**
- Reload: Seite neu laden
- Toggle Developer Tools: Entwicklertools

## Architektur

```
Native macOS App (PyWebView)
├── React Frontend (Port 3000)
│   ├── Suchoberfläche
│   ├── Tabellendarstellung  
│   ├── Markdown-Modal
│   └── Chat-Interface
└── Flask Backend (Port 5001)
    ├── /api/search - Dokumentensuche
    ├── /api/chat - LLM-Chat
    ├── /api/open-file - Datei öffnen
    ├── /api/open-folder - Ordner öffnen
    └── /api/get-markdown - Markdown-Inhalt
```

## Vorteile gegenüber Browser-Version

- **Native macOS-Integration:** Echte App mit Dock-Icon
- **Bessere Performance:** Kein Browser-Overhead  
- **Menüs und Shortcuts:** Native macOS-Bedienung
- **Dateisystem-Zugriff:** Direktes Öffnen von Dateien/Ordnern
- **Vibrancy-Effekte:** Moderne macOS-Optik

## Entwicklung

**Debug-Modus aktivieren:**
```python
# In native_app.py, Zeile ~280:
webview.start(debug=True)  # Aktiviert Entwicklertools
```

**Server-Logs anzeigen:**
Die Flask/React-Logs werden in der Konsole angezeigt, wenn die App gestartet wird.

## Troubleshooting

**"PyWebView not found":**
```bash
pip install pywebview
```

**"Backend directory not found":**  
Sicherstellen, dass `file-search-client/backend/` existiert.

**"React server failed to start":**
```bash
cd file-search-client/frontend/
npm install
npm start  # Testen ob React einzeln funktioniert
```

**Flask-Verbindungsfehler:**
```bash  
cd file-search-client/backend/
python app.py  # Testen ob Flask einzeln funktioniert
```