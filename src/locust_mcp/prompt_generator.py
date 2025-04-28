from typing import Dict, Any, List
import json
from pydantic import BaseModel

class LoadTestSpec(BaseModel):
    """Specification for a load test"""
    targetUrl: str
    endpoints: List[Dict[str, Any]]
    users: int = 10
    spawnRate: int = 1
    runTime: str = "30s"

class PromptGenerator:
    """Converts natural language prompts into load test specifications"""
    
    def parse_prompt(self, prompt: str) -> LoadTestSpec:
        """
        Parse a natural language prompt into a load test specification.
        Handles common load testing scenarios and extracts test parameters.
        """
        prompt = prompt.lower()
        
        # Extract URL
        import re
        url_match = re.search(r'https?://[^\s]+', prompt)
        target_url = url_match.group(0) if url_match else "http://localhost:8000"
        
        # Extract number of users
        users_match = re.search(r'(\d+)\s*users?', prompt)
        users = int(users_match.group(1)) if users_match else 10
        
        # Extract run time
        time_match = re.search(r'(\d+)\s*(s|seconds?|m|minutes?|h|hours?)', prompt)
        if time_match:
            value, unit = time_match.groups()
            if unit.startswith('m'):
                run_time = f"{value}m"
            elif unit.startswith('h'):
                run_time = f"{value}h"
            else:
                run_time = f"{value}s"
        else:
            run_time = "30s"
        
        # Extract spawn rate
        spawn_match = re.search(r'spawn\s*(?:rate|speed)?\s*(?:of)?\s*(\d+)', prompt)
        spawn_rate = int(spawn_match.group(1)) if spawn_match else 1
        
        # Determine endpoints and methods
        endpoints = []
        
        # Check for common HTTP methods
        for method in ['get', 'post', 'put', 'delete', 'patch']:
            if method in prompt:
                path = "/"
                weight = 1
                
                # Try to extract path
                path_match = re.search(f'{method}\\s+(?:from|to)?\\s*([/\\w]+)', prompt)
                if path_match:
                    path = path_match.group(1)
                    if not path.startswith('/'):
                        path = f"/{path}"
                
                # Check for request body for POST/PUT/PATCH
                data = None
                if method in ['post', 'put', 'patch'] and 'json' in prompt:
                    data = {"title": "Test Data", "body": "This is test data"}
                
                # Extract weight/priority
                weight_match = re.search(f'{method}.*?(\\d+)\\s*times?\\s*more', prompt)
                if weight_match:
                    weight = int(weight_match.group(1))
                
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "data": data,
                    "weight": weight
                })
        
        # If no specific endpoints were found, add a default GET endpoint
        if not endpoints:
            endpoints = [{"method": "GET", "path": "/", "weight": 1}]
            
        return LoadTestSpec(
            targetUrl=target_url,
            endpoints=endpoints,
            users=users,
            spawnRate=spawn_rate,
            runTime=run_time
        )
        
        raise ValueError("Could not parse prompt. Please provide a valid test specification or a clear test description.")
