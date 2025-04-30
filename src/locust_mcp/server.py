from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import logging
import os
import asyncio
from datetime import datetime, timedelta
from locust_mcp.prompt_generator import PromptGenerator
from locust_mcp.test_store import TestStore
from locust_mcp.locust_generator import LocustScriptGenerator
from locust_mcp.test_runner import LocustTestRunner

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for connection management
HEARTBEAT_INTERVAL = 30  # seconds
CONNECTION_TIMEOUT = 60  # seconds
MAX_REQUESTS_PER_MINUTE = 60

app = FastAPI()

# Initialize core components
prompt_generator = PromptGenerator()
test_store = TestStore()
script_generator = LocustScriptGenerator()
test_runner = LocustTestRunner()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict] = {}
        self.request_counts: Dict[WebSocket, List[datetime]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = {
            "last_heartbeat": datetime.now(),
            "connected_at": datetime.now()
        }
        self.request_counts[websocket] = []
        logger.info("New WebSocket connection established")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)
        self.request_counts.pop(websocket, None)
        logger.info("WebSocket connection closed")

    async def check_rate_limit(self, websocket: WebSocket) -> bool:
        """Check if the client has exceeded rate limits"""
        now = datetime.now()
        requests = self.request_counts.get(websocket, [])
        
        # Remove requests older than 1 minute
        requests = [t for t in requests if now - t < timedelta(minutes=1)]
        self.request_counts[websocket] = requests
        
        # Add current request
        requests.append(now)
        
        # Check if limit exceeded
        return len(requests) <= MAX_REQUESTS_PER_MINUTE

    async def heartbeat(self):
        """Send periodic heartbeats and cleanup dead connections"""
        while True:
            now = datetime.now()
            dead_connections = []
            
            for ws, conn_info in self.active_connections.items():
                try:
                    if now - conn_info["last_heartbeat"] > timedelta(seconds=CONNECTION_TIMEOUT):
                        dead_connections.append(ws)
                        continue
                        
                    if now - conn_info["last_heartbeat"] >= timedelta(seconds=HEARTBEAT_INTERVAL):
                        await ws.send_json({"type": "heartbeat"})
                        conn_info["last_heartbeat"] = now
                        
                except Exception:
                    dead_connections.append(ws)
                    
            # Cleanup dead connections
            for ws in dead_connections:
                try:
                    await ws.close()
                except Exception:
                    pass
                self.disconnect(ws)
                
            await asyncio.sleep(HEARTBEAT_INTERVAL)

# Create connection manager instance
manager = ConnectionManager()

# Start heartbeat task when app starts
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(manager.heartbeat())

class MCPRequest(BaseModel):
    command: str
    params: Dict[str, Any]

class MCPResponse(BaseModel):
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class Endpoint(BaseModel):
    method: str
    path: str
    data: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, Any]] = None
    weight: Optional[int] = 1

@app.websocket("/mcp")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            try:
                # Check rate limit
                if not await manager.check_rate_limit(websocket):
                    await websocket.send_json({
                        "error": f"Rate limit exceeded. Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute allowed."
                    })
                    continue

                # Receive message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=CONNECTION_TIMEOUT
                )
                
                message = json.loads(data)
                logger.info(f"Received message: {message}")

                # Update last heartbeat time
                manager.active_connections[websocket]["last_heartbeat"] = datetime.now()

                # Handle MCP initialization
                if message.get("command") == "initialize":
                    logger.info("Handling initialization request")
                    response = {
                        "type": "response",
                        "requestId": message.get("requestId"),
                        "success": True,
                        "result": {
                            "capabilities": {
                                "textDocument": True,
                                "workspace": True
                            }
                        }
                    }
                    await websocket.send_json(response)
                    continue

                # Handle regular MCP commands
                request = MCPRequest.parse_raw(data)
                logger.info(f"Processing command: {request.command}")
                
                # Process command
                if request.command == "generate":
                    try:
                        if "prompt" in request.params:
                            test_spec = prompt_generator.parse_prompt(request.params["prompt"])
                            script = script_generator.generate(test_spec.dict())
                            config = test_spec.dict()
                        else:
                            script = script_generator.generate(request.params)
                            config = {
                                "host": request.params.get("targetUrl", "http://localhost:8000"),
                                "users": request.params.get("users", 10),
                                "spawn_rate": request.params.get("spawnRate", 1),
                                "run_time": request.params.get("runTime", "30s")
                            }
                        
                        description = request.params.get("prompt", "Generated test")
                        test_info = test_store.save_test(script, config, description)
                        
                        response = MCPResponse(result={
                            "test_id": test_info["id"],
                            "script": script,
                            "config": config,
                            "script_path": test_info["script_path"],
                            "config_path": test_info["config_path"]
                        })
                    except Exception as e:
                        logger.error(f"Error generating script: {str(e)}")
                        response = MCPResponse(error=str(e))
                
                elif request.command == "run":
                    try:
                        if "test_id" in request.params:
                            test_data = test_store.get_test(request.params["test_id"])
                            if test_data is None:
                                raise ValueError(f"Test with ID {request.params['test_id']} not found")
                            script = test_data["script"]
                            config = test_data["config"]
                        else:
                            script = request.params.get("script", "")
                            config = request.params.get("config", {})
                        
                        results = await test_runner.run({
                            "script": script,
                            "config": config
                        })
                        response = MCPResponse(result=results)
                    except Exception as e:
                        logger.error(f"Error running test: {str(e)}")
                        response = MCPResponse(error=str(e))
                
                elif request.command == "list":
                    try:
                        tests = test_store.list_tests()
                        response = MCPResponse(result={"tests": tests})
                    except Exception as e:
                        logger.error(f"Error listing tests: {str(e)}")
                        response = MCPResponse(error=str(e))
                
                elif request.command == "stop":
                    try:
                        result = await test_runner.stop()
                        response = MCPResponse(result=result)
                    except Exception as e:
                        logger.error(f"Error stopping tests: {str(e)}")
                        response = MCPResponse(error=str(e))
                
                else:
                    error_msg = f"Unknown command: {request.command}"
                    logger.error(error_msg)
                    response = MCPResponse(error=error_msg)
                
                # Send response
                await websocket.send_text(response.json())
                
            except asyncio.TimeoutError:
                logger.warning("Connection timed out")
                break
                
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                try:
                    await websocket.send_text(MCPResponse(error=str(e)).json())
                except:
                    logger.error("Failed to send error response")
                    break

    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
    finally:
        manager.disconnect(websocket)

def create_app():
    """Create and configure the FastAPI application for MCP"""
    return app

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Locust MCP Server")
    uvicorn.run(app, host="127.0.0.1", port=8000)
