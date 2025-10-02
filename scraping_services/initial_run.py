import os
from typing import List, Set
from scheduler.scraper_scheduler import ScrapeScheduler
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scraper.scraper import VLRScraper
from scraper.scraper_utils import VLRScraperOptions
from private_api_utils.probe import probed_series_diff
from logging_config import MAIN_LOGGER as LOGGER

def probe_series(SCRAPER: VLRScraper, SCRAPE_SCHEDULER: ScrapeScheduler, series_upper: int | None = None):
    series_list: List[int] = SCRAPER.probe_series(series_upper)
    new_series: Set[int] = probed_series_diff(series_list)

    LOGGER.debug(len(series_list))
    LOGGER.debug(len(new_series))

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