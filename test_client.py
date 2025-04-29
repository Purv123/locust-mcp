import asyncio
import websockets
import json
import logging
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    async with websockets.connect('ws://localhost:8000/mcp') as websocket:
        # Generate test from natural language prompt
        test_config = {
            "command": "generate",
            "params": {
                "prompt": prompt
            }
        }

        print(f"\nGenerating test from prompt: {prompt}")
        await websocket.send(json.dumps(test_config))
        response = await websocket.recv()
        generate_result = json.loads(response)
        
        if "error" in generate_result and generate_result["error"]:
            print(f"Error: {generate_result['error']}")
            return

        if "result" in generate_result:
            script = generate_result["result"]["script"]
            print(f"\nGenerated Locust test script:")
            print("=" * 40)
            print(script)
            print("=" * 40)
            
            # Save test script
            with open(test_file_path, 'w') as f:
                f.write(script)
            
            # Save config
            with open(config_file_path, 'w') as f:
                json.dump(generate_result["result"]["config"], f, indent=4)
            
            print("\nTo run this test, use the following command:")
            print(f"locust -f {test_file_path} --host {generate_result['result']['config']['targetUrl']} --users {generate_result['result']['config']['users']} --spawn-rate {generate_result['result']['config']['spawnRate']} --run-time {generate_result['result']['config']['runTime']} --headless")

if __name__ == "__main__":
    # Get prompt from command line arguments if provided
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    asyncio.run(test_mcp_server(prompt))
