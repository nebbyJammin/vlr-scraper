import pickle
from dotenv import load_dotenv

load_dotenv()

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
from private_api_utils.private_api_bulk import bulk_insert_results
from private_api_utils.private_api_routine import get_high_priority_tasks_routine, get_low_priority_tasks_routine
from private_api_utils.private_api_utils import serializer
from scheduler.scraper_scheduler import ScrapeScheduler
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scraper.entities import VLRResult, VLRSeries, VLRTeam
from scraper.scraper import VLRScraper, VLRScraperOptions
from scraping_services.initial_run import do_initial_run
from telegram_notify.telegram_utils import send_telegram_msg
from apscheduler.schedulers.background import BackgroundScheduler

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
    SCRAPE_SCHEDULER = ScrapeScheduler(SCRAPER, NUM_SCRAPER_WORKERS)

def handle_high_priority_tasks():
    global SCRAPER, SCRAPE_SCHEDULER

    tasks = get_high_priority_tasks_routine()

    for task in tasks:
        SCRAPE_SCHEDULER.enqueue_task(task, task.context.get("priority", 1))

def handle_low_priority_tasks():
    global SCRAPER, SCRAPE_SCHEDULER

    tasks = get_low_priority_tasks_routine()

    for task in tasks:
        SCRAPE_SCHEDULER.enqueue_task(task, task.context.get("priority", 0))

def main():
    global SCRAPER, SCRAPE_SCHEDULE, HIGH_PRIORITY_FREQUENCY, LOW_PRIORITY_FREQUENCY

    high_priority_scheduler = BackgroundScheduler()
    high_priority_scheduler.start()
    high_priority_scheduler.add_job(handle_high_priority_tasks, 'interval', seconds=HIGH_PRIORITY_FREQUENCY, max_instances=1)

    atexit.register(lambda: high_priority_scheduler.shutdown(wait=False))

    low_priority_scheduler = BackgroundScheduler()
    low_priority_scheduler.start()
    low_priority_scheduler.add_job(handle_low_priority_tasks, 'interval', seconds=LOW_PRIORITY_FREQUENCY)

    atexit.register(lambda: low_priority_scheduler.shutdown(wait=False))


if __name__ == "__main__":

    atexit.register(send_telegram_msg, "vlr gg scraper is shutting down.")
    parser = argparse.ArgumentParser(description="A webscraper for vlr.gg that has a focus on scraping match, team and event data. The webscraper stores scraped data into a postgres database by hitting an external API.")

    parser.add_argument("--build", '-b', type=int, help="Specify a count (>0). The scraper will do an initial run to build the database, by recursively scraping each series->event->match->team, starting from series id = 0, up to the series id entered.")

    args = parser.parse_args()
    send_telegram_msg("vlr gg scraper is starting up!")

    try:
        BULK_INSERT_FREQUENCY = os.getenv("BULK_INSERT_FREQUENCY", 90)
    except (TypeError, ValueError):
        BULK_INSERT_FREQUENCY = 90
    
    try:
        HIGH_PRIORITY_FREQUENCY = os.getenv("HIGH_PRIORITY_FREQUENCY", 60)
    except (TypeError, ValueError):
        HIGH_PRIORITY_FREQUENCY = 60
    
    try:
        LOW_PRIORITY_FREQUENCY = os.getenv("LOW_PRIORITY_FREQUENCY", 21600)
    except (TypeError, ValueError):
        LOW_PRIORITY_FREQUENCY = 21600

    try:
        NUM_SCRAPER_WORKERS = os.getenv("NUM_SCRAPER_WORKERS", 20)
    except (TypeError, ValueError):
        NUM_SCRAPER_WORKERS = 20

    initialise_scraper()

    if args.build is not None:
        if args.build <= 0:
            LOGGER.error("Invalid args entered for build. Series id of %s is not valid!", args.build)
        do_initial_run(SCRAPER, SCRAPE_SCHEDULER, args.build)
    else:
        main();

    failed_payloads: List[tuple[str, Dict[str, any]]] = []
    try:
        while True:
            time.sleep(BULK_INSERT_FREQUENCY) # Sleep for 60 seconds by default

            # Write to db
            results: Dict[str, VLRResult] = SCRAPE_SCHEDULER.get_result_set()
            failed_payloads = bulk_insert_results(results)

            failed_payloads.extend(failed_payloads)

    except KeyboardInterrupt:
        LOGGER.info("Shutting down...")
    
    if len(failed_payloads) > 0:
        filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        with open(f"failed_payloads/{filename}", "wb") as f:
            pickle.dump(failed_payloads, f)