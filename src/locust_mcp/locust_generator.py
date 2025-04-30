from typing import Dict, Any, List
import json
import re
import shlex
from urllib.parse import urlparse, parse_qs

class LocustScriptGenerator:
    """Generator class for creating Locust test scripts."""
    
    def _parse_curl_command(self, curl_command: str, users: int = 10, run_time: str = "30s") -> Dict[str, Any]:
        """Parse a curl command into a dictionary of parameters."""
        # Find URL in the curl command
        url_match = re.search(r'curl\s+["\']?(https?://[^\s\'\"]+)["\']?', curl_command)
        if not url_match:
            raise ValueError("No valid URL found in curl command")
            
        url = url_match.group(1)
        parsed_url = urlparse(url)
        
        config = {
            "method": "GET",
            "headers": {},
            "cookies": {},
            "data": None,
            "users": users,
            "run_time": run_time,
            "host": f"{parsed_url.scheme}://{parsed_url.netloc}",
            "path": parsed_url.path,
            "query_params": {k: v[0] for k, v in parse_qs(parsed_url.query).items() if v}
        }
        
        # Parse headers
        header_matches = re.finditer(r'-H\s+["\']([^:]+):\s*([^"\']+)["\']', curl_command)
        for match in header_matches:
            key, value = match.groups()
            key = key.strip()
            value = value.strip()
            if not any(skip in key.lower() for skip in ['sec-', 'accept-encoding', 'connection', 'keep-alive']):
                config["headers"][key] = value
                
        return config

    def generate_from_curl(self, curl_command: str, users: int = 10, run_time: str = "30s") -> str:
        """Generate a Locust test script from a curl command."""
        config = self._parse_curl_command(curl_command, users, run_time)
        
        # Format script with proper indentation
        script_lines = [
            "from locust import HttpUser, task, between",
            "",
            "class PerformanceTest(HttpUser):",
            f"    host = \"{config['host']}\"  # Base URL without path",
            "    wait_time = between(1, 5)",
            "",
            "    def on_start(self):",
            "        # Set default headers that will be used for all requests",
            f"        self.headers = {json.dumps(config['headers'], indent=12)}",
            "",
            "    @task(1)",
            "    def test_get_1(self):",
            f"        path = \"{config['path']}\""
        ]
        
        # Add query parameters if present
        if config["query_params"]:
            script_lines.append(f"        params = {json.dumps(config['query_params'])}")
        
        # Add the request with proper parameters
        method = config["method"].lower()
        request_params = ["headers=self.headers"]
        
        if config["query_params"]:
            request_params.append("params=params")
        if config["data"] and method in ["post", "put", "patch"]:
            request_params.append(f"json={json.dumps(config['data'])}")
        
        params_str = ", ".join(request_params)
        script_lines.append(f"        self.client.{method}(path, {params_str})")
        
        return "\n".join(script_lines)

    def generate(self, params: Dict[str, Any]) -> str:
        """Generate a Locust test script based on the provided parameters."""
        # Check if this is a curl command
        if isinstance(params.get("prompt"), str) and params["prompt"].strip().startswith("curl"):
            users = params.get("users", 10)
            run_time = params.get("runTime", "30s")
            return self.generate_from_curl(params["prompt"], users, run_time)
            
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
