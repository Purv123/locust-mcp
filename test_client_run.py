import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_load_test():
    """Run a load test using the MCP server"""
    uri = "ws://localhost:8124/mcp"
    logger.info(f"Connecting to MCP server at {uri}")

    async with websockets.connect(uri) as websocket:
        # Generate test configuration
        test_config = {
            "command": "generate",
            "params": {
                "prompt": "Test the API at https://jsonplaceholder.typicode.com/posts with 50 users for 2 minutes"
            }
        }

        logger.info("Sending test generation request...")
        await websocket.send(json.dumps(test_config))
        response = await websocket.recv()
        result = json.loads(response)

        if "error" in result and result["error"]:
            logger.error(f"Error generating test: {result['error']}")
            return

        test_id = result["result"]["test_id"]
        logger.info(f"Generated test with ID: {test_id}")
        logger.info(f"Test script:\n{result['result']['script']}")

        # Run the test
        run_config = {
            "command": "run",
            "params": {
                "test_id": test_id
            }
        }

        logger.info("Starting load test...")
        await websocket.send(json.dumps(run_config))
        response = await websocket.recv()
        result = json.loads(response)

        if "error" in result and result["error"]:
            logger.error(f"Error running test: {result['error']}")
            return

        # Print test results
        stats = result.get("result", {}).get("statistics", [])
        if stats and len(stats) > 0:
            latest_stats = stats[-1]
            print("\nTest Results:")
            print(f"Total Requests: {latest_stats.get('num_requests', 0)}")
            print(f"Failed Requests: {latest_stats.get('num_failures', 0)}")
            print(f"Average Response Time: {latest_stats.get('avg_response_time', 0):.2f} ms")
            print(f"Requests/sec: {latest_stats.get('current_rps', 0):.2f}")
            print(f"Failure Rate: {latest_stats.get('failure_rate', 0):.2f}%")

if __name__ == "__main__":
    asyncio.run(run_load_test())
