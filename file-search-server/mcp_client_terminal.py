#!/usr/bin/env python3
"""
MCP Client Terminal Interface for File Search Server
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

class MCPClientTerminal:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model_name = "llama3.2:latest"
        self.mcp_process = None
        self.running = True
        
        # Load system prompt
        self.system_prompt = self.load_system_prompt()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\nShutting down...")
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
            return "You are a helpful file search assistant. Help users find and understand their files."
    
    def start_mcp_server(self) -> bool:
        """Start the MCP server"""
        try:
            print("Starting MCP server...")
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
                print("✓ MCP server started successfully")
                return True
            else:
                print("✗ MCP server failed to start")
                return False
                
        except Exception as e:
            print(f"✗ Failed to start MCP server: {e}")
            return False
    
    def test_ollama_connection(self) -> bool:
        """Test connection to Ollama"""
        try:
            print("Testing Ollama connection...")
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json()
                model_names = [model['name'] for model in models.get('models', [])]
                if self.model_name in model_names:
                    print(f"✓ Ollama connected, {self.model_name} available")
                    return True
                else:
                    print(f"✗ Model {self.model_name} not found in Ollama")
                    print(f"Available models: {model_names}")
                    return False
            else:
                print(f"✗ Ollama not responding (status: {response.status_code})")
                return False
        except Exception as e:
            print(f"✗ Cannot connect to Ollama: {e}")
            return False
    
    def search_files(self, query: str) -> List[Dict[str, Any]]:
        """Search files using MCP server"""
        if not self.mcp_process:
            return []
        
        try:
            # Create MCP request for general content search
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
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
                                return []
            
            return []
            
        except Exception as e:
            print(f"MCP search error: {e}")
            return []
    
    def prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Prepare context from search results for Ollama"""
        if not search_results:
            return "No files found matching your query."
        
        context_parts = ["Found files:"]
        
        for result in search_results[:5]:  # Limit to top 5 results
            if isinstance(result, dict) and ("path" in result or "file_path" in result):
                file_path = result.get("path", result.get("file_path", "Unknown path"))
                
                # Get markdown content and truncate
                markdown_content = result.get("markdown_content", result.get("summary", "No content available"))
                if markdown_content and len(markdown_content) > 100:
                    markdown_content = markdown_content[:100] + "..."
                
                context_parts.append(f"- File: {file_path}")
                if markdown_content:
                    context_parts.append(f"  Content: {markdown_content}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def call_ollama(self, query: str, context: str) -> str:
        """Call Ollama API with query and context"""
        try:
            # Combine system prompt, context, and user query
            full_prompt = f"{self.system_prompt}\n\nContext:\n{context}\n\nUser question: {query}\n\nPlease provide a helpful response based on the context above."
            
            # Prepare Ollama request
            ollama_request = {
                "model": self.model_name,
                "prompt": full_prompt,
                "stream": False
            }
            
            print("🤖 Thinking...")
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "No response from Ollama")
            
        except requests.exceptions.RequestException as e:
            return f"Error calling Ollama: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
    
    def process_query(self, query: str) -> str:
        """Process user query with MCP and Ollama"""
        try:
            print("🔍 Searching files...")
            
            # Search files using MCP
            search_results = self.search_files(query)
            
            # Prepare context for Ollama
            context = self.prepare_context(search_results)
            
            # Call Ollama with context
            response = self.call_ollama(query, context)
            
            return response
            
        except Exception as e:
            return f"Error processing query: {e}"
    
    def run(self):
        """Main application loop"""
        print("=" * 60)
        print("🔍 MCP File Search Client")
        print("=" * 60)
        
        # Check prerequisites
        if not Path("server.py").exists():
            print("✗ Error: server.py not found in current directory!")
            return
        
        if not Path("system_prompt.txt").exists():
            print("⚠ Warning: system_prompt.txt not found. Creating default one.")
        
        # Test connections
        if not self.test_ollama_connection():
            print("Please make sure Ollama is running and llama3.2:latest is installed")
            return
        
        if not self.start_mcp_server():
            print("Please check the MCP server configuration")
            return
        
        print("\n" + "=" * 60)
        print("Ready! Type your questions or 'quit' to exit")
        print("Example: 'Find files about Familie' or 'Show me recent documents'")
        print("=" * 60 + "\n")
        
        try:
            while self.running:
                try:
                    user_input = input("\n📝 You: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    # Process query
                    response = self.process_query(user_input)
                    
                    print(f"\n🤖 Assistant: {response}")
                    print("-" * 60)
                    
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                    
        finally:
            print("\nCleaning up...")
            if self.mcp_process:
                self.mcp_process.terminate()
                self.mcp_process.wait()
            print("Goodbye!")

def main():
    """Main function"""
    client = MCPClientTerminal()
    client.run()

if __name__ == "__main__":
    main()