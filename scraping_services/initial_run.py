import os
from typing import List, Set
from scheduler.scraper_scheduler import ScrapeScheduler
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scraper.scraper import VLRScraper
from scraper.scraper_utils import VLRScraperOptions
from private_api_utils.discover import get_known_series, get_unknown_events, get_unknown_events_diff
from logging_config import MAIN_LOGGER as LOGGER

def do_initial_run(SCRAPER: VLRScraper, SCRAPE_SCHEDULER: ScrapeScheduler, series_upper: int | None = None):
    discover_series(SCRAPER, SCRAPE_SCHEDULER, series_upper)

def discover_series(SCRAPER: VLRScraper, SCRAPE_SCHEDULER: ScrapeScheduler, series_upper: int | None = None):
    already_seen_series: List[int] = get_known_series()
    new_series: List[int] = SCRAPER.discover_series(already_seen_series, series_upper)

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
    front_page_event_ids: List[int] = SCRAPER.discover_front_page_event_ids()
    new_event_ids = get_unknown_events_diff(front_page_event_ids)

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
    unknown_events: List[int] = get_unknown_events()

    LOGGER.debug(unknown_events)

    # Recursively scrape all events that have no parent series.
    for event_id in unknown_events:
        SCRAPE_SCHEDULER.enqueue_task(
            ScraperTask(
                task_type=ScraperTaskType.SCRAPE_EVENT,
                id=event_id,
                recursive=True,
            ),
            1000 # High priority
        )