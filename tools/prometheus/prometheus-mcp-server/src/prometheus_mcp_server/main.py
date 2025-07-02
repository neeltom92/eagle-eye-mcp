#!/usr/bin/env python
import sys
import dotenv
from prometheus_mcp_server.server import mcp, config

def setup_environment():
    if dotenv.load_dotenv():
        print("Loaded environment variables from .env file")
    else:
        print("No .env file found or could not load it - using environment variables")

    if not config.url:
        print("ERROR: PROMETHEUS_PROD_URL environment variable is not set")
        print("Please set it to your Prometheus server URL")
        print("Example: http://your-prometheus-server:9090")
        return False
    
    print(f"Prometheus configuration:")
    print(f"  Server URL: {config.url}")
    
    print("Authentication: None (credentials are not used)")
    
    return True

def run_server():
    """Main entry point for the Prometheus MCP Server"""
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    print("\nStarting Prometheus MCP Server...")
    print("Running server in standard mode...")
    
    # Run the server with the stdio transport
    mcp.run(transport="stdio")

if __name__ == "__main__":
    run_server()
