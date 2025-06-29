# MCP File Search Client

A graphical and terminal-based client for the MCP File Search Server that uses Ollama's llama3.2 model for intelligent file search responses.

## Components

### 1. GUI Client (mcp_client_gui.py)
- **Tkinter-based graphical interface**
- Chat-style interface with input field and output area
- Automatic MCP server startup
- Real-time status updates

**Note**: Requires tkinter to be available in your Python environment.

### 2. Terminal Client (mcp_client_terminal.py) 
- **Command-line interface** (recommended if tkinter unavailable)
- Interactive chat in terminal
- Connection testing for both MCP server and Ollama
- Graceful error handling and shutdown

### 3. System Prompt (system_prompt.txt)
- **Configurable AI behavior**
- Specialized for file search assistance
- Easy to modify for different use cases

## Requirements

- Python 3.11+
- Ollama running on localhost:11434
- llama3.2:latest model installed in Ollama
- MCP server (server.py) in same directory
- SQLite database with indexed documents

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Ensure Ollama is running:
```bash
# Check if Ollama is running and has the model
ollama list
# Should show llama3.2:latest
```

3. Verify MCP server works:
```bash
python server.py
# Should start without errors
```

## Usage

### Terminal Client (Recommended)
```bash
python mcp_client_terminal.py
```

### GUI Client
```bash
python mcp_client_gui.py
```

## Features

### File Search Capabilities
- **Content search**: Find files by text content
- **Category filtering**: Search by document categories
- **Person search**: Find documents mentioning specific people  
- **Date range**: Filter by creation dates
- **File type**: Search by extension
- **Filename patterns**: Wildcard filename matching

### AI Integration
- Uses Ollama llama3.2:latest for natural language responses
- Truncates content to 100 characters as requested
- Returns file paths and relevant content excerpts
- Contextual responses based on search results

### User Interface
- **Terminal**: Simple command-line chat interface
- **GUI**: Graphical chat window with send button
- **Status updates**: Connection status and processing feedback
- **Error handling**: Clear error messages and recovery

## Example Queries

- "Find files about Familie"
- "Show me documents from 2024"
- "What files mention BMW?"
- "Find PDFs in my documents"
- "Show me recent contracts"

## Configuration

### System Prompt
Edit `system_prompt.txt` to customize AI behavior:
- Change response style
- Add specific instructions
- Modify search priorities

### Ollama Model
To use a different model, edit the `model_name` variable in the client files.

### Search Limits
Modify the `limit` parameter in search functions to return more/fewer results.

## Troubleshooting

### Common Issues

1. **Tkinter not available**:
   - Use the terminal client instead
   - Or install tkinter: `brew install python-tk` (macOS)

2. **Ollama connection failed**:
   - Check if Ollama is running: `curl http://localhost:11434/api/tags`
   - Verify model exists: `ollama list`

3. **MCP server won't start**:
   - Check if server.py exists in current directory
   - Verify database path in server.py
   - Check Python dependencies

4. **No search results**:
   - Verify database contains data
   - Check database path in server.py
   - Try different search terms

### Debug Mode
Add debug prints to see MCP communication:
```python
print(f"MCP Request: {mcp_request}")
print(f"MCP Response: {response}")
```

## Architecture

```
User Input
    ↓
Terminal/GUI Client
    ↓
MCP Server (server.py)
    ↓
SQLite Database
    ↓
Search Results
    ↓
Ollama llama3.2
    ↓
AI Response
    ↓
Display to User
```

The client handles:
- User interface and input
- MCP server communication
- Search result processing
- Ollama API integration
- Response formatting and display