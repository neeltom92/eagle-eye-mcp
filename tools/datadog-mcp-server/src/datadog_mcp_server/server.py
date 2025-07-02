import os
import json
from typing import Any, Dict, List, Optional

import dotenv
from datadog import api, initialize
from mcp.server.fastmcp import FastMCP

dotenv.load_dotenv()

datadog_instructions = """
Datadog MCP Server Instructions:

This server provides tools to interact with the Datadog API.
- Ensure your DD_API_KEY and DD_APP_KEY are correctly configured in the environment.
- Tools will generally return JSON responses or a dictionary containing an 'error' key if something went wrong.
- When searching (e.g., for dashboards), be as specific as reasonably possible with your query to narrow down results.

Available tools:
- get_monitor_details: Fetches details for a specific Datadog monitor by its ID.
- list_dashboards: Searches for Datadog dashboards by a query string in their titles.

(You can add more specific instructions here as you add more tools, detailing common use cases, or limitations.)
"""

mcp = FastMCP("datadog", instructions=datadog_instructions)

# Initialize Datadog client
# Ensure DD_API_KEY and DD_APP_KEY are in your .env file or environment
options = {
    "api_key": os.environ.get("DD_API_KEY"),
    "app_key": os.environ.get("DD_APP_KEY")
}
initialize(**options)

@mcp.tool(description="Example Datadog tool: Get monitor details by ID")
async def get_monitor_details(monitor_id: int) -> Dict[str, Any]:
    """Fetch details for a specific Datadog monitor.

    Args:
        monitor_id: The ID of the monitor to fetch.

    Returns:
        A dictionary containing the monitor details.
    """
    try:
        monitor = api.Monitor.get(monitor_id)
        return monitor
    except Exception as e:
        return {"error": str(e)}

@mcp.tool(description="Get Datadog monitor details by name. Searches for a monitor with the exact name provided.")
async def get_monitor_details_by_name(monitor_name: str) -> Dict[str, Any]:
    """Fetch details for a specific Datadog monitor by its exact name.

    Args:
        monitor_name: The exact name of the monitor to fetch.

    Returns:
        A dictionary containing the monitor details if a unique match is found.
        Returns an error if no monitor is found, or if multiple monitors match the name.
    """
    try:
        # Search for monitors with the given name.
        # The Datadog API for monitor search can be a bit broad,
        # so we will filter for an exact match on the name post-search.
        search_results = api.Monitor.search(query=f'name:"{monitor_name}"')

        if not search_results or not search_results.get('monitors'):
            return {"error": f"No monitor found with name '{monitor_name}'"}

        exact_matches = [
            m for m in search_results['monitors'] if m.get('name') == monitor_name
        ]

        if not exact_matches:
            return {"error": f"No monitor found with exact name '{monitor_name}'."}
        
        if len(exact_matches) > 1:
            return {
                "error": f"Multiple monitors found with the name '{monitor_name}'. Please use the monitor ID instead.",
                "matches": [{"id": m.get("id"), "name": m.get("name")} for m in exact_matches]
            }

        # If a unique exact match is found, get its full details.
        monitor_id = exact_matches[0].get('id')
        if monitor_id is None:
            return {"error": f"Found monitor '{monitor_name}' but it does not have an ID."}
        
        monitor_details = await get_monitor_details(monitor_id) # Call existing function
        return monitor_details

    except Exception as e:
        return {"error": f"Failed to get monitor by name '{monitor_name}': {str(e)}"}

@mcp.tool(description="Search for Datadog dashboards by title.")
async def list_dashboards(query: str) -> List[Dict[str, str]]:
    """Search for Datadog dashboards by title containing the query string.

    Args:
        query: The string to search for in dashboard titles.

    Returns:
        A list of dashboards matching the query, with their title, id, and url.
        Returns an error dictionary if the API call fails.
    """
    try:
        all_dashboards_response = api.Dashboard.get_all()
        if 'dashboards' not in all_dashboards_response:
            return {"error": "Unexpected response from Datadog API: 'dashboards' key missing."}

        matched_dashboards = []
        search_query_lower = query.lower()
        for dash in all_dashboards_response['dashboards']:
            title = dash.get('title', '')
            if search_query_lower in title.lower():
                matched_dashboards.append({
                    "id": dash.get('id_str', dash.get('id')), # id_str is preferred if available
                    "title": title,
                    "url": dash.get('url') # This is usually the relative URL
                })
        return matched_dashboards
    except Exception as e:
        return {"error": f"Failed to list Datadog dashboards: {str(e)}"}

# Add more Datadog tools here, for example:
# - list_monitors
# - get_dashboard
# - query_metrics
# - list_events

# You can model these tools based on the Datadog API documentation:
# https://docs.datadoghq.com/api/latest/ 