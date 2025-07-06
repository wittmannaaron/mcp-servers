#!/usr/bin/env python3
"""
Real WebKit Client - Connects to actual MCP server and shows HTML output
"""

import webview
import subprocess
from pathlib import Path
from mcp_client_terminal import MCPClientTerminal

class RealWebKitClient(MCPClientTerminal):
    def __init__(self):
        super().__init__()
        
    def create_menu(self):
        """Create standard macOS menu bar with system-localized labels"""
        from webview import Menu, MenuAction, MenuSeparator
        
        return [
            Menu('File', [
                MenuAction('Quit', self.quit_app)
            ]),
            Menu('Edit', [
                MenuAction('Copy', self.copy_selection),
                MenuAction('Paste', self.paste_text),
                MenuSeparator(),
                MenuAction('Select All', self.select_all)
            ])
        ]
    
    def quit_app(self):
        """Quit the application"""
        import sys
        sys.exit(0)
    
    def copy_selection(self):
        """Copy selected text to clipboard (JavaScript-based)"""
        # This will be handled by JavaScript in the WebView
        pass
    
    def paste_text(self):
        """Paste text from clipboard (JavaScript-based)"""
        # This will be handled by JavaScript in the WebView
        pass
    
    def select_all(self):
        """Select all text (JavaScript-based)"""
        # This will be handled by JavaScript in the WebView
        pass
    
    def open_file_natively(self, file_path: str) -> dict:
        """Open file using macOS 'open' command"""
        try:
            # Use macOS 'open' command to open file with default application
            subprocess.run(["open", file_path], check=True)
            return {
                "success": True,
                "message": f"Datei geöffnet: {file_path}"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": f"Fehler beim Öffnen der Datei: {e}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unbekannter Fehler: {e}"
            }
    
    def open_folder_in_finder(self, file_path: str) -> dict:
        """Open folder containing the file in Finder"""
        try:
            # Use macOS 'open' command to reveal file in Finder
            subprocess.run(["open", "-R", file_path], check=True)
            return {
                "success": True,
                "message": f"Ordner geöffnet: {file_path}"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": f"Fehler beim Öffnen des Ordners: {e}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unbekannter Fehler: {e}"
            }
    
    def search_and_get_html(self, query: str) -> dict:
        """Search using real MCP server and return HTML results"""
        print(f"[WEBKIT] Processing real query: {query}")
        
        try:
            # Extract keywords using the existing LLM method
            keywords = self.extract_keywords_with_llm(query)
            print(f"[WEBKIT] Extracted keywords: {keywords}")
            
            # Search files using the existing MCP method
            results = self.search_files_with_keywords(keywords)
            print(f"[WEBKIT] Found {len(results)} results")
            
            if results:
                # Generate HTML using the existing method
                html_output = self.generate_html_table(results, keywords)
                return {
                    "success": True,
                    "html": html_output,
                    "results_count": len(results),
                    "keywords": keywords
                }
            else:
                return {
                    "success": False,
                    "message": f"Keine Dateien gefunden für: {', '.join(keywords)}",
                    "results_count": 0,
                    "keywords": keywords
                }
                
        except Exception as e:
            print(f"[WEBKIT] Error: {e}")
            return {
                "success": False,
                "message": f"Fehler bei der Suche: {e}",
                "results_count": 0,
                "keywords": []
            }
    
    def get_html_template(self):
        return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>MCP File Search - Real Data</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .search-container {
            padding: 15px 20px;
            background: white;
            border-bottom: 1px solid #ddd;
            flex-shrink: 0;
        }
        .search-box {
            display: flex;
            gap: 10px;
            max-width: 800px;
            margin: 0 auto;
        }
        input {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 16px;
        }
        input:focus {
            border-color: #007acc;
            outline: none;
        }
        button {
            padding: 12px 20px;
            background: #007acc;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            min-width: 100px;
        }
        button:hover {
            background: #005c99;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .results-container {
            flex: 1;
            padding: 20px;
            overflow: hidden;
            height: 600px;
        }
        .status {
            text-align: center;
            padding: 40px;
            color: #666;
            background: #f8f9fa;
            border-radius: 6px;
        }
        .error {
            color: #721c24;
            background: #f8d7da;
        }
        .loading {
            color: #0c5460;
            background: #d1ecf1;
        }
        iframe {
            width: 100%;
            height: 570px;
            border: none;
            border-radius: 6px;
            overflow: hidden;
        }
    </style>
