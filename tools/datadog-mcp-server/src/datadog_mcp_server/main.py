import sys
import dotenv
import os
from datadog_mcp_server.server import mcp # Ensure mcp is imported

# DEFAULT_PORT = 6777 # Commented out as mcp.run() might handle port differently

def setup_environment():
    if dotenv.load_dotenv():
        print("Loaded environment variables from .env file")
    else:
        print("No .env file found or could not load it - using environment variables")

    # Add any Datadog specific environment checks here if needed
    # For example, check if DD_API_KEY and DD_APP_KEY are set
    if not os.environ.get("DD_API_KEY") or not os.environ.get("DD_APP_KEY"):
        print("ERROR: DD_API_KEY or DD_APP_KEY environment variables are not set.")
        print("Please set them in your .env file or environment.")
        return False
    
    print(f"Datadog MCP Server configured.")
    return True

def run_server():
    if not setup_environment():
        sys.exit(1)
    
    # port = int(os.environ.get("DATADOG_MCP_PORT", DEFAULT_PORT))
    # host = os.environ.get("DATADOG_MCP_HOST", "127.0.0.1")

    # print(f"Starting Datadog MCP Server on {host}:{port}")
    print("Starting Datadog MCP Server...")
    mcp.run() # Changed to use mcp.run()

if __name__ == "__main__":
    # This allows running the setup for quick checks if needed,
    # but the actual server is run via MCP CLI or a ASGI server like uvicorn.
    run_server() 