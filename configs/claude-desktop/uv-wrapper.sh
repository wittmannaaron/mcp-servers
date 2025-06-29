#!/bin/bash
# Lade die Benutzerumgebung
source ~/.bash_profile 2>/dev/null || source ~/.profile 2>/dev/null || source ~/.zshrc 2>/dev/null

# Führe uv mit allen übergebenen Argumenten aus
exec uv "$@"
