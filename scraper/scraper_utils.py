
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from functools import wraps
from urllib.parse import urljoin

from bs4 import BeautifulSoup

@dataclass
class VLRScraperOptions:
    timeout: int = 10
    local_tz: str = "UTC"
    vlr_utc_offset: timedelta = timedelta(hours=4)

class VLRScraperMode(Enum):
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
    @wraps(func)
    def wrapper(root, *args, **kwargs):
        if isinstance(root, str):
            root = BeautifulSoup(root, "lxml")
        return func(root, *args, **kwargs)
    
    return wrapper