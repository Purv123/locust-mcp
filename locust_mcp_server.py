from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import asyncio
import tempfile
import os
import logging
import subprocess
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

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

def parse_prompt(prompt: str) -> Dict[str, Any]:
    """Parse natural language prompt to extract test configuration."""
    config = {
        "targetUrl": "http://localhost:8000",
        "users": 10,
        "spawnRate": 1,
        "runTime": "30s",
        "endpoints": []
    }
    
    # Extract URL
    url_match = re.search(r"Test\s+(https?://[^\s]+)", prompt)
    if url_match:
        config["targetUrl"] = url_match.group(1)
    
    # Extract number of users
    users_match = re.search(r"(\d+)\s+users?", prompt)
    if users_match:
        config["users"] = int(users_match.group(1))
    
    # Extract think time
    think_time_match = re.search(r"(\d+)\s+second[s]?\s+think time", prompt)
    if think_time_match:
        think_time = int(think_time_match.group(1))
        config["thinkTime"] = think_time
    
    # Extract endpoints
    if "GET" in prompt:
        path_match = re.search(r"GET\s+(/\w+)", prompt)
        if path_match:
            config["endpoints"].append({
                "method": "GET",
                "path": path_match.group(1)
            })
    
    return config

def generate_locust_script(params: Dict[str, Any]) -> str:
    """Generate a Locust test script based on the provided parameters."""
    target_url = params.get("targetUrl", "http://localhost:8000")
    endpoints = params.get("endpoints", [])
    think_time = params.get("thinkTime", 1)
    
    script_lines = [
        "from locust import HttpUser, task, between",
        "",
        f"class PerformanceTest(HttpUser):",
        f"    host = \"{target_url}\"",
        f"    wait_time = between({think_time}, {think_time + 1})",
        ""
    ]

    for idx, endpoint in enumerate(endpoints, 1):
        method = endpoint.get("method", "GET").lower()
        path = endpoint.get("path", "/")
        data = endpoint.get("data")
        headers = endpoint.get("headers", {})
        weight = endpoint.get("weight", 1)
        
        task_lines = [
            f"    @task({weight})",
            f"    def test_{method}_{idx}(self):",
        ]

        request_params = []
        if headers:
            request_params.append(f"headers={json.dumps(headers)}")
        if data and method in ["post", "put", "patch"]:
            request_params.append(f"json={json.dumps(data)}")
        
        params_str = ", ".join(request_params)
        task_lines.append(f"        self.client.{method}(\"{path}\"{', ' + params_str if params_str else ''})")
        task_lines.append("")
        
        script_lines.extend(task_lines)

    return "\n".join(script_lines)

class WebSocketConnectionManager:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.is_connected = False

    async def connect(self):
        try:
            await self.websocket.accept()
            self.is_connected = True
            logger.info("New WebSocket connection established")
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {str(e)}")
            raise

    async def disconnect(self):
        if self.is_connected:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error during WebSocket closure: {str(e)}")
            finally:
                self.is_connected = False
                logger.info("WebSocket connection closed")

    async def send_response(self, response: MCPResponse):
        if self.is_connected:
            try:
                await self.websocket.send_text(response.json())
            except Exception as e:
                logger.error(f"Error sending response: {str(e)}")
                await self.disconnect()

@app.websocket("/mcp")
async def websocket_endpoint(websocket: WebSocket):
    connection = WebSocketConnectionManager(websocket)
    
    try:
        await connection.connect()
        
        data = await websocket.receive_text()
        request = MCPRequest.parse_raw(data)
        logger.info(f"Received command: {request.command}")
        
        if request.command == "generate":
            try:
                # Parse the prompt if provided
                if "prompt" in request.params:
                    config = parse_prompt(request.params["prompt"])
                else:
                    config = request.params
                
                # Generate Locust test script
                script = generate_locust_script(config)
                
                # Generate command string
                cmd = (f"locust -f test_script.py --host {config['targetUrl']} --users {config['users']} "
                      f"--spawn-rate {config['spawnRate']} --run-time {config['runTime']} "
                      f"--headless --only-summary --json")
                
                response = MCPResponse(result={
                    "script": script,
                    "config": config,
                    "command": cmd,
                    "success": True
                })
                await connection.send_response(response)
                
            except Exception as e:
                logger.error(f"Error generating script: {str(e)}")
                await connection.send_response(MCPResponse(error=str(e)))
        else:
            error_msg = f"Unknown command: {request.command}"
            logger.error(error_msg)
            await connection.send_response(MCPResponse(error=error_msg))
            
    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if connection.is_connected:
            await connection.send_response(MCPResponse(error=str(e)))
    finally:
        await connection.disconnect()
