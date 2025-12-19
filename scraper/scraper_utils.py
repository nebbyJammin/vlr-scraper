from logging_config import VLR_LOGGER as LOGGER
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from functools import wraps
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

@dataclass
class VLRScraperOptions:
    """The options used by the VLRScraper class"""
    timeout: int = 10
    local_tz: str = "UTC"

class VLRScraperMode(Enum):
    """The different modes that the VLRScraper can use. Each mode usually represents a different entity."""
    SERIES=0
    EVENT=1
    MATCH=2
    TEAM=3
    EVENT_MATCHES=10

BASE_URL = "https://vlr.gg/"
SCRAPER_MODE_TO_URL_ENDPOINT = {
    VLRScraperMode.SERIES: "series",
    VLRScraperMode.EVENT: "event",
    VLRScraperMode.EVENT_MATCHES: "matches",
    VLRScraperMode.MATCH: "",
    VLRScraperMode.TEAM: "team",
}

def get_vlr_url(path: str) -> str:
    return urljoin(BASE_URL, path)

def soup_cast(func):
    """A decorator that ensures the root is casted into the correct type."""
    @wraps(func)
    def wrapper(root, *args, **kwargs):
        if not isinstance(root, Tag) and not isinstance(root, BeautifulSoup):
            raise TypeError(f"Invalid argument {root} entered. Expected Tag, BeautifulSoup or str")
        if isinstance(root, str):
            root = BeautifulSoup(root, "lxml")
        return func(root, *args, **kwargs)
    
    return wrapper

def get_id_from_url(mode: VLRScraperMode, url: str) -> int | None:
    """
    Takes a url from the vlr.gg website and tries to extract the id from that url.

    Generally urls can look like:
    vlr.gg/event/2281/the-event-name-of-event-2281
    
    The scraper only cares about the '2281' part, which corresponds to the id of the event.
    
    This function tries to unpack the url as a string and return the id part.

    Ensure the correct `VLRScraperMode` is specified as each entity uses a different protocol to encode their URL endpoints.

    Returns the id if successful, else will return None.
    """
    if not isinstance(mode, VLRScraperMode):
        LOGGER.error(f"Invalid scraper mode entered. Mode was of type '{mode.__class__}'")
    if not isinstance(url, str):
        LOGGER.error(f"Invalid url entered. URL was of type '{mode.__class__}'")
        
    url = url.strip()

    paths: list[str] = url.split('/')
        
    id: int | None = None
    id_as_string: str
    if mode == VLRScraperMode.MATCH:
        # Matches do not have a special URL path prefix
        for i, path in enumerate(paths):
            if len(path) == 0:
                if i < len(paths) - 1:
                    id_as_string = paths[i + 1]
                else:
                    LOGGER.error(f"No ID could be extracted from URL '{url}'")
                    return None
            else:
                # Try to just cast current path as a number
                id_as_string = path

            try:
                id = int(id_as_string)
                break
            except ValueError:
                continue
    else:
        scraper_prefix: str = SCRAPER_MODE_TO_URL_ENDPOINT.get(mode, "")

        prefix_idx = paths.index(scraper_prefix)
        if prefix_idx < len(paths) - 1:
            id_as_string = paths[prefix_idx + 1]
            try:
                id = int(id_as_string)
            except ValueError:
                LOGGER.error(f"Got invalid ID from {mode}")
                return None
        else:
            LOGGER.error(f"No ID could be extracted from URL {url}")
            return None


    return id