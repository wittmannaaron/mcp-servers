#!/usr/bin/env python3
"""
MCP Client Terminal Interface for File Search Server (German Version)
Connects to the file search MCP server and uses Ollama llama3.2 for responses
"""

import asyncio
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
import signal
import os
import uuid

class MCPClientTerminal:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model_name = "llama3.2:latest"
        self.mcp_process = None
        self.running = True
        self.mcp_initialized = False
        self.available_tools = []
        
        # Load system prompt
        self.system_prompt = self.load_system_prompt()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\nBeende Anwendung...")
        self.running = False
        if self.mcp_process:
            self.mcp_process.terminate()
        sys.exit(0)
    
    def load_system_prompt(self) -> str:
        """Load system prompt from file"""
        try:
            with open("system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "Du bist ein hilfreicher Dateisuch-Assistent. Hilf Benutzern beim Finden und Verstehen ihrer Dateien."
    
    def start_mcp_server(self) -> bool:
        """Start the MCP server"""
        try:
            print("Starte MCP-Server...")
            self.mcp_process = subprocess.Popen(
                [sys.executable, "server.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            
            # Wait a moment for server to start
            time.sleep(2)
            
            if self.mcp_process.poll() is None:
                print("✓ MCP-Server erfolgreich gestartet")
                # Initialize MCP protocol
                if self.initialize_mcp():
                    return True
                else:
                    print("✗ MCP-Protokoll-Initialisierung fehlgeschlagen")
                    return False
            else:
                stderr_output = self.mcp_process.stderr.read()
                print(f"✗ MCP-Server konnte nicht gestartet werden: {stderr_output}")
                return False
                
        except Exception as e:
            print(f"✗ Fehler beim Starten des MCP-Servers: {e}")
            return False
    
    def initialize_mcp(self) -> bool:
        """Initialize MCP protocol and discover tools"""
        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "file-search-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            request_json = json.dumps(init_request) + "\n"
            self.mcp_process.stdin.write(request_json)
            self.mcp_process.stdin.flush()
            
            # Read initialize response
            response_line = self.mcp_process.stdout.readline()
            if response_line:
                init_response = json.loads(response_line)
                if "result" in init_response:
                    print("✓ MCP-Protokoll initialisiert")
                    
                    # Send initialized notification
                    initialized_notification = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized"
                    }
                    
                    notification_json = json.dumps(initialized_notification) + "\n"
                    self.mcp_process.stdin.write(notification_json)
                    self.mcp_process.stdin.flush()
                    
                    # Discover tools
                    if self.discover_tools():
                        self.mcp_initialized = True
                        return True
            
            return False
            
        except Exception as e:
            print(f"MCP-Initialisierung fehlgeschlagen: {e}")
            return False
    
    def discover_tools(self) -> bool:
        """Discover available tools from MCP server"""
        try:
            tools_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list"
            }
            
            request_json = json.dumps(tools_request) + "\n"
            self.mcp_process.stdin.write(request_json)
            self.mcp_process.stdin.flush()
            
            # Read tools response
            response_line = self.mcp_process.stdout.readline()
            if response_line:
                tools_response = json.loads(response_line)
                if "result" in tools_response and "tools" in tools_response["result"]:
                    self.available_tools = tools_response["result"]["tools"]
                    print(f"✓ {len(self.available_tools)} Tools entdeckt: {[tool['name'] for tool in self.available_tools]}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Tool-Entdeckung fehlgeschlagen: {e}")
            return False
    
    def test_ollama_connection(self) -> bool:
        """Test connection to Ollama"""
        try:
            print("Teste Ollama-Verbindung...")
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json()
                model_names = [model['name'] for model in models.get('models', [])]
                if self.model_name in model_names:
                    print(f"✓ Ollama verbunden, {self.model_name} verfügbar")
                    return True
                else:
                    print(f"✗ Modell {self.model_name} nicht in Ollama gefunden")
                    print(f"Verfügbare Modelle: {model_names}")
                    return False
            else:
                print(f"✗ Ollama antwortet nicht (Status: {response.status_code})")
                return False
        except Exception as e:
            print(f"✗ Kann nicht mit Ollama verbinden: {e}")
            return False
    
    def search_files(self, query: str) -> List[Dict[str, Any]]:
        """Search files using MCP server"""
        if not self.mcp_process or not self.mcp_initialized:
            return []
        
        try:
            # Create MCP request for general content search using getData tool
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "getData",
                    "arguments": {
                        "search_terms": [query]
                    }
                }
            }
            
            # Send request to MCP server
            request_json = json.dumps(mcp_request) + "\n"
            self.mcp_process.stdin.write(request_json)
            self.mcp_process.stdin.flush()
            
            # Read response with timeout
            import select
            ready, _, _ = select.select([self.mcp_process.stdout], [], [], 10.0)
            
            if ready:
                response_line = self.mcp_process.stdout.readline()
                if response_line:
                    response = json.loads(response_line)
                    print(f"DEBUG MCP Response: {response}")  # Debug output
                    
                    if "result" in response and "content" in response["result"]:
                        content = response["result"]["content"]
                        if isinstance(content, list) and len(content) > 0:
                            results = []
                            for item in content:
                                if isinstance(item, dict) and "text" in item:
                                    text_content = item["text"]
                                    try:
                                        # Each text item is a separate JSON document
                                        parsed_result = json.loads(text_content)
                                        results.append(parsed_result)
                                    except json.JSONDecodeError as e:
                                        print(f"DEBUG JSON Parse Error for item: {e}")
                                        results.append({"raw_response": text_content})
                            
                            print(f"DEBUG Parsed Results: {len(results)} items")
                            return results
                    elif "error" in response:
                        print(f"MCP-Fehler: {response['error']}")
                        return []
            else:
                print("Timeout beim Warten auf MCP-Antwort")
            
            return []
            
        except Exception as e:
            print(f"MCP-Suchfehler: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.mcp_process or not self.mcp_initialized:
            return {}
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "get_database_stats",
                    "arguments": {}
                }
            }
            
            request_json = json.dumps(mcp_request) + "\n"
            self.mcp_process.stdin.write(request_json)
            self.mcp_process.stdin.flush()
            
            # Read response
            import select
            ready, _, _ = select.select([self.mcp_process.stdout], [], [], 5.0)
            
            if ready:
                response_line = self.mcp_process.stdout.readline()
                if response_line:
                    response = json.loads(response_line)
                    if "result" in response and "content" in response["result"]:
                        content = response["result"]["content"]
                        if isinstance(content, list) and len(content) > 0:
                            text_content = content[0].get("text", "")
                            try:
                                return json.loads(text_content)
                            except json.JSONDecodeError:
                                return {"raw_response": text_content}
            
            return {}
            
        except Exception as e:
            print(f"Fehler beim Abrufen der Datenbankstatistiken: {e}")
            return {}
    
    def prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Prepare context from search results for Ollama"""
        if not search_results:
            return "Keine Dateien gefunden, die zu Ihrer Anfrage passen."
        
        context_parts = [f"Gefundene Dateien ({len(search_results)} Ergebnisse):"]
        
        for i, result in enumerate(search_results, 1):
            if isinstance(result, dict):
                filename = result.get("filename", "Unbekannte Datei")
                file_path = result.get("file_path", "Unbekannter Pfad")
                content_preview = result.get("content_preview", "Kein Inhalt")
                created_at = result.get("created_at", "Unbekanntes Datum")
                
                context_parts.append(f"\n{i}. Datei: {filename}")
                context_parts.append(f"   Pfad: {file_path}")
                context_parts.append(f"   Erstellt: {created_at}")
                if content_preview and content_preview != "Kein Inhalt":
                    context_parts.append(f"   Inhalt: {content_preview[:150]}...")
        
        return "\n".join(context_parts)
    
    def generate_html_table(self, search_results: List[Dict[str, Any]], search_terms: List[str]) -> str:
        """Generate stacked HTML table from search results for WebKit app"""
        # HTML template optimized for WebKit/macOS
        html_template = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Suchergebnisse für: {search_terms}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
            line-height: 1.5;
            min-height: 100%;
            overflow-y: auto;
        }}
        .container {{
            max-width: 900px;
            margin: 20px auto;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            overflow: hidden;
            min-height: calc(100% - 40px);
        }}
        .header {{
            background: linear-gradient(135deg, #007acc 0%, #005c99 100%);
            color: white;
            padding: 8px 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 16px;
            font-weight: 600;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .result-header {{
            background-color: #f8f9fa;
            padding: 12px 20px;
            border-bottom: 1px solid #e9ecef;
        }}
        .result-header .date {{
            font-weight: 600;
            color: #495057;
            margin-right: 15px;
        }}
        .result-header .filename {{
            font-weight: 600;
            color: #007acc;
            font-size: 16px;
            text-decoration: none;
            cursor: pointer;
        }}
        .result-header .filename:hover {{
            text-decoration: underline;
            background-color: rgba(0, 122, 204, 0.1);
            padding: 2px 4px;
            border-radius: 4px;
        }}
        .result-filepath {{
            background-color: #f8f9fa;
            padding: 12px 20px;
            border-bottom: 1px solid #e9ecef;
        }}
        .filepath {{
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 13px;
            color: #007acc;
            text-decoration: none;
            word-break: break-all;
        }}
        .filepath:hover {{
            text-decoration: underline;
            background-color: rgba(0, 122, 204, 0.1);
            padding: 2px 4px;
            border-radius: 4px;
        }}
        .result-content {{
            background-color: #ffffff;
            padding: 15px 20px;
            border-bottom: 1px solid #e9ecef;
        }}
        .content {{
            color: #495057;
            font-size: 14px;
            line-height: 1.6;
        }}
        .content strong {{
            color: #212529;
            font-weight: 600;
        }}
        .content p {{
            margin: 0 0 12px 0;
        }}
        .content p:last-child {{
            margin-bottom: 0;
        }}
        .separator {{
            height: 8px;
            background-color: #f8f9fa;
        }}
        .timestamp {{
            color: #6c757d;
            font-size: 12px;
            text-align: center;
            padding: 15px;
            background-color: #f8f9fa;
        }}
    </style>
    <script>
        // Function to open files - supports both WebKit app and browser fallback
        function openFile(filePath) {{
            // Check if we're in an iframe (results are displayed in iframe)
            if (window.parent && window.parent !== window) {{
                // We're in an iframe, call parent window's API
                if (window.parent.openFileNatively) {{
                    window.parent.openFileNatively(filePath);
                }} else {{
                    // Fallback for iframe in browser
                    if (navigator.clipboard) {{
                        navigator.clipboard.writeText(filePath).then(() => {{
                            alert('Dateipfad wurde in die Zwischenablage kopiert:\\n' + filePath);
                        }}).catch(() => {{
                            prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                        }});
                    }} else {{
                        prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                    }}
                }}
            }} else {{
                // We're in the main window
                if (typeof pywebview !== 'undefined' && pywebview.api && pywebview.api.open_file_natively) {{
                    // Use native API for WebKit app
                    pywebview.api.open_file_natively(filePath).then(function(result) {{
                        if (!result.success) {{
                            alert('Fehler beim Öffnen der Datei: ' + result.message);
                        }}
                    }}).catch(function(error) {{
                        alert('Fehler beim Öffnen der Datei: ' + error);
                    }});
                }} else {{
                    // Fallback for browser version
                    if (navigator.clipboard) {{
                        navigator.clipboard.writeText(filePath).then(() => {{
                            alert('Dateipfad wurde in die Zwischenablage kopiert:\\n' + filePath);
                        }}).catch(() => {{
                            prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                        }});
                    }} else {{
                        prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                    }}
                }}
            }}
        }}
        
        // Function to open folder in Finder - supports both WebKit app and browser fallback
        function openFolder(filePath) {{
            // Check if we're in an iframe (results are displayed in iframe)
            if (window.parent && window.parent !== window) {{
                // We're in an iframe, call parent window's API
                if (window.parent.openFolderInFinder) {{
                    window.parent.openFolderInFinder(filePath);
                }} else {{
                    // Fallback for iframe in browser
                    if (navigator.clipboard) {{
                        navigator.clipboard.writeText(filePath).then(() => {{
                            alert('Dateipfad wurde in die Zwischenablage kopiert:\\n' + filePath);
                        }}).catch(() => {{
                            prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                        }});
                    }} else {{
                        prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                    }}
                }}
            }} else {{
                // We're in the main window
                if (typeof pywebview !== 'undefined' && pywebview.api && pywebview.api.open_folder_in_finder) {{
                    // Use native API for WebKit app
                    pywebview.api.open_folder_in_finder(filePath).then(function(result) {{
                        if (!result.success) {{
                            alert('Fehler beim Öffnen des Ordners: ' + result.message);
                        }}
                    }}).catch(function(error) {{
                        alert('Fehler beim Öffnen des Ordners: ' + error);
                    }});
                }} else {{
                    // Fallback for browser version
                    if (navigator.clipboard) {{
                        navigator.clipboard.writeText(filePath).then(() => {{
                            alert('Dateipfad wurde in die Zwischenablage kopiert:\\n' + filePath);
                        }}).catch(() => {{
                            prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                        }});
                    }} else {{
                        prompt('Dateipfad (Kopieren mit Cmd+C):', filePath);
                    }}
                }}
            }}
        }}
        
        // For WebKit app integration, you can add:
        // window.openFileNatively = function(filePath) {{
        //     window.webkit?.messageHandlers?.fileOpener?.postMessage(filePath);
        // }};
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Search results</h1>
        </div>
        
        <table>
{table_rows}
        </table>
        
        <div class="timestamp">
            Erstellt am {timestamp}
        </div>
    </div>
</body>
</html>"""

        # Generate stacked table rows
        table_rows = []
        for i, result in enumerate(search_results):
            filename = result.get("filename", "Unbekannte Datei")
            created_at = result.get("created_at", "Unbekanntes Datum")
            file_path = result.get("file_path", "Unbekannter Pfad")
            content_preview = result.get("content_preview", "Kein Inhalt")
            
            # Format date/time to German format without seconds
            formatted_date = self.format_german_datetime(created_at)
            
            # Process content with markdown
            processed_content = self.render_simple_markdown(content_preview)
            
            # Escape HTML for filename only (content is already processed)
            filename = self.escape_html(filename)
            
            # Create JavaScript call for file opening (works better in WebKit apps)
            escaped_path = file_path.replace("'", "\\'")
            
            # Create stacked rows for this result (3 rows: date+filename, filepath, content)
            result_rows = f"""            <!-- Result {i+1} -->
            <tr class="result-header">
                <td>
                    <span class="date">{formatted_date}</span>
                    <a href="#" onclick="openFile('{escaped_path}'); return false;" class="filename">{filename}</a>
                </td>
            </tr>
            <tr class="result-filepath">
                <td><a href="#" onclick="openFolder('{escaped_path}'); return false;" class="filepath">{file_path}</a></td>
            </tr>
            <tr class="result-content">
                <td><div class="content">{processed_content}</div></td>
            </tr>"""
            
            # Add separator between results (except after last one)
            if i < len(search_results) - 1:
                result_rows += """
            <tr class="separator">
                <td></td>
            </tr>"""
            
            table_rows.append(result_rows)
        
        # Generate timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%d.%m.%Y um %H:%M")
        
        # Fill template
        html_output = html_template.format(
            search_terms=", ".join(search_terms),
            result_count=len(search_results),
            table_rows="\n".join(table_rows),
            timestamp=timestamp
        )
        
        return html_output
    
    def escape_html(self, text: str) -> str:
        """Escape HTML characters"""
        if not text:
            return ""
        
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }
        
        for char, escaped in replacements.items():
            text = text.replace(char, escaped)
        
        return text
    
    def format_german_datetime(self, datetime_str: str) -> str:
        """Format datetime to German format DD.MM.YYYY HH:MM"""
        try:
            from datetime import datetime
            if "T" in datetime_str:
                # Parse ISO format: 2025-06-18T22:18:12.098993
                dt = datetime.fromisoformat(datetime_str.split('.')[0])  # Remove milliseconds
                return dt.strftime("%d.%m.%Y %H:%M")
            else:
                return datetime_str  # Return as-is if not recognized format
        except:
            return datetime_str  # Fallback to original
    
    def render_simple_markdown(self, text: str) -> str:
        """Convert simple markdown to HTML, handling literal \\n strings from database"""
        if not text:
            return ""
        
        # First, convert literal \n strings to actual newlines
        text = text.replace('\\n\\n', '\n\n').replace('\\n', '\n')
        
        # Escape HTML to prevent XSS
        text = self.escape_html(text)
        
        # Convert **bold** to <strong>
        import re
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # Convert *italic* to <em> (but avoid double conversion)
        text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
        
        # Split into paragraphs by double line breaks
        paragraphs = re.split(r'\n\n+', text)
        processed_paragraphs = []
        
        for paragraph in paragraphs:
            # Convert single line breaks to <br> within paragraphs
            paragraph = paragraph.replace('\n', '<br>')
            if paragraph.strip():  # Only add non-empty paragraphs
                processed_paragraphs.append(f'<p>{paragraph}</p>')
        
        return ''.join(processed_paragraphs)
    
    def save_html_output(self, html_content: str) -> None:
        """Save HTML content to file"""
        try:
            with open("search_results.html", "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            print(f"Fehler beim Speichern der HTML-Datei: {e}")
    
    def extract_keywords_with_llm(self, query: str) -> List[str]:
        """Extract keywords from German query using enhanced LLM prompt for multi-word support"""
        try:
            keyword_prompt = """Extrahiere alle wichtigen Suchbegriffe aus der deutschen Anfrage. 
Jeder Begriff sollte separat aufgelistet werden.

Beispiele:
"Bitte liste alle Dateien auf, die das Wort Ihring beinhalten" → Ihring
"Finde Dateien über BMW" → BMW  
"Suche nach Dokumenten mit Anke oder Familie" → Anke, Familie
"Zeige mir Dateien über Ihring und BMW" → Ihring, BMW
"Finde alle PDF-Dateien mit Vertrag und Sparkasse" → PDF, Vertrag, Sparkasse
"Hausbegehung Blumenstrasse Dokumente" → Hausbegehung, Blumenstrasse, Dokumente

Antworte nur mit den Begriffen getrennt durch Kommas, keine weiteren Worte.

Input: {query}
Output:""".format(query=query)

            ollama_request = {
                "model": self.model_name,
                "prompt": keyword_prompt,
                "stream": False
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                extracted = result.get("response", "").strip()
                
                # Parse comma-separated keywords and clean them
                if extracted:
                    keywords = []
                    for kw in extracted.split(','):
                        clean_kw = kw.strip().replace('"', '').replace("'", '')
                        if clean_kw and len(clean_kw) > 1:  # Only meaningful terms
                            keywords.append(clean_kw)
                    return keywords if keywords else ["Ihring"]  # Fallback
                else:
                    return ["Ihring"]  # Fallback
            else:
                return ["Ihring"]  # Fallback
                
        except Exception as e:
            print(f"DEBUG: Keyword extraction failed: {e}")
            return ["Ihring"]  # Fallback

    def search_files_with_keywords(self, keywords: List[str], search_mode: str = "OR") -> List[Dict[str, Any]]:
        """Search files using MCP server with extracted keywords - simplified for reliability"""
        if not self.mcp_process or not self.mcp_initialized:
            return []
        
        try:
            # Use simple getData instead of complex auto mode for now
            # This avoids the auto-mode complexity that might be causing JSON issues
            
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "getData",
                    "arguments": {
                        "search_terms": keywords,
                        "search_mode": search_mode
                    }
                }
            }
            
            request_json = json.dumps(mcp_request) + "\n"
            print(f"DEBUG: Sending MCP request: {request_json.strip()}")
            self.mcp_process.stdin.write(request_json)
            self.mcp_process.stdin.flush()
            
            # Read response with timeout
            import select
            ready, _, _ = select.select([self.mcp_process.stdout], [], [], 10.0)
            
            if ready:
                response_line = self.mcp_process.stdout.readline()
                print(f"DEBUG: Raw response: {repr(response_line)}")
                
                if response_line and response_line.strip():
                    try:
                        response = json.loads(response_line)
                        print(f"DEBUG MCP Response: {response}")
                        
                        if "result" in response and "content" in response["result"]:
                            content = response["result"]["content"]
                            if isinstance(content, list) and len(content) > 0:
                                results = []
                                for item in content:
                                    if isinstance(item, dict) and "text" in item:
                                        text_content = item["text"]
                                        try:
                                            parsed_result = json.loads(text_content)
                                            results.append(parsed_result)
                                        except json.JSONDecodeError as e:
                                            print(f"DEBUG JSON Parse Error for item: {e}")
                                            results.append({"raw_response": text_content})
                                
                                print(f"DEBUG Parsed Results: {len(results)} items")
                                return results
                            else:
                                print(f"DEBUG: Empty or invalid content: {content}")
                                return []
                        elif "error" in response:
                            print(f"MCP-Fehler: {response['error']}")
                            return []
                        else:
                            print(f"DEBUG: Unexpected response structure: {response}")
                            return []
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: Failed to parse JSON: {e}")
                        print(f"DEBUG: Response content: {repr(response_line)}")
                        return []
                else:
                    print("DEBUG: Empty response from server")
                    return []
            else:
                print("Timeout beim Warten auf MCP-Antwort")
                return []
            
        except Exception as e:
            print(f"MCP-Suchfehler: {e}")
            import traceback
            traceback.print_exc()
            return []

    def call_ollama_with_function_calling(self, query: str) -> str:
        """Call Ollama with Llama 3.2 function calling format"""
        try:
            # Combine system prompt with user query
            full_prompt = f"{self.system_prompt}\n\nUser query: {query}"
            
            ollama_request = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False
            }
            
            print("🤖 Denke nach...")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            ollama_response = result.get("response", "").strip()
            
            print(f"DEBUG: LLM Response: {ollama_response}")
            
            # Parse function call format: [getData(search_terms=['Ihring'])]
            if ollama_response.startswith('[') and ollama_response.endswith(']'):
                function_call = ollama_response[1:-1]  # Remove brackets
                
                # Parse function name and parameters
                if '(' in function_call and ')' in function_call:
                    func_name = function_call.split('(')[0]
                    params_str = function_call.split('(', 1)[1].rsplit(')', 1)[0]
                    
                    print(f"DEBUG: Function: {func_name}, Params: {params_str}")
                    
                    if func_name == "getData":
                        # Parse search_terms parameter
                        search_terms = self.parse_search_terms(params_str)
                        print(f"DEBUG: Parsed search terms: {search_terms}")
                        
                        # Call MCP server with OR mode (simplified)
                        search_results = self.search_files_with_keywords(search_terms, "OR")
                        
                        # Generate HTML table for results
                        if search_results:
                            html_output = self.generate_html_table(search_results, search_terms)
                            self.save_html_output(html_output)
                            return f"HTML-Tabelle mit {len(search_results)} Ergebnissen für '{', '.join(search_terms)}' wurde erstellt und in 'search_results.html' gespeichert."
                        else:
                            return f"Keine Dateien gefunden, die '{', '.join(search_terms)}' enthalten."
                    
                    elif func_name == "get_database_stats":
                        # Call database stats
                        stats = self.get_database_stats()
                        if stats:
                            return f"**Datenbankstatistiken:**\n\nGesamte Dateien: {stats.get('total_files', 'Unbekannt')}\nStatus: {stats.get('status', 'Unbekannt')}"
                        else:
                            return "Datenbankstatistiken konnten nicht abgerufen werden."
                    
                    else:
                        return f"Unbekannte Funktion: {func_name}"
                else:
                    return "Fehlerhafte Funktionsaufruf-Syntax"
            else:
                # If no function call, return the response as is
                return ollama_response
                
        except Exception as e:
            return f"Fehler bei der Verarbeitung: {e}"

    def parse_search_terms(self, params_str: str) -> List[str]:
        """Parse search_terms from function parameter string"""
        try:
            import re
            # Look for search_terms=['term1', 'term2'] pattern
            match = re.search(r"search_terms\s*=\s*\[([^\]]+)\]", params_str)
            if match:
                terms_str = match.group(1)
                # Extract quoted terms
                terms = re.findall(r"'([^']*)'|\"([^\"]*)\"", terms_str)
                # Flatten and clean
                search_terms = [term[0] or term[1] for term in terms if term[0] or term[1]]
                return search_terms if search_terms else ["Ihring"]
            else:
                return ["Ihring"]  # Fallback
        except:
            return ["Ihring"]  # Fallback

    def call_ollama_with_tools(self, query: str) -> str:
        """Call Ollama and let it decide which tools to use"""
        try:
            # Create prompt that tells Ollama to extract keywords and call tools
            full_prompt = f"""{self.system_prompt}

Benutzer-Frage: {query}

Analysiere die Frage und extrahiere die relevanten Suchbegriffe. Rufe dann getData mit diesen Begriffen auf und präsentiere die Ergebnisse.

Für die Frage "{query}" solltest du:
1. Die relevanten Suchbegriffe extrahieren 
2. getData mit diesen Begriffen aufrufen
3. Die Ergebnisse in einer hilfreichen Antwort präsentieren
"""
            
            print("🤖 Denke nach...")
            
            # Call Ollama API
            ollama_request = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            ollama_response = result.get("response", "Keine Antwort von Ollama")
            
            # Check if Ollama wants to call a tool (look for function calls in response)
            if "getData" in ollama_response or "get_database_stats" in ollama_response:
                # For now, extract "Ihring" manually and call tools
                search_results = self.search_files("Ihring") 
                context = self.prepare_context(search_results)
                return self.call_ollama(query, context)
            else:
                return ollama_response
            
        except Exception as e:
            return f"Fehler beim Verarbeiten der Anfrage: {e}"

    def call_ollama(self, query: str, context: str) -> str:
        """Call Ollama API with query and context"""
        try:
            # Combine system prompt, context, and user query
            full_prompt = f"{self.system_prompt}\n\nKontext:\n{context}\n\nBenutzer-Frage: {query}\n\nBitte gib eine hilfreiche Antwort basierend auf dem obigen Kontext."
            
            # Prepare Ollama request
            ollama_request = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False
            }
            
            print("🤖 Denke nach...")
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "Keine Antwort von Ollama")
            
        except requests.exceptions.RequestException as e:
            return f"Fehler beim Aufruf von Ollama: {e}"
        except Exception as e:
            return f"Unerwarteter Fehler: {e}"
    
    def process_query(self, query: str) -> str:
        """Process user query with MCP and Ollama"""
        try:
            # Special handling for tool inquiry
            if "tool" in query.lower() or "werkzeug" in query.lower() or "funktion" in query.lower():
                if self.available_tools:
                    tools_info = "Verfügbare MCP-Tools:\n"
                    for tool in self.available_tools:
                        tools_info += f"- {tool['name']}: {tool.get('description', 'Keine Beschreibung')}\n"
                    
                    # Also get database stats
                    stats = self.get_database_stats()
                    if stats:
                        stats_context = f"Datenbankstatistiken: {json.dumps(stats, indent=2)}"
                    else:
                        stats_context = "Datenbankstatistiken nicht verfügbar"
                    
                    context = f"{tools_info}\n{stats_context}"
                else:
                    context = "MCP-Tools konnten nicht geladen werden"
                
                return self.call_ollama(query, context)
            
            print("🔍 Verarbeite Anfrage...")
            
            # Let Ollama handle everything: extract keywords AND call functions
            response = self.call_ollama_with_function_calling(query)
            
            return response
            
        except Exception as e:
            return f"Fehler bei der Verarbeitung der Anfrage: {e}"
    
    def run(self):
        """Main application loop"""
        print("=" * 60)
        print("🔍 MCP Dateisuch-Client (Deutsch)")
        print("=" * 60)
        
        # Check prerequisites
        if not Path("server.py").exists():
            print("✗ Fehler: server.py nicht im aktuellen Verzeichnis gefunden!")
            return
        
        if not Path("system_prompt.txt").exists():
            print("⚠ Warnung: system_prompt.txt nicht gefunden. Erstelle Standard-Datei.")
        
        # Test connections
        if not self.test_ollama_connection():
            print("Bitte stellen Sie sicher, dass Ollama läuft und llama3.2:latest installiert ist")
            return
        
        if not self.start_mcp_server():
            print("Bitte überprüfen Sie die MCP-Server-Konfiguration")
            return
        
        print("\n" + "=" * 60)
        print("Bereit! Stellen Sie Fragen oder geben Sie 'quit' zum Beenden ein")
        print("Beispiele: 'Finde Dateien über Familie' oder 'Zeige mir aktuelle Dokumente'")
        print("          'Welche Tools hast du?' oder 'Was sind deine Funktionen?'")
        print("=" * 60 + "\n")
        
        try:
            while self.running:
                try:
                    user_input = input("\n📝 Sie: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['quit', 'exit', 'q', 'beenden', 'ende']:
                        break
                    
                    # Process query
                    response = self.process_query(user_input)
                    
                    print(f"\n🤖 Assistent: {response}")
                    print("-" * 60)
                    
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                    
        finally:
            print("\nRäume auf...")
            if self.mcp_process:
                self.mcp_process.terminate()
                self.mcp_process.wait()
            print("Auf Wiedersehen!")

def main():
    """Main function"""
    client = MCPClientTerminal()
    client.run()

if __name__ == "__main__":
    main()