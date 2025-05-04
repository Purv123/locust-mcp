import asyncio
import websockets
import json
import logging
import sys
import os
import re
import csv
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from src.locust_mcp.locust_generator import LocustScriptGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_test_cases(csv_path: str) -> list:
    """Read test cases from CSV file"""
    test_cases = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append({
                'sr_no': row['Sr. No'],
                'curl_command': row['Curl Command'],
                'users': int(row['No. Of Users']),
                'duration': row['Duration']
            })
    return test_cases

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

async def generate_test(test_case: dict, generator: LocustScriptGenerator, timestamp: str) -> tuple:
    """Generate a single test from a test case"""
    # Create test directory
    test_dir = os.path.join("tests", "generated", f"{timestamp}_case{test_case['sr_no']}")
    os.makedirs(test_dir, exist_ok=True)
    
    # Define test file paths
    test_file_name = f"locust_test_{timestamp}_case{test_case['sr_no']}.py"
    test_file_path = os.path.join(test_dir, test_file_name)
    config_file_path = os.path.join(test_dir, "config.json")

    # Generate test script
    script = generator.generate_from_curl(
        test_case['curl_command'],
        users=test_case['users'],
        run_time=test_case['duration']
    )
    
    # Get config
    config = generator._parse_curl_command(
        test_case['curl_command'],
        users=test_case['users'],
        run_time=test_case['duration']
    )
    
    # Save test script
    with open(test_file_path, 'w') as f:
        f.write(script)
    
    # Save config
    with open(config_file_path, 'w') as f:
        json.dump(config, f, indent=4)
        
    return test_file_path, config_file_path, script, config

async def batch_generate_tests(csv_path: str):
    """Generate tests from a CSV file of test cases"""
    logger.info(f"Reading test cases from {csv_path}")
    
    # Read test cases
    test_cases = read_test_cases(csv_path)
    if not test_cases:
        logger.error("No test cases found in CSV file")
        return
    
    # Create generator instance
    generator = LocustScriptGenerator()
    
    # Generate timestamp for this batch
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Process each test case
    for test_case in test_cases:
        logger.info(f"Generating test for case {test_case['sr_no']}")
        
        try:
            test_file_path, config_file_path, script, config = await generate_test(
                test_case, generator, timestamp
            )
            
            print(f"\nGenerated test for case {test_case['sr_no']}:")
            print("=" * 80)
            print(script)
            print("=" * 80)
            
            print(f"\nTest files saved:")
            print(f"Test script: {test_file_path}")
            print(f"Config file: {config_file_path}")
            print("\nTo run this test, use the following command:")
            print(f"locust -f {test_file_path} --users {test_case['users']} --spawn-rate 1 --run-time {test_case['duration']} --headless")
            
        except Exception as e:
            logger.error(f"Error generating test for case {test_case['sr_no']}: {str(e)}")
            continue
    
    logger.info(f"Completed processing {len(test_cases)} test cases")

if __name__ == "__main__":
    # Check if CSV file path is provided
    if len(sys.argv) != 2:
        print("Usage: python test_client.py <path_to_csv_file>")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
        
    asyncio.run(batch_generate_tests(csv_path))
