import os
from scheduler.scraper_scheduler import ScrapeScheduler
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scraper.scraper import VLRScraper
from scraper.scraper_utils import VLRScraperOptions
from logging_config import MAIN_LOGGER as LOGGER

def do_initial_run(SCRAPER: VLRScraper, SCRAPE_SCHEDULER: ScrapeScheduler, series_upper: int):
    """Scans every series->event->match->team recursively. May take up to 24 hours depending on worker count + sleep time. It is recommended to have ~20 workers with average sleep time of 1s."""
    for id in range(0,series_upper + 1):
        SCRAPE_SCHEDULER.enqueue_task(
            ScraperTask(
                task_type=ScraperTaskType.SCRAPE_SERIES,
                id=id,
                recursive=True,
            ), 100
        )