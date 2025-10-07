import json
import logging
import os
from typing import Dict, List
from urllib.parse import urljoin

import requests

from private_api_utils.private_api_utils import serializer, vlr_result_list_to_dict
from scraper.entities import VLRResult
from logging_config import PRIVATE_API_LOGGER as LOGGER
from private_api_utils.private_api_utils import PRIVATE_API_BASE_URL


def bulk_insert(endpoint: str, payload: Dict[str, any]) -> requests.Response:
    """
    A helper method that takes a payload in the format expected by the private api endpoint and attempts to bulk insert using the relevant bulk insert endpoint.
    """

    ATTEMPTS = 10
    for attempt in range(ATTEMPTS):
        try:
            response = requests.post(
                url=urljoin(PRIVATE_API_BASE_URL, endpoint),
                data=json.dumps(payload, default=serializer),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            return response
        except Exception as e:
            if attempt == ATTEMPTS - 1:
                LOGGER.error("Failed to bulk insert at PRIVATE_API endpoint after %s attempts", ATTEMPTS)
                return None

def bulk_insert_series(series_dict: Dict[str, any]) -> requests.Response:
    payload = {
        "series": vlr_result_list_to_dict(series_dict)
    }
    return bulk_insert("series/bulk", payload)

def bulk_insert_teams(teams_dict: Dict[str, any]) -> requests.Response:
    payload = {
        "teams": vlr_result_list_to_dict(teams_dict)
    }
    return bulk_insert("team/bulk", payload)

def bulk_insert_events(events_dict: Dict[str, any]) -> requests.Response:
    payload = {
        "events": vlr_result_list_to_dict(events_dict)
    }
    return bulk_insert("event/bulk", payload)

def bulk_insert_matches(matches_dict: Dict[str, any]) -> requests.Response:
    payload = {
        "matches": vlr_result_list_to_dict(matches_dict)
    }
    return bulk_insert("match/bulk", payload)

def bulk_insert_results(result_dict: Dict[str, any]) -> List[tuple[str, Dict[str, any]]]:
    """
    A helper method that bulk inserts each component of the `results_dict`, which is typically returned from the getting the result set of the `ScrapeScheduler` 
    """

    result_names = ("series", "team", "event", "match")
    result_name_set = set(result_names)
    if not result_name_set.issubset(result_dict.keys()):
        LOGGER.error("Invalid result dictionary received. Cannot bulk insert results.")
        return None

    res_series = bulk_insert_series(result_dict["series"])
    res_team = bulk_insert_teams(result_dict["team"])
    res_event = bulk_insert_events(result_dict["event"])
    res_match = bulk_insert_matches(result_dict["match"])

    failed_payloads: List[tuple[str, Dict[str, any]]] = []
    for i, result in enumerate([res_series, res_team, res_event, res_match]):
        if not result:
            LOGGER.error("Got no response for %s", result_names[i])
            failed_payloads.extend((result_names[i], result_dict))
        elif not result.ok:
            LOGGER.error("Got bad status code %s for %s", result.status_code, result.text)
            # TODO: Store all these results to later reattempt.
            failed_payloads.extend((result_names[i], result_dict))
    
    return failed_payloads