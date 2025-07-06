#!/bin/zsh

# Improved Dependency Analysis Script for Python Project
# Handles multiple virtual environments and project structures

echo "🔍 Verbesserte Python Dependency Analyse"
echo "========================================"
echo

# Create temporary files
TEMP_DIR=$(mktemp -d)
MAIN_IMPORTS="$TEMP_DIR/main_imports.txt"
SQLITE_IMPORTS="$TEMP_DIR/sqlite_imports.txt"
MAIN_UNIQUE="$TEMP_DIR/main_unique.txt"
SQLITE_UNIQUE="$TEMP_DIR/sqlite_unique.txt"
MAIN_REQUIREMENTS="$TEMP_DIR/main_requirements.txt"
SQLITE_REQUIREMENTS="$TEMP_DIR/sqlite_requirements.txt"

# Function to extract package name from import statement
extract_package_name() {
    local import_line="$1"
    # Remove 'import ' or 'from ' prefix
    local cleaned=$(echo "$import_line" | sed -E 's/^(import|from) +//')
    # Get first part before dot or space
    local package=$(echo "$cleaned" | sed -E 's/[. ].*//')
    echo "$package"
}

# Function to check if a library is actually used in a file
check_library_usage() {
    local file="$1"
    local library="$2"
    
    # Count actual usage (excluding import lines)
    local usage_count=$(grep -v "^[[:space:]]*\(import\|from\)" "$file" | grep -c "$library" 2>/dev/null || echo 0)
    echo "$usage_count"
}

echo "📁 Analysiere Projektstruktur..."

# Analyze main project (excluding sqlite subdirectory and venv)
echo "🔍 Hauptprojekt (ohne src/sqlite):"
echo "--------------------------------"

find . -name "*.py" \
    -not -path "./venv/*" \
    -not -path "./.venv/*" \
    -not -path "./src/sqlite/*" \
    -not -path "./__pycache__/*" | while read -r file; do
    echo "Processing: $file"
    
    # Extract import statements
    grep -E "^[[:space:]]*(import|from)[[:space:]]+" "$file" 2>/dev/null | while read -r import_line; do
        package=$(extract_package_name "$import_line")
        usage_count=$(check_library_usage "$file" "$package")
        echo "$file|$package|$import_line|$usage_count" >> "$MAIN_IMPORTS"
    done
done

# Analyze sqlite subproject separately
echo
echo "🔍 SQLite MCP Server (src/sqlite):"
echo "--------------------------------"

find ./src/sqlite -name "*.py" \
    -not -path "./src/sqlite/.venv/*" \
    -not -path "./src/sqlite/__pycache__/*" | while read -r file; do
    echo "Processing: $file"
    
    # Extract import statements
    grep -E "^[[:space:]]*(import|from)[[:space:]]+" "$file" 2>/dev/null | while read -r import_line; do
        package=$(extract_package_name "$import_line")
        usage_count=$(check_library_usage "$file" "$package")
        echo "$file|$package|$import_line|$usage_count" >> "$SQLITE_IMPORTS"
    done
done

echo
echo "📊 Analysiere Dependencies..."

# Get unique imported packages for each project
cut -d'|' -f2 "$MAIN_IMPORTS" | sort | uniq > "$MAIN_UNIQUE"
cut -d'|' -f2 "$SQLITE_IMPORTS" | sort | uniq > "$SQLITE_UNIQUE"

# Extract libraries from requirements files
echo "📋 Extrahiere Requirements..."

# Main project requirements.txt
grep -v "^#" requirements.txt | grep -v "^$" | sed -E 's/[>=<].*//' | sed 's/\[.*\]//' > "$MAIN_REQUIREMENTS"

# SQLite project dependencies from pyproject.toml
echo "📋 Extrahiere SQLite Dependencies aus pyproject.toml..."
if [[ -f "src/sqlite/pyproject.toml" ]]; then
    # Extract dependencies from pyproject.toml
    python3 -c "
