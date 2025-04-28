#!/usr/bin/env python3
import os
import sys
import uvicorn

def main():
    # Add the src directory to Python path
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, src_dir)
    
    # Import and run the server
    from locust_mcp.server import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")

if __name__ == "__main__":
    main()
