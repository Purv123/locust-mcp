from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import asyncio
import tempfile
import os
import logging
import subprocess

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

def generate_locust_script(params: Dict[str, Any]) -> str:
    """Generate a Locust test script based on the provided parameters."""
    target_url = params.get("targetUrl", "http://localhost:8000")
    endpoints = params.get("endpoints", [])
    
    script_lines = [
        "from locust import HttpUser, task, between",
        "",
        f"class PerformanceTest(HttpUser):",
        f"    host = \"{target_url}\"",
        "    wait_time = between(1, 5)",
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

async def run_locust_test(script: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Run Locust tests with the given script and configuration."""
    try:
        # Create temporary file for the test script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            # Construct Locust command
            cmd = [
                "locust",
                "-f", script_path,
                "--host", config.get("host", "http://localhost:8000"),
                "--users", str(config.get("users", 10)),
                "--spawn-rate", str(config.get("spawn_rate", 1)),
                "--run-time", str(config.get("run_time", "30s")),
                "--headless",
                "--json"
            ]

            # Run Locust process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            
            try:
                # Parse JSON output from Locust
                results = json.loads(stdout.decode())
                return {
                    "success": True,
                    "statistics": results,
                    "error": None
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "statistics": None,
                    "error": "Failed to parse Locust output",
                    "output": stdout.decode()
                }

        except Exception as e:
            return {
                "success": False,
                "statistics": None,
                "error": str(e)
            }
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path)

    except Exception as e:
        return {
            "success": False,
            "statistics": None,
            "error": str(e)
        }

@app.websocket("/mcp")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("New WebSocket connection established")
    
    while True:
        try:
            # Receive message
            data = await websocket.receive_text()
            request = MCPRequest.parse_raw(data)
            logger.info(f"Received command: {request.command}")
            
            # Process command
            if request.command == "generate":
                try:
                    # Generate Locust test script
                    script = generate_locust_script(request.params)
                    response = MCPResponse(result={
                        "script": script,
                        "config": {
                            "host": request.params.get("targetUrl", "http://localhost:8000"),
                            "users": request.params.get("users", 10),
                            "spawn_rate": request.params.get("spawnRate", 1),
                            "run_time": request.params.get("runTime", "30s")
                        }
                    })
                except Exception as e:
                    logger.error(f"Error generating script: {str(e)}")
                    response = MCPResponse(error=str(e))
                    
            elif request.command == "run":
                try:
                    # Run Locust test
                    results = await run_locust_test(
                        request.params.get("script", ""),
                        request.params.get("config", {})
                    )
                    response = MCPResponse(result=results)
                except Exception as e:
                    logger.error(f"Error running test: {str(e)}")
                    response = MCPResponse(error=str(e))
                    
            elif request.command == "stop":
                try:
                    # Stop running tests
                    cmd = "pkill -f locust"
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    response = MCPResponse(result={"success": True, "message": "All Locust processes stopped"})
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
            await websocket.send_text(MCPResponse(error=str(e)).json())

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Locust MCP Server")
    uvicorn.run(app, host="127.0.0.1", port=8000)
