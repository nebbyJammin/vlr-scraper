import os
from scheduler.scraper_scheduler import ScrapeScheduler
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scraper.scraper import VLRScraper
from scraper.scraper_utils import VLRScraperOptions
from logging_config import MAIN_LOGGER as LOGGER

def do_initial_run(SCRAPER: VLRScraper, SCRAPE_SCHEDULER: ScrapeScheduler):
    # Testing, let's do series id 70 to current
    for id in range(70, 85):
        SCRAPE_SCHEDULER.enqueue_task(
            ScraperTask(
                task_type=ScraperTaskType.SCRAPE_SERIES,
                id=id,
                recursive=True,
            ), 100
        )