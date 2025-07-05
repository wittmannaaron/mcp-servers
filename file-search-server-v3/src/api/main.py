import asyncio
import os
from typing import Optional
from contextlib import AsyncExitStack

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ollama
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

app = FastAPI(title="FileBrowser MCP API", version="1.0.0")

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str

class MCPChatClient:
    def __init__(self):
        """Initialize the MCP Chat Client with Ollama"""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.ollama_client = ollama.AsyncClient()
        self._connected = False
        self.model = "llama3.2:latest"
        logger.info("MCPChatClient initialized with Ollama")

    async def connect_to_servers(self):
        """Connect to the SQLite MCP server"""
        if self._connected:
            return

        try:
            # Path to the SQLite MCP server (absolute path)
            server_script_path = os.path.abspath("docs/MCP-Servers-src/sqlite_MCP_Server/src/mcp_server_sqlite/server.py")
            database_path = os.path.abspath("src/database/filebrowser.db")

            # Check if server script exists
            if not os.path.exists(server_script_path):
                raise FileNotFoundError(f"SQLite MCP server not found at {server_script_path}")

            # Check if database exists
            if not os.path.exists(database_path):
                logger.warning(f"Database not found at {database_path}, will be created by MCP server")

            # Set up server parameters for Python script
            server_params = StdioServerParameters(
                command="python",
                args=[server_script_path, database_path],
                env=os.environ.copy()
            )

            # Connect to the server
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )

            # Initialize the session
            await self.session.initialize()

            # List available tools for verification
            response = await self.session.list_tools()
            tools = response.tools
            tool_names = [tool.name for tool in tools]
            logger.info(f"Connected to SQLite MCP server with tools: {tool_names}")

            self._connected = True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available MCP tools"""
        try:
            # Ensure we're connected to servers
            await self.connect_to_servers()

            # Build the conversation messages
            messages = [
                {
                    "role": "user",
                    "content": query
                }
            ]

            # Get available tools from the MCP server
            response = await self.session.list_tools()
            available_tools = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            } for tool in response.tools]

            logger.info(f"Processing query with {len(available_tools)} available tools")

            # Initial Ollama API call
            response = await self.ollama_client.chat(
                model=self.model,
                messages=messages,
                tools=available_tools
            )

            # Process response and handle tool calls
            final_text = []

            # Handle the response content
            if hasattr(response, 'message'):
                message = response.message

                # Check if there's text content
                if hasattr(message, 'content') and message.content:
                    final_text.append(message.content)

                # Check for tool calls
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Add assistant message to conversation
                    messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": message.tool_calls
                    })

                    # Process each tool call
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = tool_call.function.arguments

                        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                        try:
                            # Execute tool call via MCP
                            result = await self.session.call_tool(tool_name, tool_args)
                            tool_result_content = []

                            # Extract content from tool result
                            for item in result.content:
                                if hasattr(item, 'text'):
                                    tool_result_content.append(item.text)

                            tool_result_text = "\n".join(tool_result_content)
                            logger.info(f"Tool {tool_name} result: {tool_result_text[:200]}...")

                            # Add tool result to conversation
                            messages.append({
                                "role": "tool",
                                "content": tool_result_text,
                                "tool_call_id": tool_call.id
                            })

                        except Exception as tool_error:
                            logger.error(f"Tool execution failed: {tool_error}")
                            # Add error message as tool result
                            messages.append({
                                "role": "tool",
                                "content": f"Error executing {tool_name}: {str(tool_error)}",
                                "tool_call_id": tool_call.id
                            })

                    # Get next response from Ollama after tool execution
                    response = await self.ollama_client.chat(
                        model=self.model,
                        messages=messages,
                        tools=available_tools
                    )

                    # Add Ollama's final response to final text
                    if hasattr(response, 'message') and hasattr(response.message, 'content'):
                        final_text.append(response.message.content)

            return "\n".join(final_text) if final_text else "I apologize, but I couldn't generate a response."

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.exit_stack.aclose()
            self._connected = False
            logger.info("MCPChatClient cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global client instance
mcp_client = MCPChatClient()

@app.on_event("startup")
async def startup_event():
    """Initialize MCP client on startup"""
    logger.info("Starting up FileBrowser MCP API with Ollama")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up MCP client on shutdown"""
    logger.info("Shutting down FileBrowser MCP API")
    await mcp_client.cleanup()

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Process a chat query using the MCP-enabled Ollama LLM
    """
    try:
        logger.info(f"Received chat request: {request.query[:100]}...")
        response = await mcp_client.process_query(request.query)
        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if Ollama is available
        models = await mcp_client.ollama_client.list()
        ollama_status = "available"
    except:
        ollama_status = "unavailable"

    return {
        "status": "healthy",
        "service": "FileBrowser MCP API",
        "llm_provider": "Ollama",
        "model": mcp_client.model,
        "ollama_status": ollama_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)