</head>
<body>
    <div class="search-container">
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="z.B. 'Finde Dateien über Familie' oder 'Suche nach BMW'">
            <button id="searchBtn" onclick="performSearch()">Suchen</button>
        </div>
    </div>
    
    <div class="results-container">
        <div id="resultsContent" class="status">
            Bereit für Ihre Suche. Geben Sie einen Suchbegriff ein.
        </div>
    </div>
    
    <script>
        // Function to open files natively via Python API
        function openFileNatively(filePath) {
            pywebview.api.open_file_natively(filePath).then(function(result) {
                if (!result.success) {
                    alert('Fehler beim Öffnen der Datei: ' + result.message);
                }
            }).catch(function(error) {
                alert('Fehler beim Öffnen der Datei: ' + error);
            });
        }
        
        function performSearch() {
            const input = document.getElementById('searchInput');
            const button = document.getElementById('searchBtn');
            const results = document.getElementById('resultsContent');
            const query = input.value.trim();
            
            if (!query) {
                alert('Bitte geben Sie eine Suchanfrage ein');
                return;
            }
            
            // Show loading state
            button.disabled = true;
            button.textContent = 'Suche...';
            results.innerHTML = '<div class="status loading">🔍 Durchsuche Datenbank...</div>';
            
            // Call real search
            pywebview.api.search_and_get_html(query).then(function(result) {
                button.disabled = false;
                button.textContent = 'Suchen';
                
                if (result.success) {
                    // Show HTML results in iframe for proper rendering
                    const blob = new Blob([result.html], {type: 'text/html'});
                    const url = URL.createObjectURL(blob);
                    results.innerHTML = `<iframe src="${url}"></iframe>`;
                } else {
                    results.innerHTML = `<div class="status error">${result.message}</div>`;
                }
                
            }).catch(function(error) {
                button.disabled = false;
                button.textContent = 'Suchen';
                results.innerHTML = `<div class="status error">Fehler: ${error}</div>`;
                console.error('Search error:', error);
            });
        }
        
        // Enter key support
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
        
        // Focus input on load
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('searchInput').focus();
        });
        
        // Add keyboard shortcuts for copy/paste
        document.addEventListener('keydown', function(e) {
            // Command+C (Copy)
            if (e.metaKey && e.key === 'c') {
                document.execCommand('copy');
            }
            // Command+V (Paste) - only in search input
            else if (e.metaKey && e.key === 'v') {
                if (e.target.id === 'searchInput') {
                    // Let default paste behavior work
                    return true;
                }
            }
            // Command+A (Select All)
            else if (e.metaKey && e.key === 'a') {
                document.execCommand('selectAll');
            }
        });
        
        // Expose file opening function for iframe access
        window.openFileNatively = function(filePath) {
            if (typeof pywebview !== 'undefined' && pywebview.api && pywebview.api.open_file_natively) {
                pywebview.api.open_file_natively(filePath).then(function(result) {
                    if (!result.success) {
                        alert('Fehler beim Öffnen der Datei: ' + result.message);
                    }
                }).catch(function(error) {
                    alert('Fehler beim Öffnen der Datei: ' + error);
                });
            } else {
                // Fallback: copy to clipboard
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(filePath).then(() => {
                        alert('Dateipfad wurde in die Zwischenablage kopiert:\\n' + filePath);
                    }).catch(() => {
                        prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                    });
                } else {
                    prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                }
            }
        };
        
        // Expose folder opening function for iframe access
        window.openFolderInFinder = function(filePath) {
            if (typeof pywebview !== 'undefined' && pywebview.api && pywebview.api.open_folder_in_finder) {
                pywebview.api.open_folder_in_finder(filePath).then(function(result) {
                    if (!result.success) {
                        alert('Fehler beim Öffnen des Ordners: ' + result.message);
                    }
                }).catch(function(error) {
                    alert('Fehler beim Öffnen des Ordners: ' + error);
                });
            } else {
                // Fallback: copy to clipboard
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(filePath).then(() => {
                        alert('Dateipfad wurde in die Zwischenablage kopiert:\\n' + filePath);
                    }).catch(() => {
                        prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                    });
                } else {
                    prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                }
            }
        };
    </script>
</body>
</html>"""
    
    def start_app(self):
        """Start the real WebKit application"""
        print("=" * 60)
        print("🔍 Real WebKit MCP Client")
        print("=" * 60)
        
        # Check prerequisites
        if not Path("server.py").exists():
            print("✗ Fehler: server.py nicht gefunden!")
            return
        
        # Test connections
        if not self.test_ollama_connection():
            print("Bitte stellen Sie sicher, dass Ollama läuft")
            return
        
        if not self.start_mcp_server():
            print("Bitte überprüfen Sie die MCP-Server-Konfiguration")
            return
        
        print("\nStarte WebKit Interface mit echten Daten...")
        
        try:
            # Create WebKit window with menu
            webview.create_window(
                'MCP File Search - Real Data',
                html=self.get_html_template(),
                js_api=self,
                width=1200,
                height=800,
                min_size=(800, 600)
            )
            
            # Start the app (copy/paste works via JavaScript and default WebKit behavior)
            webview.start(debug=False)
            
        finally:
            # Cleanup
            print("Räume auf...")
            if self.mcp_process:
                self.mcp_process.terminate()
                self.mcp_process.wait()
            print("Auf Wiedersehen!")

def main():
    """Main function"""
    client = RealWebKitClient()
    client.start_app()

if __name__ == "__main__":
    main()