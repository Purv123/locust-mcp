import sys
import uvicorn
from .server import create_app

def main():
    """Entry point for the MCP server"""
    uvicorn.run(
        "locust_mcp.server:create_app",
        host="127.0.0.1",
        port=8000,
        factory=True,
        log_level="info"
    )

if __name__ == "__main__":
    sys.exit(main())
