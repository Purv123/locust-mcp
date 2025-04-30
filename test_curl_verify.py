import json
from src.locust_mcp.locust_generator import LocustScriptGenerator

# Test curl command with properly formatted URL
curl_command = """curl https://mon.signalfx.com/v2/dashboard/_/hierarchy/DoW3fDtAkDc?group=DjdWq-WAkfI \
  -H 'accept: application/json, text/plain, */*' \
  -H 'x-sf-token: hLSs0pMv10B2pz6CfGsPjg'"""

# Create generator instance
generator = LocustScriptGenerator()

# Generate test with minimal load (1 user, 1 second)
script = generator.generate_from_curl(curl_command, users=1, run_time="1s")

print("Generated script:")
print("=" * 40)
print(script)
print("=" * 40)

# Save the script to verify
with open('verify_test.py', 'w') as f:
    f.write(script)
