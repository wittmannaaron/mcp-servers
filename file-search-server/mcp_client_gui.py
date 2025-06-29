#!/usr/bin/env python3
"""
MCP Client GUI for File Search Server
Connects to the file search MCP server and uses Ollama llama3.2 for responses
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import asyncio
import threading
import json
import subprocess
import sys
from pathlib import Path
import requests
from typing import Dict, List, Any, Optional
import time

class MCPClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MCP File Search Client")
        self.root.geometry("900x700")
        
        # MCP server process
        self.mcp_process = None
        self.ollama_url = "http://localhost:11434"
        self.model_name = "llama3.2:latest"
        
        # Load system prompt
        self.system_prompt = self.load_system_prompt()
        
        self.setup_gui()
        self.start_mcp_server()
        
    def load_system_prompt(self) -> str:
        """Load system prompt from file"""
        try:
            with open("system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "You are a helpful file search assistant. Help users find and understand their files."
    
    def setup_gui(self):
        """Create the GUI layout"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="File Search Assistant", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # Output text area
        output_frame = ttk.LabelFrame(main_frame, text="Assistant Response", padding="5")
        output_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(
            output_frame, 
            wrap=tk.WORD, 
            height=20, 
            state=tk.DISABLED,
            font=("Consolas", 10)
        )
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        
        # Input field
        ttk.Label(input_frame, text="Your question:").grid(row=0, column=0, sticky=tk.W)
        self.input_text = tk.Text(input_frame, height=3, font=("Arial", 11))
        self.input_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Send button
        self.send_button = ttk.Button(
            input_frame, 
            text="Send", 
            command=self.on_send_click
        )
        self.send_button.grid(row=2, column=1, sticky=tk.E, pady=(5, 0))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Starting MCP server...")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, font=("Arial", 9))
        status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        # Bind Enter key to send
        self.input_text.bind('<Control-Return>', lambda e: self.on_send_click())
        
    def start_mcp_server(self):
        """Start the MCP server in background"""
        def start_server():
            try:
                self.mcp_process = subprocess.Popen(
                    [sys.executable, "server.py"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=0
                )
                self.root.after(1000, lambda: self.status_var.set("MCP server started. Ready to chat."))
            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Failed to start MCP server: {e}"))
        
        threading.Thread(target=start_server, daemon=True).start()
    
    def on_send_click(self):
        """Handle send button click"""
        query = self.input_text.get("1.0", tk.END).strip()
        if not query:
            return
            
        # Clear input
        self.input_text.delete("1.0", tk.END)
        
        # Show user message
        self.append_output(f"You: {query}\n\n", "user")
        
        # Disable send button
        self.send_button.config(state=tk.DISABLED)
        self.status_var.set("Processing...")
        
        # Process query in background
        threading.Thread(target=self.process_query, args=(query,), daemon=True).start()
    
    def process_query(self, query: str):
        """Process user query with MCP and Ollama"""
        try:
            # First, try to extract search intent and call MCP tools
            search_results = self.search_files(query)
            
            # Prepare context for Ollama
            context = self.prepare_context(search_results)
            
            # Call Ollama with context
            response = self.call_ollama(query, context)
            
            # Display response
            self.root.after(0, lambda: self.append_output(f"Assistant: {response}\n\n", "assistant"))
            
        except Exception as e:
            self.root.after(0, lambda: self.show_error(f"Error processing query: {e}"))
        finally:
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_var.set("Ready"))
    
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
            
            # Read response
            response_line = self.mcp_process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                if "result" in response and "content" in response["result"]:
                    # Parse the content (it's usually a list)
                    content = response["result"]["content"]
                    if isinstance(content, list) and len(content) > 0:
                        # The first item should contain our search results
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
            if isinstance(result, dict) and "path" in result:
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
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "No response from Ollama")
            
        except requests.exceptions.RequestException as e:
            return f"Error calling Ollama: {e}"
        except Exception as e:
            return f"Unexpected error: {e}"
    
    def append_output(self, text: str, tag: str = ""):
        """Append text to output area"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        
        # Configure tags for styling
        if tag == "user":
            # Find the last occurrence of the text to apply tag
            start = self.output_text.search(text.split('\n')[0], tk.END, backwards=True)
            if start:
                end = f"{start}+{len(text.split()[0])+1}c"
                self.output_text.tag_add("user", start, end)
                self.output_text.tag_config("user", foreground="blue", font=("Arial", 10, "bold"))
        elif tag == "assistant":
            start = self.output_text.search("Assistant:", tk.END, backwards=True)
            if start:
                end = f"{start}+10c"
                self.output_text.tag_add("assistant", start, end)
                self.output_text.tag_config("assistant", foreground="green", font=("Arial", 10, "bold"))
        
        self.output_text.config(state=tk.DISABLED)
        self.output_text.see(tk.END)
    
    def show_error(self, message: str):
        """Show error message"""
        self.append_output(f"Error: {message}\n\n", "error")
        self.output_text.tag_config("error", foreground="red")
        self.send_button.config(state=tk.NORMAL)
        self.status_var.set("Ready")
    
    def on_closing(self):
        """Handle application closing"""
        if self.mcp_process:
            self.mcp_process.terminate()
            self.mcp_process.wait()
        self.root.destroy()

def main():
    """Main function"""
    # Check if system_prompt.txt exists
    if not Path("system_prompt.txt").exists():
        print("Warning: system_prompt.txt not found. Creating default one.")
    
    # Check if server.py exists
    if not Path("server.py").exists():
        print("Error: server.py not found in current directory!")
        return
    
    # Create and run GUI
    root = tk.Tk()
    app = MCPClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()