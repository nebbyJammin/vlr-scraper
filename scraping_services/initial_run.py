import os
from typing import List, Set
from scheduler.scraper_scheduler import ScrapeScheduler
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scraper.scraper import VLRScraper
from scraper.scraper_utils import VLRScraperOptions
from private_api_utils.discover import get_known_series, get_unknown_events, get_unknown_events_diff
from logging_config import MAIN_LOGGER as LOGGER

def discover_series(SCRAPER: VLRScraper, SCRAPE_SCHEDULER: ScrapeScheduler, series_upper: int | None = None, ignore_seen: bool = False):
    """Enqueues any series that has not yet been discovered to the Scrape Scheduler. 
    Requires the private api to be available."""
    already_seen_series: List[int] | None = get_known_series()
    new_series: List[int] | None = SCRAPER.discover_series(already_seen_series, series_upper) if not ignore_seen else SCRAPER.discover_series(None, series_upper)

    # Recursively scrape all series that have just been discovered/probed.
    for series_id in new_series:
        SCRAPE_SCHEDULER.enqueue_task(
            ScraperTask(
                task_type=ScraperTaskType.SCRAPE_SERIES,
                id=series_id,
                recursive=True,
            ),
            2000 # High priority
        )

def discover_front_page_events(SCRAPER: VLRScraper, SCRAPE_SCHEDULER: ScrapeScheduler):
    """Enqueues all front page events that have not been discovered. 
    This is important to discover events with no parent series. 
    Requires the private api to be available."""
    front_page_event_ids: List[int] = SCRAPER.discover_front_page_event_ids()
    new_event_ids = get_unknown_events_diff(front_page_event_ids)

    LOGGER.info("Discovering front page events: %s", new_event_ids)

    if new_event_ids:
        for event_id in new_event_ids:
            SCRAPE_SCHEDULER.enqueue_task(
                ScraperTask(
                    task_type=ScraperTaskType.SCRAPE_EVENT,
                    id=event_id,
                    recursive=True,
                ),
                1050 # High priority
            )

def discover_lone_events(SCRAPER: VLRScraper, SCRAPE_SCHEDULER: ScrapeScheduler):
    """Enqueues all events that have not been discovered. 
    This is important to fill in the gaps and discover events that have no parent series. 
    USE THIS ONLY AFTER `discover_series()` HAS BEEN CALLED RECENTLY i.e. the database is mostly up to date.
    Requires the private api to be available. 
    """
    unknown_events: List[int] | None = get_unknown_events()

    LOGGER.info('Discovering lone events: %s', unknown_events)

    # Recursively scrape all events that have no parent series.
    if unknown_events:
        for event_id in unknown_events:
            SCRAPE_SCHEDULER.enqueue_task(
                ScraperTask(
                    task_type=ScraperTaskType.SCRAPE_EVENT,
                    id=event_id,
                    recursive=True,
                ),
                1000 # High priority
            )
