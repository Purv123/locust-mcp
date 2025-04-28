#!/usr/bin/env python3
import os
import sys
import uvicorn

def main():
    # Import and run the server
    # Start the server with more verbose logging
    print("Starting Locust MCP Server...")
    uvicorn.run(
        "locust_mcp.server:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=True,  # Enable auto-reload for development
        reload_dirs=["src"]  # Watch the src directory for changes
    )

if __name__ == "__main__":
    main()
