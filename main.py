
import time
from logging_config import MAIN_LOGGER as LOGGER
from scraper.entities import VLRSeries
from scraper.scraper import VLRScraper, VLRScraperOptions
import os

SCRAPER: VLRScraper

# TODO: USE APSCHEDULER to schedule scraping
def main():
    global SCRAPER  

    SCRAPER_OPTIONS = VLRScraperOptions(
        local_tz=os.getenv("LOCAL_TIME_ZONE", "UTC")
    )

    SCRAPER = VLRScraper(SCRAPER_OPTIONS)
    # for i in range(80):
    #     debugSeries(i)
    debugSeries(74) # vct-2025
    debugSeries(4) # none

def debugSeries(series_id: int):
    global SCRAPER

    series, event_ids = SCRAPER.scrape_series(series_id)
    LOGGER.debug(series)
    LOGGER.debug(event_ids)

    if series:
        event, match_ids = SCRAPER.scrape_event(event_ids.pop(), series_id)

        LOGGER.debug(event)
        LOGGER.debug(match_ids)
    
    time.sleep(0.5)



if __name__ == "__main__":
    main();