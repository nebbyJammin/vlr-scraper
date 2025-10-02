
from typing import Dict, List, Set
from urllib.parse import urljoin
from logging_config import PRIVATE_API_LOGGER as LOGGER

import requests

from private_api_utils.private_api_utils import PRIVATE_API_BASE_URL


def probed_series_diff(probed_series: List[int] | Set[int]) -> Set[int] | None:
    ATTEMPTS = 10
    url = urljoin(PRIVATE_API_BASE_URL, "series/probe")
    for attempt in range(ATTEMPTS):
        try:
            response = requests.get(url, timeout=5)
            break
        except Exception as e:
            if attempt == ATTEMPTS - 1:
                LOGGER.error("Failed to fetch url %s. %s", url, e, exc_info=True)
                return None
    
    if not response.ok:
        LOGGER.error("Private API returned bad response %s when attempting to probe at %s", response.status_code, url)
        return None
    
    data: Dict[str, any] = response.json()
    data: List[int] = data["known_series"]

    if isinstance(probed_series, list):
        probed_series = set(probed_series)
    
    if isinstance(probed_series, set):
        already_known_series = set(data)
        diff = probed_series.difference(already_known_series) 
        return diff
    else:
        LOGGER.error("Unexpected type %s for probed_series when trying to find probed_series diff.", probed_series.__class__)
        return None