import argparse
import atexit
from enum import Enum
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List

import psycopg2
import requests

from logging_config import MAIN_LOGGER as LOGGER
from private_api_utils.private_api_bulk import bulk_insert_events, bulk_insert_matches, bulk_insert_results, bulk_insert_series, bulk_insert_teams
from scheduler.scraper_scheduler import ScrapeScheduler
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scraper.entities import VLRResult, VLRSeries, VLRTeam
from scraper.scraper import VLRScraper, VLRScraperOptions
from scraping_services.initial_run import do_initial_run
from telegram_notify.telegram_utils import send_telegram_msg

SCRAPER: VLRScraper
SCRAPE_SCHEDULER: ScrapeScheduler

def initialise_scraper():
    global SCRAPER, SCRAPE_SCHEDULER

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
    SCRAPE_SCHEDULER = ScrapeScheduler(SCRAPER)

def main():
    global SCRAPER, SCRAPE_SCHEDULER

    SCRAPE_SCHEDULER.enqueue_task(
        ScraperTask(
            task_type=ScraperTaskType.SCRAPE_SERIES,
            id=85,
            recursive=False
        )
    )

    # SCRAPE_SCHEDULER.enqueue_task(
    #     ScraperTask(
    #         task_type=ScraperTaskType.SCRAPE_SERIES,
    #         id=74,
    #         recursive=False
    #     )
    # )
    # SCRAPE_SCHEDULER.enqueue_task(
    #     ScraperTask(
    #         task_type=ScraperTaskType.SCRAPE_EVENT,
    #         id=2283,
    #         context={
    #             'id':74
    #         },
    #         recursive=True
    #     )
    # )

    # for i in range(70, 80):
    #     debugSeries(i)

    # debugSeries(79) # project-v
    # debugSeries(74) # vct-2025
    # debugSeries(4) # none

    # debugTeam(624) # prx
    # debugTeam(6387) # bleed
    # LOGGER.debug(SCRAPER.scrape_match(542265))

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

def debugScraperTasks():
    # Scrape vct-2025 series
    SCRAPE_SCHEDULER.enqueue_task(
        ScraperTask(
            task_type=ScraperTaskType.SCRAPE_SERIES,
            id=74,
            recursive=False
        ), 0
    )

    # Scrape vct champs 2025 event
    SCRAPE_SCHEDULER.enqueue_task(
        ScraperTask(
            task_type=ScraperTaskType.SCRAPE_EVENT,
            id=2283,
            context={
                "id": 74
            },
            recursive=False
        ), 0
    )

    # Scrape vct champs 2025 first few games of the group stage
    SCRAPE_SCHEDULER.enqueue_task(
        ScraperTask(
            task_type=ScraperTaskType.SCRAPE_MATCH,
            id=542265,
            context={
                "id":2283
            },
            recursive=False
        ), 0
    )
    SCRAPE_SCHEDULER.enqueue_task(
        ScraperTask(
            task_type=ScraperTaskType.SCRAPE_MATCH,
            id=542266,
            context={
                "id":2283
            },
            recursive=False
        ), 0
    )
    SCRAPE_SCHEDULER.enqueue_task(
        ScraperTask(
            task_type=ScraperTaskType.SCRAPE_MATCH,
            id=542267,
            context={
                "id":2283
            },
            recursive=False
        ), 0
    )
    SCRAPE_SCHEDULER.enqueue_task(
        ScraperTask(
            task_type=ScraperTaskType.SCRAPE_MATCH,
            id=542268,
            context={
                "id":2283
            },
            recursive=False
        ), 0
    )
    SCRAPE_SCHEDULER.enqueue_task(
        ScraperTask(
            task_type=ScraperTaskType.SCRAPE_MATCH,
            id=542269,
            context={
                "id":2283
            },
            recursive=False
        ), 0
    )

if __name__ == "__main__":
    send_telegram_msg("vlr gg scraper is starting up!")

    atexit.register(send_telegram_msg, "vlr gg scraper is shutting down.")
    # parser = argparse.ArgumentParser(description="Nebby's vlr scraper")

    parser = argparse.ArgumentParser(description="vlrgg scraper tool")

    parser.add_argument("--build", action="store_true", help="Will build the initial database by scraping vlr.gg from beginning to end recursively.")

    args = parser.parse_args()

    initialise_scraper()

    if args.build:
        do_initial_run(SCRAPER, SCRAPE_SCHEDULER)
    else:
        main();

    try:
        while True:
            time.sleep(300) # Sleep for 300 seconds

            # Write to db
            results: Dict[str, VLRResult] = SCRAPE_SCHEDULER.get_result_set()
            res = bulk_insert_results(results)

            if not res:
                LOGGER.error("Failed to bulk insert. No response object for %s. Likely due to network timeout.", results)
                # TODO: Store failed bulk insert due to network timeout
            elif not res.ok:
                # Error
                LOGGER.error("Received error message from bulk insertion %s. Code: %s", res, res.code)
                LOGGER.error("Erroneous result set: ", results)

    except KeyboardInterrupt:
        LOGGER.info("Shutting down...")