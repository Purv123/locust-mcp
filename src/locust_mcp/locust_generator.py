from typing import Dict, Any, List
import json

class LocustScriptGenerator:
    """Generator class for creating Locust test scripts."""
    
    def generate(self, params: Dict[str, Any]) -> str:
        """Generate a Locust test script based on the provided parameters."""
        target_url = params.get("targetUrl", "http://localhost:8000")
        endpoints = params.get("endpoints", [])
        users = params.get("users", 10)
        spawn_rate = params.get("spawnRate", 1)
        
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

    def generate_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Locust configuration based on the provided parameters."""
        return {
            "host": params.get("targetUrl", "http://localhost:8000"),
            "users": params.get("users", 10),
            "spawn_rate": params.get("spawnRate", 1),
            "run_time": params.get("runTime", "30s")
        }
