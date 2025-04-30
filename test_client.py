import asyncio
import websockets
import json
import logging
import sys
import os
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from src.locust_mcp.locust_generator import LocustScriptGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_test_params(prompt: str) -> dict:
    """Extract test parameters from the prompt"""
    params = {
        "users": 1,
        "runTime": "1s"
    }
    
    # Extract user count
    users_match = re.search(r'with\s+(\d+)\s+users?', prompt)
    if users_match:
        params["users"] = int(users_match.group(1))

    # Extract run time
    time_match = re.search(r'for\s+(\d+)\s*(s|seconds?|m|minutes?|h|hours?)', prompt)
    if time_match:
        value, unit = time_match.groups()
        if unit.startswith('m'):
            params["runTime"] = f"{value}m"
        elif unit.startswith('h'):
            params["runTime"] = f"{value}h"
        else:
            params["runTime"] = f"{value}s"
    
    return params

def extract_curl_command(prompt: str) -> str:
    """Extract curl command from a prompt that might contain test parameters"""
    # Find the curl command part
    curl_match = re.search(r'curl\s+.*$', prompt, re.MULTILINE)
    if curl_match:
        return curl_match.group(0)
    return prompt

async def test_mcp_server(prompt: str = None):
    """Demo client showing natural language test generation"""
    logger.info("Connecting to MCP server...")
    
    if not prompt:
        # Default test if no prompt provided
        prompt = "Test https://jsonplaceholder.typicode.com API with 5 users: GET /posts endpoint"

    # Create timestamp for the test directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_dir = os.path.join("tests", "generated", timestamp)
    os.makedirs(test_dir, exist_ok=True)
    
    # Define test file paths
    test_file_name = f"locust_test_{timestamp}.py"
    test_file_path = os.path.join(test_dir, test_file_name)
    config_file_path = os.path.join(test_dir, "config.json")

    # Extract test parameters and curl command
    test_params = extract_test_params(prompt)
    is_curl = "curl" in prompt
    
    # Create generator instance
    generator = LocustScriptGenerator()
    
    if is_curl:
        # Generate directly using the curl command
        curl_command = extract_curl_command(prompt)
        script = generator.generate_from_curl(
            curl_command,
            users=test_params["users"],
            run_time=test_params["runTime"]
        )
        # Parse the command to get config
        config = generator._parse_curl_command(
            curl_command,
            users=test_params["users"],
            run_time=test_params["runTime"]
        )
    else:
        # Use WebSocket server for natural language prompts
        async with websockets.connect('ws://localhost:8000/mcp') as websocket:
            test_config = {
                "command": "generate",
                "params": {
                    "prompt": prompt,
                    "users": test_params["users"],
                    "runTime": test_params["runTime"]
                }
            }

            await websocket.send(json.dumps(test_config))
            response = await websocket.recv()
            generate_result = json.loads(response)
            
            if "error" in generate_result and generate_result["error"]:
                print(f"Error: {generate_result['error']}")
                return

            if "result" in generate_result:
                script = generate_result["result"]["script"]
                config = generate_result["result"]["config"]
    
    print(f"\nGenerating test from {'curl command' if is_curl else 'prompt'}: {prompt}")
    print(f"\nGenerated Locust test script:")
    print("=" * 80)
    print(script)
    print("=" * 80)
    
    # Save test script
    with open(test_file_path, 'w') as f:
        f.write(script)
    
    # Save config
    with open(config_file_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print("\nTest files saved:")
    print(f"Test script: {test_file_path}")
    print(f"Config file: {config_file_path}")
    print("\nTo run this test, use the following command:")
    if is_curl:
        print(f"locust -f {test_file_path}")
    else:
        print(f"locust -f {test_file_path} --host {config['targetUrl']} --users {test_params['users']} --spawn-rate 1 --run-time {test_params['runTime']}")

if __name__ == "__main__":
    # Get prompt from command line arguments if provided
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    asyncio.run(test_mcp_server(prompt))
