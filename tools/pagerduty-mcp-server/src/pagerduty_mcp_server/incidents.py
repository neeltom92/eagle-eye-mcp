"""PagerDuty incident operations."""

from typing import List, Dict, Any, Optional
import logging

from . import client
from . import utils
from .parsers import parse_incident

logger = logging.getLogger(__name__)

INCIDENTS_URL = '/incidents'

VALID_STATUSES = ['triggered', 'acknowledged', 'resolved']
DEFAULT_STATUSES = ['triggered', 'acknowledged', 'resolved']
VALID_URGENCIES = ['high', 'low']
DEFAULT_URGENCIES = ['high', 'low']

AUTORESOLVE_TYPE = 'service_reference'

"""
Incidents API Helpers
"""

def list_incidents(*,
                  service_ids: Optional[List[str]] = None,
                  team_ids: Optional[List[str]] = None,
                  statuses: Optional[List[str]] = None,
                  urgencies: Optional[List[str]] = None,
                  since: Optional[str] = None,
                  until: Optional[str] = None,
                  limit: Optional[int] = None) -> Dict[str, Any]:
    """List PagerDuty incidents based on specified filters.

    Args:
        service_ids (List[str]): List of PagerDuty service IDs to filter by (optional)
        team_ids (List[str]): List of PagerDuty team IDs to filter by (optional)
        statuses (List[str]): List of status values to filter by (optional). Valid values are:
            - 'triggered' - The incident is currently active (included by default)
            - 'acknowledged' - The incident has been acknowledged by a user (included by default)
            - 'resolved' - The incident has been resolved (included by default)
            Defaults to ['triggered', 'acknowledged', 'resolved'] if not specified.
        urgencies (List[str]): List of urgency values to filter by (optional). Valid values are:
            - 'high' - High urgency incidents (included by default)
            - 'low' - Low urgency incidents (included by default)
            Defaults to ['high', 'low'] if not specified.
        since (str): Start of date range in ISO8601 format (optional). Default is 1 month ago
        until (str): End of date range in ISO8601 format (optional). Default is now
        limit (int): Limit the number of results returned (optional)

    Returns:
        Dict[str, Any]: A dictionary containing:
            - incidents (List[Dict[str, Any]]): List of incident objects matching the specified criteria
            - metadata (Dict[str, Any]): Metadata about the response including:
                - count: Total number of incidents
                - description: Human-readable description of the response
                - status_counts: Dictionary mapping each status to its count
                - autoresolve_count: Number of incidents that were auto-resolved (status='resolved' and last_status_change_by.type='service_reference')
                - no_data_count: Number of incidents with titles starting with "No Data:"
            - error (Optional[Dict[str, Any]]): Error information if the API request fails

    Raises:
        ValueError: If invalid status or urgency values are provided
        ValidationError: If since or until parameters are not valid ISO8601 timestamps
        RuntimeError: If the API request fails or response processing fails
    """

    pd_client = client.get_api_client()

    if statuses is None:
        statuses = DEFAULT_STATUSES
    else:
        invalid_statuses = [s for s in statuses if s not in VALID_STATUSES]
        if invalid_statuses:
            raise ValueError(f"Invalid status values: {invalid_statuses}. Valid values are: {VALID_STATUSES}")

    if urgencies is None:
        urgencies = DEFAULT_URGENCIES
    else:
        invalid_urgencies = [u for u in urgencies if u not in VALID_URGENCIES]
        if invalid_urgencies:
            raise ValueError(f"Invalid urgency values: {invalid_urgencies}. Valid values are: {VALID_URGENCIES}")

    if statuses is not None and not isinstance(statuses, (list, str)):
        raise ValueError("statuses must be a list or string")

    # Convert relative times for since and until
    processed_since = utils.try_convert_relative_time_to_pdt_iso(since)
    processed_until = utils.try_convert_relative_time_to_pdt_iso(until)

    params = {}
    if service_ids:
        params['service_ids'] = service_ids
    if team_ids:
        params['team_ids'] = team_ids
    if statuses:
        params['statuses[]'] = statuses
    if processed_since: # Use processed value
        params['since'] = processed_since
        utils.validate_iso8601_timestamp(processed_since, 'since')
    if processed_until: # Use processed value
        params['until'] = processed_until
        utils.validate_iso8601_timestamp(processed_until, 'until')
    if limit:
        params['limit'] = limit

    try:
        response = pd_client.list_all(INCIDENTS_URL, params=params)
        metadata = _calculate_incident_metadata(response)
        parsed_response = [parse_incident(result=result) for result in response]

        return utils.api_response_handler(
            results=parsed_response,
            resource_name='incidents',
            additional_metadata=metadata
        )
    except Exception as e:
        utils.handle_api_error(e)

