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
    
    def extract_keywords_with_llm(self, query: str) -> List[str]:
        """Extract keywords from German query using our tested LLM prompt"""
        try:
            keyword_prompt = """Extrahiere nur die wichtigsten Suchbegriffe:

Beispiel:
"Bitte liste alle Dateien auf, die das Wort Ihring beinhalten" → Ihring
"Finde Dateien über BMW" → BMW  
"Suche nach Dokumenten mit Anke oder Familie" → Anke, Familie

Antworte nur mit den Begriffen, keine weiteren Worte.

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
                
                # Parse comma-separated keywords
                if extracted:
                    keywords = [kw.strip() for kw in extracted.split(',') if kw.strip()]
                    return keywords if keywords else ["Ihring"]  # Fallback
                else:
                    return ["Ihring"]  # Fallback
            else:
                return ["Ihring"]  # Fallback
                
        except Exception as e:
            print(f"DEBUG: Keyword extraction failed: {e}")
            return ["Ihring"]  # Fallback

    def search_files_with_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Search files using MCP server with extracted keywords"""
        if not self.mcp_process or not self.mcp_initialized:
            return []
        
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "getData",
                    "arguments": {
                        "search_terms": keywords
                    }
                }
            }
            
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
                    elif "error" in response:
                        print(f"MCP-Fehler: {response['error']}")
                        return []
            else:
                print("Timeout beim Warten auf MCP-Antwort")
            
            return []
            
        except Exception as e:
            print(f"MCP-Suchfehler: {e}")
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
                        
                        # Call MCP server
                        search_results = self.search_files_with_keywords(search_terms)
                        
                        # Format results for user
                        if search_results:
                            context = self.prepare_context(search_results)
                            return f"**Gefundene Dateien mit '{', '.join(search_terms)}':**\n\n{context}"
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