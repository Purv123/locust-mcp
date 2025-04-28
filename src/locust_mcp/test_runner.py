import asyncio
import tempfile
import os
from typing import Dict, Any
import json
import subprocess

class LocustTestRunner:
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run Locust tests with the given parameters."""
        script = params.get("script", "")
        config = params.get("config", {})
        
        if not script:
            return {"error": "No test script provided"}

        # Create a temporary file for the test script
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
            # Clean up temporary file
            if os.path.exists(script_path):
                os.unlink(script_path)

    async def stop(self) -> Dict[str, Any]:
        """Stop any running Locust tests."""
        try:
            # Find and kill any running Locust processes
            cmd = "pkill -f locust"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            return {
                "success": True,
                "message": "All Locust processes stopped"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