def show_incident(*,
                 incident_id: str) -> Dict[str, Any]:
    """Get detailed information about a given incident.

    Args:
        incident_id (str): The ID or number of the incident to get

    Returns:
        Dict[str, Any]: A dictionary containing:
            - incident (Dict[str, Any]): Incident object with detailed information
            - metadata (Dict[str, Any]): Metadata about the response including:
                - count (int): Always 1 for single resource responses
                - description (str): Description of the result
            - error (Optional[Dict[str, Any]]): Error information if the API request fails

    Raises:
        ValueError: If incident_id is None or empty
        RuntimeError: If the API request fails or response processing fails
        KeyError: If the API response is missing required fields
    """

    if not incident_id:
        raise ValueError("incident_id cannot be empty")

    pd_client = client.get_api_client()

    try:
        response = pd_client.jget(f"{INCIDENTS_URL}/{incident_id}")
        try:
            incident_data = response['incident']
        except KeyError:
            raise RuntimeError(f"Failed to fetch or process incident {incident_id}: 'incident'")
            
        return utils.api_response_handler(
            results=parse_incident(result=incident_data),
            resource_name='incident'
        )
    except Exception as e:
        utils.handle_api_error(e)

def list_past_incidents(*,
                 incident_id: str,
                 limit: Optional[int] = None,
                 total: Optional[bool] = None) -> Dict[str, Any]:
    """List incidents from the past 6 months that are similar to the input incident, and were generated on the same service as the parent incident. Results are ordered by similarity score.

    The returned incidents are in a slimmed down format containing only id, created_at, self, and title.
    Each incident also includes a similarity_score (a decimal value) indicating how similar it is to the input incident.
    Incidents are sorted by similarity_score in descending order, so the most similar incidents appear first.

    Args:
        incident_id (str): The ID or number of the incident to find similar incidents for
        limit (int): The maximum number of past incidents to return (optional). This parameter is passed
            directly to the PagerDuty API. Default in the API is 5.
        total (bool): Whether to return the total number of incidents that match the criteria (optional).
            This parameter is passed directly to the PagerDuty API. Default is False.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - incidents (List[Dict[str, Any]]): List of similar incident objects, each containing:
                - id (str): The incident ID
                - created_at (str): Creation timestamp
                - self (str): API URL for the incident
                - title (str): The incident title
                - similarity_score (Decimal): Decimal value indicating similarity to the input incident
            - metadata (Dict[str, Any]): Metadata about the response including count and description

    Raises:
        ValueError: If incident_id is None or empty
        RuntimeError: If the API request fails or response processing fails
        KeyError: If the API response is missing required fields
    """

    if not incident_id:
        raise ValueError("incident_id cannot be empty")

    pd_client = client.get_api_client()

    params = {'limit': limit, 'total': total}
    try:
        response = pd_client.jget(f"{INCIDENTS_URL}/{incident_id}/past_incidents", params=params)
        try:
            past_incidents = response['past_incidents']
        except KeyError:
            raise RuntimeError(f"Failed to fetch past incidents for {incident_id}: Response missing 'past_incidents' field")
            
        parsed_response = [
            {
                **parse_incident(result=item.get('incident', {})),
                'similarity_score': item.get('score', 0.0)
            }
            for item in past_incidents
        ]
        parsed_response.sort(key=lambda x: x['similarity_score'], reverse=True)

        return utils.api_response_handler(
            results=parsed_response,
            resource_name='incidents'
        )
    except Exception as e:
        utils.handle_api_error(e)

