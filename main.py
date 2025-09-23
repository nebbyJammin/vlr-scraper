from datetime import timedelta
from logging_config import MAIN_LOGGER as LOGGER
from scraper.entities import VLRSeries
from scraper.scraper import VLRScraper, VLRScraperOptions
import os
import time

SCRAPER: VLRScraper

# TODO: USE APSCHEDULER to schedule scraping
def main():
    global SCRAPER  

    vlr_utc_offset_str = os.getenv("VLR_UTC_OFFSET", 4)
    vlr_utc_offset: int = 4

    try:
        vlr_utc_offset = int(vlr_utc_offset_str)
    except (ValueError, TypeError) as e:
        vlr_utc_offset = 4

    SCRAPER_OPTIONS = VLRScraperOptions(
        local_tz=os.getenv("LOCAL_TIME_ZONE", "UTC"),
        vlr_utc_offset=vlr_utc_offset
    )

    SCRAPER = VLRScraper(SCRAPER_OPTIONS)
    # for i in range(70, 80):
    #     debugSeries(i)
    # debugSeries(79) # project-v
    debugSeries(74) # vct-2025
    # debugSeries(4) # none

def debugSeries(series_id: int):
    global SCRAPER

    series, event_ids = SCRAPER.scrape_series(series_id)
    LOGGER.debug(series)
    # LOGGER.debug(event_ids)

    if series:
        top_event_id = event_ids.pop(0)
        event, match_ids = SCRAPER.scrape_event(top_event_id, series_id)

        LOGGER.debug(event)
        # LOGGER.debug(match_ids)
    
        if event:
            # top_match_id = match_ids.pop(0)
            # match, team_ids = SCRAPER.scrape_match(top_match_id, top_event_id)

            # LOGGER.debug(match)

            # for match in match_ids:
            #     match, team_ids = SCRAPER.scrape_match(match, top_event_id)

            #     LOGGER.debug([match, team_ids])

            LOGGER.debug(SCRAPER.scrape_match(542279, event_id=top_event_id))



if __name__ == "__main__":
    main();