import tomllib
with open('src/sqlite/pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
    deps = data.get('project', {}).get('dependencies', [])
    dev_deps = data.get('tool', {}).get('uv', {}).get('dev-dependencies', [])
    all_deps = deps + dev_deps
    for dep in all_deps:
        # Remove version constraints
        import re
        clean_dep = re.sub(r'[>=<].*', '', dep)
        clean_dep = re.sub(r'\[.*\]', '', clean_dep)
        print(clean_dep.strip())
" > "$SQLITE_REQUIREMENTS" 2>/dev/null || echo "mcp" > "$SQLITE_REQUIREMENTS"
fi

echo
echo "🔍 ANALYSE ERGEBNISSE"
echo "===================="

echo
echo "1️⃣  HAUPTPROJEKT - IMPORTIERTE PAKETE:"
echo "------------------------------------"
if [[ -s "$MAIN_UNIQUE" ]]; then
    sort "$MAIN_UNIQUE" | nl
else
    echo "Keine Imports gefunden"
fi

echo
echo "2️⃣  SQLITE MCP SERVER - IMPORTIERTE PAKETE:"
echo "------------------------------------------"
if [[ -s "$SQLITE_UNIQUE" ]]; then
    sort "$SQLITE_UNIQUE" | nl
else
    echo "Keine Imports gefunden"
fi

echo
echo "3️⃣  HAUPTPROJEKT - REQUIREMENTS.TXT:"
echo "-----------------------------------"
sort "$MAIN_REQUIREMENTS" | nl

echo
echo "4️⃣  SQLITE MCP SERVER - PYPROJECT.TOML DEPENDENCIES:"
echo "---------------------------------------------------"
if [[ -s "$SQLITE_REQUIREMENTS" ]]; then
    sort "$SQLITE_REQUIREMENTS" | nl
else
    echo "Keine Dependencies gefunden"
fi

echo
echo "5️⃣  HAUPTPROJEKT - PAKETE IN REQUIREMENTS ABER NICHT IMPORTIERT:"
echo "---------------------------------------------------------------"
comm -23 <(sort "$MAIN_REQUIREMENTS") <(sort "$MAIN_UNIQUE") | while read -r lib; do
    if [[ -n "$lib" ]]; then
        echo "❌ $lib - möglicherweise nicht benötigt im Hauptprojekt"
    fi
done

echo
echo "6️⃣  SQLITE SERVER - PAKETE IN PYPROJECT ABER NICHT IMPORTIERT:"
echo "-------------------------------------------------------------"
if [[ -s "$SQLITE_REQUIREMENTS" && -s "$SQLITE_UNIQUE" ]]; then
    comm -23 <(sort "$SQLITE_REQUIREMENTS") <(sort "$SQLITE_UNIQUE") | while read -r lib; do
        if [[ -n "$lib" ]]; then
            echo "❌ $lib - möglicherweise nicht benötigt im SQLite Server"
        fi
    done
fi

echo
echo "7️⃣  HAUPTPROJEKT - IMPORTIERTE PAKETE NICHT IN REQUIREMENTS:"
echo "-----------------------------------------------------------"
comm -13 <(sort "$MAIN_REQUIREMENTS") <(sort "$MAIN_UNIQUE") | while read -r lib; do
    if [[ -n "$lib" ]]; then
        # Check if it's a standard library
        if python3 -c "import $lib" 2>/dev/null; then
            if python3 -c "import sys; print('$lib' in sys.stdlib_module_names)" 2>/dev/null | grep -q "True"; then
                echo "✅ $lib - Standard Library (OK)"
            else
                echo "⚠️  $lib - Externe Bibliothek, fehlt in requirements.txt"
            fi
        else
            echo "❓ $lib - Unbekannte Bibliothek oder lokales Modul"
        fi
    fi
done

echo
echo "8️⃣  SQLITE SERVER - IMPORTIERTE PAKETE NICHT IN PYPROJECT:"
echo "---------------------------------------------------------"
if [[ -s "$SQLITE_REQUIREMENTS" && -s "$SQLITE_UNIQUE" ]]; then
    comm -13 <(sort "$SQLITE_REQUIREMENTS") <(sort "$SQLITE_UNIQUE") | while read -r lib; do
        if [[ -n "$lib" ]]; then
            # Check if it's a standard library
            if python3 -c "import $lib" 2>/dev/null; then
                if python3 -c "import sys; print('$lib' in sys.stdlib_module_names)" 2>/dev/null | grep -q "True"; then
                    echo "✅ $lib - Standard Library (OK)"
                else
                    echo "⚠️  $lib - Externe Bibliothek, fehlt in pyproject.toml"
                fi
            else
                echo "❓ $lib - Unbekannte Bibliothek oder lokales Modul"
            fi
        fi
    done
fi

echo
echo "9️⃣  ÜBERSCHNEIDUNGEN ZWISCHEN PROJEKTEN:"
echo "--------------------------------------"
if [[ -s "$MAIN_UNIQUE" && -s "$SQLITE_UNIQUE" ]]; then
    echo "Gemeinsame Pakete:"
    comm -12 <(sort "$MAIN_UNIQUE") <(sort "$SQLITE_UNIQUE") | while read -r lib; do
        if [[ -n "$lib" ]]; then
            echo "🔄 $lib - in beiden Projekten verwendet"
        fi
    done
    
    echo
    echo "Nur im Hauptprojekt:"
    comm -23 <(sort "$MAIN_UNIQUE") <(sort "$SQLITE_UNIQUE") | while read -r lib; do
        if [[ -n "$lib" ]]; then
            echo "📦 $lib - nur im Hauptprojekt"
        fi
    done
    
    echo
    echo "Nur im SQLite Server:"
    comm -13 <(sort "$MAIN_UNIQUE") <(sort "$SQLITE_UNIQUE") | while read -r lib; do
        if [[ -n "$lib" ]]; then
            echo "🗄️  $lib - nur im SQLite Server"
        fi
    done
fi

echo
echo "🔟 DETAILLIERTE NUTZUNGSANALYSE - HAUPTPROJEKT:"
echo "----------------------------------------------"
echo "Imports die möglicherweise ungenutzt sind:"
while IFS='|' read -r file package import_stmt usage_count; do
    if [[ "$usage_count" == "0" && "$file" != "File" && -n "$file" ]]; then
        echo "❌ $file: '$import_stmt' (nicht verwendet)"
    fi
done < "$MAIN_IMPORTS"

echo
echo "1️⃣1️⃣ DETAILLIERTE NUTZUNGSANALYSE - SQLITE SERVER:"
echo "------------------------------------------------"
echo "Imports die möglicherweise ungenutzt sind:"
while IFS='|' read -r file package import_stmt usage_count; do
    if [[ "$usage_count" == "0" && "$file" != "File" && -n "$file" ]]; then
        echo "❌ $file: '$import_stmt' (nicht verwendet)"
    fi
done < "$SQLITE_IMPORTS"

echo
echo "1️⃣2️⃣ ZUSAMMENFASSUNG NACH PAKETEN - HAUPTPROJEKT:"
echo "-----------------------------------------------"
cut -d'|' -f2 "$MAIN_IMPORTS" | sort | uniq -c | sort -nr | while read -r count package; do
    if [[ -n "$package" && "$package" != "Package" ]]; then
        total_usage=$(grep "|$package|" "$MAIN_IMPORTS" | cut -d'|' -f4 | awk '{sum+=$1} END {print sum+0}')
        echo "📦 $package: verwendet in $count Dateien, $total_usage mal aufgerufen"
    fi
done

echo
echo "1️⃣3️⃣ ZUSAMMENFASSUNG NACH PAKETEN - SQLITE SERVER:"
echo "------------------------------------------------"
if [[ -s "$SQLITE_IMPORTS" ]]; then
    cut -d'|' -f2 "$SQLITE_IMPORTS" | sort | uniq -c | sort -nr | while read -r count package; do
        if [[ -n "$package" && "$package" != "Package" ]]; then
            total_usage=$(grep "|$package|" "$SQLITE_IMPORTS" | cut -d'|' -f4 | awk '{sum+=$1} END {print sum+0}')
            echo "🗄️  $package: verwendet in $count Dateien, $total_usage mal aufgerufen"
        fi
    done
fi

echo
echo "1️⃣4️⃣ DOPPELTE EINTRÄGE IN REQUIREMENTS.TXT:"
echo "------------------------------------------"
sort "$MAIN_REQUIREMENTS" | uniq -d | while read -r dup; do
    if [[ -n "$dup" ]]; then
        echo "🔄 $dup - doppelt in requirements.txt"
    fi
done

echo
echo "📁 Detaillierte Reports gespeichert in: $TEMP_DIR"
echo "   - Hauptprojekt: $MAIN_IMPORTS"
echo "   - SQLite Server: $SQLITE_IMPORTS"
echo
echo "💡 EMPFEHLUNGEN:"
echo "==============="
echo "1. ✅ Separates SQLite MCP Server Projekt erkannt"
echo "2. 🔍 Prüfen Sie die '❌' markierten Pakete in beiden Projekten"
echo "3. ⚠️  Fügen Sie fehlende externe Bibliotheken hinzu"
echo "4. 🧹 Entfernen Sie ungenutzte Imports aus dem Code"
echo "5. 📦 Bereinigen Sie doppelte Einträge in requirements.txt"
echo "6. 🔄 Überlegen Sie, ob gemeinsame Dependencies konsolidiert werden können"

echo
echo "🔍 Für detaillierte Analyse:"
echo "Hauptprojekt: cat $MAIN_IMPORTS | column -t -s'|'"
echo "SQLite Server: cat $SQLITE_IMPORTS | column -t -s'|'"