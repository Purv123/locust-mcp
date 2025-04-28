from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import logging
import os
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

app = FastAPI()

# Initialize core components
prompt_generator = PromptGenerator()
test_store = TestStore()
script_generator = LocustScriptGenerator()
test_runner = LocustTestRunner()

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
    await websocket.accept()
    logger.info("New WebSocket connection established")

    while True:
        try:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"Received message: {message}")

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
            
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            try:
                await websocket.send_text(MCPResponse(error=str(e)).json())
            except:
                logger.error("Failed to send error response")

def create_app():
    """Create and configure the FastAPI application for MCP"""
    return app

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Locust MCP Server")
    uvicorn.run(app, host="127.0.0.1", port=8000)
