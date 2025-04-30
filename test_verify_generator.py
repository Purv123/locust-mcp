from src.locust_mcp.locust_generator import LocustScriptGenerator

# Test curl command
curl_command = "curl https://mon.signalfx.com/v2/dashboard/_/hierarchy/DoW3fDtAkDc?group=DjdWq-WAkfI"
curl_command += ' -H "accept: application/json, text/plain, */*"'
curl_command += ' -H "x-sf-token: hLSs0pMv10B2pz6CfGsPjg"'
curl_command += ' -H "accept-language: en-US,en;q=0.9"'
curl_command += ' -H "origin: https://app.mon0.signalfx.com"'
curl_command += ' -H "referer: https://app.mon0.signalfx.com/"'

# Create generator instance
generator = LocustScriptGenerator()

# Parse the command first to debug
config = generator._parse_curl_command(curl_command)
print("\nParsed configuration:")
print("=" * 40)
print(f"Host: {config['host']}")
print(f"Path: {config['path']}")
print(f"Query params: {config['query_params']}")
print(f"Headers: {config['headers']}")
print("=" * 40)

# Generate test with minimal load (1 user, 1 second)
script = generator.generate_from_curl(curl_command, users=1, run_time="1s")

print("\nGenerated test script:")
print("=" * 40)
print(script)
print("=" * 40)
