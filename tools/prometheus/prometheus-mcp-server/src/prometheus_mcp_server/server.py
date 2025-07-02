#!/usr/bin/env python

import os
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import time
from datetime import datetime, timedelta

import dotenv
import requests
from mcp.server.fastmcp import FastMCP

dotenv.load_dotenv()
mcp = FastMCP("prometheus-prod")

@dataclass
class PrometheusConfig:
    url: str
    # Optional Org ID for multi-tenant setups
    org_id: Optional[str] = None

config = PrometheusConfig(
    url=os.environ.get("PROMETHEUS_PROD_URL", ""),
    org_id=os.environ.get("ORG_ID", ""),
)

def get_prometheus_auth():
    """Authentication is not used."""
    return None

def make_prometheus_request(endpoint, params=None):
    """Make a request to the Prometheus API."""
    if not config.url:
        raise ValueError("Prometheus configuration is missing. Please set PROMETHEUS_URL environment variable.")

    url = f"{config.url.rstrip('/')}/api/v1/{endpoint}"
    headers = {}
    
    # Add OrgID header if specified
    if config.org_id:
        headers["X-Scope-OrgID"] = config.org_id

    # Make the request with appropriate headers
    response = requests.get(url, params=params, headers=headers)
    
    response.raise_for_status()
    result = response.json()
    
    if result["status"] != "success":
        raise ValueError(f"Prometheus API error: {result.get('error', 'Unknown error')}")
    
    return result["data"]

@mcp.tool(description="Execute a PromQL instant query against Prometheus")
async def execute_query(query: str, time: Optional[str] = None) -> Dict[str, Any]:
    """Execute an instant query against Prometheus.
    
    Args:
        query: PromQL query string
        time: Optional RFC3339 or Unix timestamp (default: current time)
        
    Returns:
        Query result with type (vector, matrix, scalar, string) and values
    """
    params = {"query": query}
    if time:
        params["time"] = time
    
    data = make_prometheus_request("query", params=params)
    return {
        "resultType": data["resultType"],
        "result": data["result"]
    }

@mcp.tool(description="Execute a PromQL range query with start time, end time, and step interval")
async def execute_range_query(query: str, start: str, end: str, step: str) -> Dict[str, Any]:
    """Execute a range query against Prometheus.
    
    Args:
        query: PromQL query string
        start: Start time as RFC3339 or Unix timestamp
        end: End time as RFC3339 or Unix timestamp
        step: Query resolution step width (e.g., '15s', '1m', '1h')
        
    Returns:
        Range query result with type (usually matrix) and values over time
    """
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step
    }
    
    data = make_prometheus_request("query_range", params=params)
    return {
        "resultType": data["resultType"],
        "result": data["result"]
    }

@mcp.tool(description="List all available metrics in Prometheus")
async def list_metrics() -> List[str]:
    """Retrieve a list of all metric names available in Prometheus.
    
    Returns:
        List of metric names as strings
    """
    data = make_prometheus_request("label/__name__/values")
    return data

@mcp.tool(description="Get metadata for a specific metric")
async def get_metric_metadata(metric: str) -> List[Dict[str, Any]]:
    """Get metadata about a specific metric.
    
    Args:
        metric: The name of the metric to retrieve metadata for
        
    Returns:
        List of metadata entries for the metric
    """
    params = {"metric": metric}
    data = make_prometheus_request("metadata", params=params)
    return data["metadata"]

@mcp.tool(description="Get information about all scrape targets")
async def get_targets() -> Dict[str, List[Dict[str, Any]]]:
    """Get information about all Prometheus scrape targets.
    
    Returns:
        Dictionary with active and dropped targets information
    """
    data = make_prometheus_request("targets")
    return {
        "activeTargets": data["activeTargets"],
        "droppedTargets": data["droppedTargets"]
    }

if __name__ == "__main__":
    print(f"Starting Prometheus MCP Server...")
    mcp.run()
