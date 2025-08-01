#!/usr/bin/env python3
"""
Native macOS App for Document Search Client
Integrates React frontend with Flask backend in PyWebView
"""

import webview
import subprocess
import threading
import time
import json
import requests
from pathlib import Path
import os
import signal
import sys

class DocumentSearchApp:
    def __init__(self):
        self.flask_process = None
        self.react_process = None
        self.flask_port = 5001
        self.react_port = 3000
        self.base_url = f"http://localhost:{self.flask_port}"
        
    def create_menu(self):
        """Create native macOS menu bar"""
        # PyWebView 5.4+ doesn't support custom menus the same way
        # We'll use keyboard shortcuts instead
        return None
    
    def new_search(self):
        """Clear search and focus input"""
        webview.windows[0].evaluate_js("""
            document.querySelector('input[type="text"]').value = '';
            document.querySelector('input[type="text"]').focus();
        """)
    
    def quit_app(self):
        """Quit the application"""
        self.cleanup()
        sys.exit(0)
    
    def copy_selection(self):
        """Copy selected text to clipboard"""
        webview.windows[0].evaluate_js("document.execCommand('copy')")
    
    def paste_text(self):
        """Paste text from clipboard"""
        webview.windows[0].evaluate_js("document.execCommand('paste')")
    
    def select_all(self):
        """Select all text"""
        webview.windows[0].evaluate_js("document.execCommand('selectAll')")
    
    def reload_page(self):
        """Reload the current page"""
        webview.windows[0].reload()
    
    def toggle_dev_tools(self):
        """Toggle developer tools"""
        webview.windows[0].evaluate_js("window.open('', '_blank')")
    
    def start_flask_server(self):
        """Start Flask backend server"""
        print("Starting Flask backend server...")
        backend_dir = Path(__file__).parent / "file-search-client" / "backend"
        
        if not backend_dir.exists():
            print(f"Error: Backend directory not found at {backend_dir}")
            return False
            
        try:
            # Change to backend directory and start Flask
            self.flask_process = subprocess.Popen([
                sys.executable, "app.py"
            ], cwd=backend_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for Flask to start
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.post(f"{self.base_url}/api/search", 
                                           json={"query": "test"}, timeout=1)
                    if response.status_code in [200, 400]:  # 400 is expected for empty query
                        print("Flask server started successfully")
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(1)
            
            print("Flask server failed to start")
            return False
            
        except Exception as e:
            print(f"Error starting Flask server: {e}")
            return False
    
    def start_react_server(self):
        """Start React development server"""
        print("Starting React frontend server...")
        frontend_dir = Path(__file__).parent / "file-search-client" / "frontend"
        
        if not frontend_dir.exists():
            print(f"Error: Frontend directory not found at {frontend_dir}")
            return False
            
        try:
            # Check if node_modules exists
            if not (frontend_dir / "node_modules").exists():
                print("Installing npm dependencies...")
                subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
            
            # Start React development server
            env = os.environ.copy()
            env["BROWSER"] = "none"  # Prevent auto-opening browser
            env["PORT"] = str(self.react_port)
            
            self.react_process = subprocess.Popen([
                "npm", "start"
            ], cwd=frontend_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for React to start
            max_attempts = 60  # React takes longer to start
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"http://localhost:{self.react_port}", timeout=1)
                    if response.status_code == 200:
                        print("React server started successfully")
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(1)
            
            print("React server failed to start")
            return False
            
        except Exception as e:
            print(f"Error starting React server: {e}")
            return False
    
    def cleanup(self):
        """Clean up processes on exit"""
        print("Cleaning up processes...")
        
        if self.flask_process:
            try:
                self.flask_process.terminate()
                self.flask_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.flask_process.kill()
            except Exception as e:
                print(f"Error terminating Flask process: {e}")
        
        if self.react_process:
            try:
                self.react_process.terminate()
                self.react_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.react_process.kill()
            except Exception as e:
                print(f"Error terminating React process: {e}")
    
    def wait_for_servers(self):
        """Wait for both servers to be ready"""
        print("Waiting for servers to be ready...")
        
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=self.start_flask_server)
        flask_thread.daemon = True
        flask_thread.start()
        
        # Start React in a separate thread  
        react_thread = threading.Thread(target=self.start_react_server)
        react_thread.daemon = True
        react_thread.start()
        
        # Wait for both threads to complete
        flask_thread.join(timeout=30)
        react_thread.join(timeout=60)
        
        # Verify both servers are running
        flask_ready = False
        react_ready = False
        
        try:
            response = requests.post(f"{self.base_url}/api/search", 
                                   json={"query": "test"}, timeout=2)
            flask_ready = response.status_code in [200, 400]
        except:
            pass
            
        try:
            response = requests.get(f"http://localhost:{self.react_port}", timeout=2)
            react_ready = response.status_code == 200
        except:
            pass
            
        return flask_ready and react_ready
    
    def start_app(self):
        """Start the native macOS application"""
        print("=" * 60)
        print("🔍 Document Search - Native macOS App")
        print("=" * 60)
        
        # Set up signal handlers for clean shutdown
        def signal_handler(sig, frame):
            print("\nShutting down...")
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start backend servers
        if not self.wait_for_servers():
            print("Failed to start backend servers")
            return
        
        print(f"Servers ready! Opening native app...")
        print(f"Flask backend: {self.base_url}")
        print(f"React frontend: http://localhost:{self.react_port}")
        
        try:
            # Create native window
            webview.create_window(
                'Document Search',
                url=f"http://localhost:{self.react_port}",
                width=1400,
                height=900,
                min_size=(1000, 700),
                resizable=True,
                maximized=False,
                on_top=False,
                shadow=True,
                vibrancy=True
            )
            
            # Start the app (no custom menu in PyWebView 5.4+)
            webview.start(
                debug=False,
                private_mode=False
            )
            
        except Exception as e:
            print(f"Error starting WebView: {e}")
        finally:
            self.cleanup()

def main():
    """Main function"""
    # Check if PyWebView is available
    try:
        import webview
    except ImportError:
        print("PyWebView is not installed. Please install it with:")
        print("pip install pywebview")
        sys.exit(1)
    
    # Check if required directories exist
    app_dir = Path(__file__).parent
    if not (app_dir / "file-search-client").exists():
        print("Error: file-search-client directory not found")
        print("Please make sure the React/Flask application is in the correct location")
        sys.exit(1)
    
    app = DocumentSearchApp()
    app.start_app()

if __name__ == "__main__":
    main()