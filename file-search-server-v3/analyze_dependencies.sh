#!/bin/zsh

# Dependency Analysis Script for Python Project
# Analyzes actual imports vs requirements.txt

echo "🔍 Python Dependency Analysis"
echo "=============================="
echo

# Create temporary files
TEMP_DIR=$(mktemp -d)
ALL_IMPORTS="$TEMP_DIR/all_imports.txt"
UNIQUE_IMPORTS="$TEMP_DIR/unique_imports.txt"
REQUIREMENTS_LIBS="$TEMP_DIR/requirements_libs.txt"
USAGE_REPORT="$TEMP_DIR/usage_report.txt"

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

echo "📁 Scanning Python files..."

# Find all Python files and extract imports
find . -name "*.py" -not -path "./venv/*" -not -path "./__pycache__/*" | while read -r file; do
    echo "Processing: $file"
    
    # Extract import statements
    grep -E "^[[:space:]]*(import|from)[[:space:]]+" "$file" 2>/dev/null | while read -r import_line; do
        package=$(extract_package_name "$import_line")
        usage_count=$(check_library_usage "$file" "$package")
        echo "$file|$package|$import_line|$usage_count" >> "$ALL_IMPORTS"
    done
done

echo
echo "📊 Analyzing imports..."

# Get unique imported packages
cut -d'|' -f2 "$ALL_IMPORTS" | sort | uniq > "$UNIQUE_IMPORTS"

# Extract libraries from requirements.txt
echo "📋 Extracting requirements..."
grep -v "^#" requirements.txt | grep -v "^$" | sed -E 's/[>=<].*//' | sed 's/\[.*\]//' > "$REQUIREMENTS_LIBS"

echo
echo "🔍 ANALYSIS RESULTS"
echo "==================="

echo
echo "1️⃣  IMPORTED PACKAGES IN CODE:"
echo "------------------------------"
sort "$UNIQUE_IMPORTS" | nl

echo
echo "2️⃣  PACKAGES IN REQUIREMENTS.TXT:"
echo "--------------------------------"
sort "$REQUIREMENTS_LIBS" | nl

echo
echo "3️⃣  PACKAGES IN REQUIREMENTS BUT NOT IMPORTED:"
echo "---------------------------------------------"
comm -23 <(sort "$REQUIREMENTS_LIBS") <(sort "$UNIQUE_IMPORTS") | while read -r lib; do
    if [[ -n "$lib" ]]; then
        echo "❌ $lib - möglicherweise nicht benötigt"
    fi
done

echo
echo "4️⃣  IMPORTED PACKAGES NOT IN REQUIREMENTS:"
echo "-----------------------------------------"
comm -13 <(sort "$REQUIREMENTS_LIBS") <(sort "$UNIQUE_IMPORTS") | while read -r lib; do
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
echo "5️⃣  DETAILED USAGE ANALYSIS:"
echo "----------------------------"

# Create detailed usage report
echo "File|Package|Import Statement|Usage Count" > "$USAGE_REPORT"
cat "$ALL_IMPORTS" >> "$USAGE_REPORT"

# Show packages that are imported but never used
echo "📋 Imports die möglicherweise ungenutzt sind:"
while IFS='|' read -r file package import_stmt usage_count; do
    if [[ "$usage_count" == "0" && "$file" != "File" ]]; then
        echo "❌ $file: '$import_stmt' (nicht verwendet)"
    fi
done < "$USAGE_REPORT"

echo
echo "6️⃣  SUMMARY BY PACKAGE:"
echo "----------------------"

# Count usage per package across all files
cut -d'|' -f2 "$ALL_IMPORTS" | sort | uniq -c | sort -nr | while read -r count package; do
    if [[ -n "$package" && "$package" != "Package" ]]; then
        total_usage=$(grep "|$package|" "$ALL_IMPORTS" | cut -d'|' -f4 | awk '{sum+=$1} END {print sum+0}')
        echo "📦 $package: verwendet in $count Dateien, $total_usage mal aufgerufen"
    fi
done

echo
echo "7️⃣  DUPLICATE ENTRIES IN REQUIREMENTS.TXT:"
echo "-----------------------------------------"
# Check for duplicates in requirements.txt
sort "$REQUIREMENTS_LIBS" | uniq -d | while read -r dup; do
    if [[ -n "$dup" ]]; then
        echo "🔄 $dup - doppelt in requirements.txt"
    fi
done

echo
echo "📁 Detailed report saved to: $USAGE_REPORT"
echo "🧹 Temporary files in: $TEMP_DIR"
echo
echo "💡 EMPFEHLUNGEN:"
echo "==============="
echo "1. Prüfen Sie die '❌' markierten Pakete in requirements.txt"
echo "2. Fügen Sie fehlende externe Bibliotheken hinzu ('⚠️')"
echo "3. Entfernen Sie ungenutzte Imports aus dem Code"
echo "4. Bereinigen Sie doppelte Einträge in requirements.txt"

# Keep temp files for manual inspection
echo
echo "🔍 Für detaillierte Analyse:"
echo "cat $USAGE_REPORT | column -t -s'|'"