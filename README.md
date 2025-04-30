# Locust MCP (Model Context Protocol) Test Generator

A natural language-driven load testing tool that generates and runs Locust test scripts based on simple English prompts or curl commands.

## Features

- Generate Locust test scripts using:
  - Natural language prompts
  - Curl commands (NEW!)
- Automatically detect API endpoints, user count, and think time from prompts
- Save generated tests with timestamps for historical tracking
- Configurable test parameters (users, spawn rate, run time)
- WebSocket-based communication between client and server
- Support for headers, cookies, and complex HTTP requests

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- virtualenv (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd locust-mcp-purvit
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Server

1. Start the MCP server:
```bash
python start_server.py
```

The server will start on `localhost:8000`.

### Generating and Running Tests

Use the test client to generate Locust test scripts using natural language prompts:

```bash
python test_client.py "Test https://api.example.com with 5 users: GET /users endpoint with 2 second think time between requests"
```

The test client will:
1. Generate a Locust test script based on your prompt
2. Save the test script in a timestamped directory under `tests/generated/`
3. Output the command to run the test

### Example Prompts

1. Basic GET endpoint test:
```bash
python test_client.py "Test https://jsonplaceholder.typicode.com API with 5 users: GET /posts endpoint"
```

2. Test with think time:
```bash
python test_client.py "Test https://api.example.com with 10 users: GET /users endpoint with 3 second think time between requests"
```

3. Using curl commands:
```bash
python test_client.py "curl 'https://api.example.com/v2/data' \
  -H 'accept: application/json' \
  -H 'authorization: Bearer token123' \
  -H 'content-type: application/json'"
```

The generator will automatically:
- Parse the curl command
- Extract headers, cookies, and other parameters
- Generate an equivalent Locust test
- Handle complex requests with proper authentication and headers

### Curl Command Support

The tool now supports generating tests directly from curl commands. It handles:
- Headers (-H flags)
- Cookies (-b flag)
- Request methods (-X flag)
- Request data (-d flag)
- Complex URLs with query parameters
- Authentication headers
- Content-Type specifications

When using curl commands:
1. Copy the curl command from your browser's network tools or API documentation
2. Pass it directly to the test client
3. The generator will create a Locust test maintaining all headers and parameters

### Test Output Structure

Generated tests are saved in the following structure:
```
tests/generated/
└── YYYYMMDD_HHMMSS/
    ├── locust_test_YYYYMMDD_HHMMSS.py  # Generated test script
    └── config.json                      # Test configuration
```

### Running Generated Tests

After generating a test, you can run it using the provided Locust command:
```bash
locust -f tests/generated/YYYYMMDD_HHMMSS/locust_test_YYYYMMDD_HHMMSS.py --host https://api.example.com --users 5 --spawn-rate 1 --run-time 30s --headless
```

## Project Structure

```
├── locust_mcp_server.py    # Main server implementation
├── test_client.py          # Test generation client
├── requirements.txt        # Project dependencies
├── src/
│   └── locust_mcp/        # Core MCP implementation
└── tests/
    └── generated/         # Generated test scripts
```

## Configuration

The server and test generation behavior can be configured through various parameters:

- Default number of users: 10
- Default spawn rate: 1 user/second
- Default run time: 30 seconds
- Default think time: 1 second

These defaults can be overridden through the natural language prompt or command-line arguments.

## Development

To contribute to the project:

1. Create a new virtual environment
2. Install development dependencies:
```bash
pip install -r requirements.txt
```

3. Make your changes
4. Run tests (if available)
5. Submit a pull request


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