def list_related_incidents(*,
                         incident_id: str) -> Dict[str, Any]:
    """List the 20 most recent related incidents that are impacting other services and responders.
    The limit of 20 incidents is enforced by the PagerDuty API.

    Args:
        incident_id (str): The ID or number of the incident to get related incidents for

    Returns:
        Dict[str, Any]: A dictionary containing:
            - incidents (List[Dict[str, Any]]): List of related incident objects, each containing:
                - id (str): The incident ID
                - created_at (str): Creation timestamp
                - self (str): API URL for the incident
                - title (str): The incident title
                - relationship_type (str): The type of relationship (e.g. 'machine_learning_inferred')
                - relationship_metadata (Dict[str, Any]): Additional metadata about the relationship including:
                    - grouping_classification (str): Classification of the grouping
                    - user_feedback (Dict[str, int]): Feedback counts for the relationship
            - metadata (Dict[str, Any]): Metadata about the response including:
                - count (int): Total number of related incidents (up to 20)
                - description (str): Description of the results
            - error (Optional[Dict[str, Any]]): Error information if the API request fails

    Raises:
        ValueError: If incident_id is None or empty
        RuntimeError: If the API request fails or response processing fails
        KeyError: If the API response is missing required fields
    """

    if not incident_id:
        raise ValueError("incident_id cannot be empty")

    pd_client = client.get_api_client()

    try:
        response = pd_client.jget(f"{INCIDENTS_URL}/{incident_id}/related_incidents")
        try:
            related_incidents = response['related_incidents']
        except KeyError:
            raise RuntimeError(f"Failed to fetch related incidents for {incident_id}: Response missing 'related_incidents' field")
            
        parsed_response = [
            {
                **parse_incident(result=item['incident']),
                'relationship_type': item['relationships'][0]['type'] if item['relationships'] else None,
                'relationship_metadata': item['relationships'][0]['metadata'] if item['relationships'] else None
            }
            for item in related_incidents
        ]

        return utils.api_response_handler(
            results=parsed_response,
            resource_name='incidents'
        )
    except Exception as e:
        utils.handle_api_error(e)


"""
Incidents Private Helpers
"""

def _count_incident_statuses(incidents: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count incidents by status.

    Args:
        incidents (List[Dict[str, Any]]): List of incident objects

    Returns:
        Dict[str, int]: Dictionary mapping status to count
    """
    status_counts = {}
    for incident in incidents:
        status = incident.get('status')
        if status in VALID_STATUSES:
            status_counts[status] = status_counts.get(status, 0) + 1
    return status_counts

def _count_autoresolved_incidents(incidents: List[Dict[str, Any]]) -> int:
    """Count incidents that were auto-resolved.

    Args:
        incidents (List[Dict[str, Any]]): List of incident objects

    Returns:
        int: Number of auto-resolved incidents
    """
    return sum(
        1 for incident in incidents
        if (incident.get('status') == 'resolved' and
            incident.get('last_status_change_by', {}).get('type', '') == AUTORESOLVE_TYPE)
    )

def _count_no_data_incidents(incidents: List[Dict[str, Any]]) -> int:
    """Count incidents that are "no data" incidents.

    Args:
        incidents (List[Dict[str, Any]]): List of incident objects

    Returns:
        int: Number of incidents with titles starting with "No Data:"
    """
    return sum(
        1 for incident in incidents
        if incident.get('title', '').startswith('No Data:')
    )

def _calculate_incident_metadata(incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate additional metadata for incidents including status counts and autoresolve count.

    Args:
        incidents (List[Dict[str, Any]]): List of incident objects

    Returns:
        Dict[str, Any]: Dictionary containing:
            - status_counts (Dict[str, int]): Dictionary mapping each status to its count
            - autoresolve_count (int): Number of incidents that were auto-resolved
                (status='resolved' and last_status_change_by.type='service_reference')
            - no_data_count (int): Number of incidents generated by "No Data" events
    """
    if not incidents:
        return {
            'status_counts': {status: 0 for status in VALID_STATUSES},
            'autoresolve_count': 0,
            'no_data_count': 0
        }

    status_counts = _count_incident_statuses(incidents)
    autoresolve_count = _count_autoresolved_incidents(incidents)
    no_data_count = _count_no_data_incidents(incidents)

    return {
        'status_counts': {
            status: status_counts.get(status, 0)
            for status in VALID_STATUSES
        },
        'autoresolve_count': autoresolve_count,
        'no_data_count': no_data_count
    }
