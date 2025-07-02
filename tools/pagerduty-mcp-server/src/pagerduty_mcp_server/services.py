"""PagerDuty service operations."""

from typing import List, Dict, Any, Optional
import logging

from . import client
from .parsers import parse_service
from . import utils

logger = logging.getLogger(__name__)

SERVICES_URL = '/services'

"""
Services API Helpers
"""

def list_services(*,
                 team_ids: Optional[List[str]] = None,
                 query: Optional[str] = None,
                 limit: Optional[int] = None) -> Dict[str, Any]:
    """List existing PagerDuty services.

    Args:
        team_ids (List[str]): Filter results to only services assigned to teams with the given IDs (optional)
        query (str): Filter services whose names contain the search query (optional)
        limit (int): Limit the number of results returned (optional)

    Returns:
        Dict[str, Any]: A dictionary containing:
            - services (List[Dict[str, Any]]): List of service objects matching the specified criteria
            - metadata (Dict[str, Any]): Metadata about the response including:
                - count (int): Total number of results
                - description (str): Description of the results
            - error (Optional[Dict[str, Any]]): Error information if the API request fails

    Raises:
        ValueError: If team_ids is an empty list
        RuntimeError: If the API request fails or response processing fails
        KeyError: If the API response is missing required fields
    """

    pd_client = client.get_api_client()

    if team_ids is not None and not team_ids:
        raise ValueError("team_ids cannot be an empty list")

    params = {}
    if team_ids:
        params['team_ids[]'] = team_ids  # PagerDuty API expects array parameters with [] suffix
    if query:
        params['query'] = query
    if limit:
        params['limit'] = limit

    try:
        response = pd_client.list_all(SERVICES_URL, params=params)
        
        # Ensure we have an iterable, even if response is None
        actual_response_iterable = response if response is not None else []
        
        parsed_response = []
        for item in actual_response_iterable: # Explicit loop
            parsed_item = parse_service(result=item)
            # Optionally, only add valid items if parse_service can return None for individual services
            # For now, let's assume parse_service always returns a dict or raises an error for bad items
            parsed_response.append(parsed_item)
            
        return utils.api_response_handler(results=parsed_response, resource_name='services')
    except Exception as e:
        # Direct logging and structured error return
        error_message = f"Exception directly caught in list_services: {type(e).__name__} - {str(e)}"
        logger.error(error_message) # Assumes logger is available and configured

        # Return a dictionary that mimics a valid response structure but indicates an error
        return {
            "metadata": {
                "count": 0,
                "description": "An error occurred within list_services while fetching services.",
                "original_error_type": type(e).__name__,
                "original_error_message": str(e)
            },
            "services": [], # Ensure services key exists and is an empty list
            "error": { 
                "code": "LIST_SERVICES_EXCEPTION",
                "message": error_message
            }
        }

def show_service(*,
                service_id: str) -> Dict[str, Any]:
    """Get detailed information about a given service.

    Args:
        service_id (str): The ID of the service to get

    Returns:
        Dict[str, Any]: A dictionary containing:
            - service (Dict[str, Any]): Service object with detailed information
            - metadata (Dict[str, Any]): Metadata about the response including:
                - count (int): Always 1 for single resource responses
                - description (str): Description of the result
            - error (Optional[Dict[str, Any]]): Error information if the API request fails

    Raises:
        ValueError: If service_id is None or empty
        RuntimeError: If the API request fails or response processing fails
        KeyError: If the API response is missing required fields
    """

    if not service_id:
        raise ValueError("service_id cannot be empty")

    pd_client = client.get_api_client()

    try:
        response = pd_client.jget(f"{SERVICES_URL}/{service_id}")
        try:
            service_data = response['service']  # Raw PagerDuty API data for the service
        except KeyError:
            raise RuntimeError(f"Failed to fetch service {service_id}: Response missing 'service' field")
            
        parsed_service_dict = parse_service(result=service_data)

        # Augment the parsed_service_dict with escalation policy details
        # Ensure parsed_service_dict is a dictionary before modifying it
        if isinstance(parsed_service_dict, dict):
            escalation_policy_data = service_data.get('escalation_policy') # Get raw escalation policy data
            if isinstance(escalation_policy_data, dict):
                parsed_service_dict['escalation_policy_id'] = escalation_policy_data.get('id')
                parsed_service_dict['escalation_policy_summary'] = escalation_policy_data.get('summary')
            else:
                # Ensure keys exist with None values if escalation_policy data is not found or not a dict
                parsed_service_dict['escalation_policy_id'] = None
                parsed_service_dict['escalation_policy_summary'] = None
        # Consider logging a warning if parsed_service_dict is not a dict as expected for a single service.
        
        return utils.api_response_handler(
            results=parsed_service_dict, # Pass the augmented dictionary
            resource_name='service'
        )
    except Exception as e:
        utils.handle_api_error(e)


"""
Services Helpers
"""

def fetch_service_ids(*,
                      team_ids: List[str]) -> List[str]:
    """Get the service IDs for a list of team IDs.

    Args:
        team_ids (List[str]): A list of team IDs

    Returns:
        List[str]: A list of service IDs. Returns an empty list if no services are found.

    Note:
        This is an internal helper function used by other modules to fetch service IDs.
        The PagerDuty API expects array parameters with [] suffix (e.g., 'team_ids[]').

    Raises:
        ValueError: If team_ids is empty or None
        RuntimeError: If the API request fails or response processing fails
        KeyError: If the API response is missing required fields
    """
    if not team_ids:
        raise ValueError("Team IDs must be specified")

    pd_client = client.get_api_client()
    params = {'team_ids[]': team_ids}  # PagerDuty API expects array parameters with [] suffix
    try:
        services_response = pd_client.list_all(SERVICES_URL, params=params)
        parsed_response = [parse_service(result=result) for result in services_response]
        return [service['id'] for service in parsed_response]
    except Exception as e:
        utils.handle_api_error(e)
