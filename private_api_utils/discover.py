
from typing import Dict, List, Set
from urllib.parse import urljoin
from logging_config import PRIVATE_API_LOGGER as LOGGER

import requests

from private_api_utils.private_api_utils import PRIVATE_API_BASE_URL

def get_known_series() -> List[int] | None:
    ATTEMPTS = 10
    url = urljoin(PRIVATE_API_BASE_URL, "series/get-known")
    for attempt in range(ATTEMPTS):
        try:
            response = requests.get(url, timeout=5)
            break
        except Exception as e:
            if attempt == ATTEMPTS - 1:
                LOGGER.error("Failed to fetch url %s. %s", url, e, exc_info=True)
                return None
    
    if not response.ok:
        LOGGER.error("Private API returned bad response %s when attempting to get known series at %s", response.status_code, url)
        return None
    
    return response.json()["id"]

def get_unknown_series() -> List[int] | None:
    ATTEMPTS = 10
    url = urljoin(PRIVATE_API_BASE_URL, "series/get-unknown")
    for attempt in range(ATTEMPTS):
        try:
            response = requests.get(url, timeout=5)
            break
        except Exception as e:
            if attempt == ATTEMPTS - 1:
                LOGGER.error("Failed to fetch url %s. %s", url, e, exc_info=True)
                return None
    
    if not response.ok:
        LOGGER.error("Private API returned bad response %s when attempting to get unknown series at %s", response.status_code, url)
        return None
    
    return response.json()["id"]

def get_unknown_events() -> List[int] | None:
    ATTEMPTS = 10
    url = urljoin(PRIVATE_API_BASE_URL, "event/get-unknown")
    for attempt in range(ATTEMPTS):
        try:
            response = requests.get(url, timeout=5)
            break
        except Exception as e:
            if attempt == ATTEMPTS - 1:
                LOGGER.error("Failed to fetch url %s. %s", url, e, exc_info=True)
                return None
    
    if not response.ok:
        LOGGER.error("Private API returned bad response %s when attempting to get unknown events at %s", response.status_code, url)
        return None
    
    return response.json()["id"]

def get_unknown_events_diff(event_ids_to_diff: List[int]) -> List[int] | None:
    ATTEMPTS = 10
    url = urljoin(PRIVATE_API_BASE_URL, "event/get-unknown-diff")
    for attempt in range(ATTEMPTS):
        try:
            response = requests.get(url, timeout=5, params={
                "id": event_ids_to_diff
            })
            break
        except Exception as e:
            if attempt == ATTEMPTS - 1:
                LOGGER.error("Failed to fetch url %s. %s", url, e, exc_info=True)
                return None
    
    if not response.ok:
        LOGGER.error("Private API returned bad response %s when attempting to get unknown events at %s", response.status_code, url)
        return None

    return [] if not response.json()["id"] else response.json()["id"]