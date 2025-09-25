import argparse
import atexit
import os
import time
from datetime import datetime, timedelta, timezone

import psycopg2

from logging_config import MAIN_LOGGER as LOGGER
from pg_connection.PostgresPool import PostgresPool
from scraper.entities import VLRSeries
from scraper.scraper import VLRScraper, VLRScraperOptions
from telegram_notify.telegram_utils import send_telegram_msg

SCRAPER: VLRScraper
DB_POOL: PostgresPool = PostgresPool()

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
    # debugSeries(74) # vct-2025
    # debugSeries(4) # none

    # debugTeam(624) # prx
    # debugTeam(6387) # bleed
    LOGGER.debug(SCRAPER.scrape_match(542265))

def debugTeam(team_id: int):
    team = SCRAPER.scrape_team(team_id=team_id)

    LOGGER.debug(team)

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
    send_telegram_msg("vlr gg scraper is starting up!")

    atexit.register(DB_POOL.close_all) # Ensure all db connections close gracefully on script termination
    atexit.register(send_telegram_msg, "vlr gg scraper is shutting down.")
    # parser = argparse.ArgumentParser(description="Nebby's vlr scraper")

    main();