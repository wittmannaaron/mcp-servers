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
            # Create MCP request for general content search
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "search_file_content",
                    "arguments": {
                        "query": query,
                        "limit": 10
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
                            text_content = content[0].get("text", "")
                            try:
                                results = json.loads(text_content)
                                print(f"DEBUG Parsed Results: {len(results) if isinstance(results, list) else 'Not a list'}")
                                return results if isinstance(results, list) else []
                            except json.JSONDecodeError as e:
                                print(f"DEBUG JSON Parse Error: {e}")
                                # If it's not JSON, treat as raw text result
                                return [{"raw_response": text_content}]
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
        
        context_parts = ["Gefundene Dateien:"]
        
        for result in search_results[:5]:  # Limit to top 5 results
            if isinstance(result, dict):
                if "raw_response" in result:
                    # Handle raw response
                    context_parts.append(f"- Ergebnis: {result['raw_response'][:200]}...")
                elif "path" in result or "file_path" in result:
                    file_path = result.get("path", result.get("file_path", "Unbekannter Pfad"))
                    filename = result.get("filename", "Unbekannte Datei")
                    
                    # Get content and truncate
                    content = result.get("markdown_content", result.get("summary", "Kein Inhalt verfügbar"))
                    if content and len(content) > 100:
                        content = content[:100] + "..."
                    
                    context_parts.append(f"- Datei: {filename}")
                    context_parts.append(f"  Pfad: {file_path}")
                    if content:
                        context_parts.append(f"  Inhalt: {content}")
                    context_parts.append("")
        
        return "\n".join(context_parts)
    
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
            
            print("🔍 Durchsuche Dateien...")
            
            # Search files using MCP
            search_results = self.search_files(query)
            
            # Prepare context for Ollama
            context = self.prepare_context(search_results)
            
            # Call Ollama with context
            response = self.call_ollama(query, context)
            
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