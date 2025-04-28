import asyncio
import websockets
import json
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_server(prompt: str = None):
    """Demo client showing natural language test generation"""
    logger.info("Connecting to MCP server...")
    
    if not prompt:
        # Default test if no prompt provided
        prompt = "Test https://jsonplaceholder.typicode.com API with 5 users: GET /posts 3 times more often than POST /posts with json data"

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

        test_id = generate_result["result"]["test_id"]
        print(f"\nGenerated test (ID: {test_id}):")
        print(generate_result["result"]["script"])

        # Run the generated test
        run_config = {
            "command": "run",
            "params": {
                "test_id": test_id
            }
        }

        print("\nRunning the generated test...")
        await websocket.send(json.dumps(run_config))
        response = await websocket.recv()
        run_result = json.loads(response)

        if "error" in run_result and run_result["error"]:
            print(f"Error: {run_result['error']}")
        else:
            stats = run_result.get("result", {}).get("statistics", [])
            if stats and len(stats) > 0:
                latest_stats = stats[-1]
                print("\nTest Results:")
                print(f"Total Requests: {latest_stats.get('num_requests', 0)}")
                print(f"Failed Requests: {latest_stats.get('num_failures', 0)}")
                print(f"Average Response Time: {latest_stats.get('avg_response_time', 0):.2f} ms")
                print(f"Requests/sec: {latest_stats.get('current_rps', 0):.2f}")
                print(f"Failure Rate: {latest_stats.get('failure_rate', 0):.2f}%")

if __name__ == "__main__":
    # Get prompt from command line arguments if provided
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    asyncio.run(test_mcp_server(prompt))
