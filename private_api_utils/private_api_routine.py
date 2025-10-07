from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from private_api_utils.private_api_utils import PRIVATE_API_BASE_URL
from logging_config import PRIVATE_API_LOGGER as LOGGER

def unpack_tasks(scraper_tasks: List[ScraperTask], response: requests.Response):
    """
    Unpacks the response from the FastAPI private api server and appends each response item to the end of the `scraper_tasks` list. 
    Typically, call this when handling a response such as getting low/high priority tasks.
    """

    data: Dict[str, Any] = response.json()
    data: Dict[str, Dict[str, Any]] = data["data"]
    if "match" in data.keys() and isinstance(data["match"], List):
        scraper_tasks.extend([
            ScraperTask(
                ScraperTaskType.SCRAPE_MATCH,
                id=match_json["id"],
                context={
                    'id': match_json["event_id"],
                    'priority': match_json.get("priority", 0)
                },
                recursive=False,
            ) for match_json in data["match"]
        ])

    if "event" in data.keys() and isinstance(data["event"], List):
        scraper_tasks.extend([
            ScraperTask(
                ScraperTaskType.SCRAPE_EVENT,
                id=event_json["id"],
                context={
                    "id": event_json["series_id"],
                    'priority': event_json.get("priority", 0)
                },
                recursive=False,
            ) for event_json in data["event"]
        ])

    if "series" in data.keys() and isinstance(data["series"], List):
        scraper_tasks.extend([
            ScraperTask(
                ScraperTaskType.SCRAPE_TEAM,
                id=series_json["id"],
                context={
                    'priority': series_json.get("priority", 0)
                },
                recursive=False,
            ) for series_json in data["series"]
        ])
    
    if "team" in data.keys() and isinstance(data["team"], List):
        scraper_tasks.extend([
            ScraperTask(
                ScraperTaskType.SCRAPE_TEAM,
                id=team_json["id"],
                recursive=False,
                context={
                    'priority': team_json.get("priority", 0)
                },
            ) for team_json in data["team"]
        ])
    

def get_high_priority_tasks_routine() -> List[ScraperTask] | None:
    """
    Returns a list of scraper tasks the represent the tasks that need to be scraped at a high priority level.
    This usually includes things like upcoming/ongoing events and matches.
    """

    ATTEMPTS = 10
    for attempt in range(ATTEMPTS):
        try:
            response = requests.get(
                url=urljoin(PRIVATE_API_BASE_URL, "routine/high-priority"),
                timeout=10,
            )
        except Exception as e:
            if attempt == ATTEMPTS - 1:
                LOGGER.error("Failed to fetch high-priority routine %s", e, exc_info=True)
                return None
    
    if not response.ok:
        return None
    
    scraper_tasks: List[ScraperTask] = []
    unpack_tasks(scraper_tasks, response)

    return scraper_tasks

def get_low_priority_tasks_routine() -> List[ScraperTask] | None:
    """
    Returns a list of scraper tasks that represent the tasks that need to be scraped at a low priority level. 
    This usually includes things like completed events/matches that haven't been scraped in a while.
    It is important to do this to ensure data isn't outdated - however, for vlr.gg, it is extremely unlikely for completed entities to update after completion.
    """

    ATTEMPTS = 10
    for attempt in range(ATTEMPTS):
        try:
            response = requests.get(
                url=urljoin(PRIVATE_API_BASE_URL, "routine/low-priority"),
                timeout=10,
            )
        except Exception as e:
            if attempt == ATTEMPTS - 1:
                LOGGER.error("Failed to fetch low-priority routine %s", e, exc_info=True)
                return None
    
    if not response.ok:
        return None
    
    scraper_tasks: List[ScraperTask] = []
    unpack_tasks(scraper_tasks, response)

    return scraper_tasks