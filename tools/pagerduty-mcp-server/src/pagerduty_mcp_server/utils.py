"""Pagerduty helper utilities"""

from typing import List, Dict, Any, Optional, Union
import logging
from datetime import datetime, timedelta, timezone
import re

logger = logging.getLogger(__name__)

RESPONSE_LIMIT = 500

class ValidationError(Exception):
    """Raised when data validation fails."""
    pass

"""
Utils public methods
"""

def api_response_handler(*,
                        results: Union[Dict[str, Any], List[Dict[str, Any]]],
                        resource_name: str,
                        limit: Optional[int] = RESPONSE_LIMIT,
                        additional_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process API response and return a standardized format.

    Example response:
    {
        "metadata": {
            "count": 2,
            "description": "Found 2 results for resource type <resource_name>",
            # Additional metadata fields can be included here
        },
        "<resource_name>": [
            ...
        ]
    }

    Args:
        results (Union[Dict[str, Any], List[Dict[str, Any]]]): The API response results
        resource_name (str): The name of the resource (e.g., 'services', 'incidents').
            Use plural form for list operations, singular for single-item operations.
        limit (int): The maximum number of results allowed (optional, default is {pagerduty_mcp_server.utils.RESPONSE_LIMIT})
        additional_metadata (Dict[str, Any]): Optional additional metadata to include in the response

    Returns:
        Dict[str, Any]: A dictionary containing:
            - {resource_name} (List[Dict[str, Any]]): The processed results as a list
            - metadata (Dict[str, Any]): Metadata about the response including:
                - count (int): Total number of results
                - description (str): Description of the results
                - Additional fields from additional_metadata if provided
            - error (Optional[Dict[str, Any]]): Error information if the query exceeds the limit, containing:
                - code (str): Error code (e.g., "LIMIT_EXCEEDED")
                - message (str): Human-readable error message

    Raises:
        ValidationError: If the results format is invalid or resource_name is empty
    """
    if not resource_name or not resource_name.strip():
        raise ValidationError("resource_name cannot be empty")

    if isinstance(results, dict):
        results = [results]

    if len(results) > limit:
        return {
            "metadata": {
                "count": len(results),
                "description": f"Query returned {len(results)} {resource_name}, which exceeds the limit of {limit}"
            },
            "error": {
                "code": "LIMIT_EXCEEDED",
                "message": f"Query returned {len(results)} {resource_name}, which exceeds the limit of {limit}"
            }
        }

    metadata = {
        "count": len(results),
        "description": f"Found {len(results)} {'result' if len(results) == 1 else 'results'} for resource type {resource_name}"
    }

    if additional_metadata:
        metadata.update(additional_metadata)

    return {
        "metadata": metadata,
        f"{resource_name}": results
    }

def validate_iso8601_timestamp(timestamp: str, param_name: str) -> None:
    """Validate that a string is a valid ISO8601 timestamp.

    Args:
        timestamp (str): The timestamp string to validate
        param_name (str): The name of the parameter being validated (for error messages)

    Note:
        Accepts both UTC timestamps (ending in 'Z') and timestamps with timezone offsets.
        UTC timestamps are automatically converted to the equivalent offset format.

    Raises:
        ValidationError: If the timestamp is not a valid ISO8601 format
    """
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError as e:
        raise ValidationError(f"Invalid ISO8601 timestamp for {param_name}: {timestamp}. Error: {str(e)}")

def handle_api_error(e: Exception) -> None:
    """Log the error and re-raise the original exception.

    Args:
        e (Exception): The exception that was raised

    Raises:
        Exception: The original exception without modification
    """
    # Get the full error message from the response if available
    if hasattr(e, 'response') and e.response is not None:
        error_message = e.response.text
    else:
        error_message = str(e)

    logger.error(error_message)
    raise e

def try_convert_relative_time_to_pdt_iso(time_param_value: Optional[str]) -> Optional[str]:
    """
    Tries to convert a relative time string (e.g., "2 hours ago", "30 minutes ago")
    to an ISO8601 timestamp string in PDT (fixed UTC-7 offset).
    If the input is not a recognized relative time string, or is None, it's returned unchanged.
    """
    if not time_param_value:
        return time_param_value

    match = re.fullmatch(r"(\d+)\s+(hour|minute)s?\s+ago", time_param_value, re.IGNORECASE)
    if match:
        value = int(match.group(1))
        unit = match.group(2).lower()
        
        if unit == "hour":
            delta = timedelta(hours=value)
        elif unit == "minute":
            delta = timedelta(minutes=value)
        else:
            # Should not happen with the regex, but as a safeguard
            return time_param_value 

        now_utc = datetime.now(timezone.utc)
        target_utc = now_utc - delta
        
        # Convert to PDT (fixed UTC-7 offset)
        pdt_timezone = timezone(timedelta(hours=-7))
        target_pdt = target_utc.astimezone(pdt_timezone)
        
        return target_pdt.isoformat()
        
    return time_param_value # Return original if no match or not a string
