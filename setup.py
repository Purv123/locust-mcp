from setuptools import setup

setup(
    name="locust-mcp",
    version="0.1.0",
    description="MCP server for generating and running Locust load tests",
    packages=["locust_mcp"],
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "locust>=2.15.1",
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "websockets>=11.0.3",
        "pydantic>=2.0.0"
    ],
    entry_points={
        "console_scripts": [
            "locust-mcp=locust_mcp.server:main",
        ],
    },
)
