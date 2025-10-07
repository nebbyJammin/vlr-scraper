from dotenv import load_dotenv

from utils import dump_failed_payloads

load_dotenv()

import argparse
import atexit
from enum import Enum
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Set

import logging
import pickle

from logging_config import MAIN_LOGGER as LOGGER
from private_api_utils.private_api_bulk import bulk_insert_results
from private_api_utils.private_api_routine import get_high_priority_tasks_routine, get_low_priority_tasks_routine
from private_api_utils.private_api_utils import serializer
from scheduler.scraper_scheduler import ScrapeScheduler
from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scraper.entities import VLRResult, VLRSeries, VLRTeam
from scraper.scraper import VLRScraper, VLRScraperOptions
from scraping_services.initial_run import discover_front_page_events, discover_lone_events, discover_series
from telegram_notify.telegram_utils import send_telegram_msg
from apscheduler.schedulers.background import BackgroundScheduler

SCRAPER: VLRScraper
SCRAPE_SCHEDULER: ScrapeScheduler
FAILED_PAYLOADS: List[tuple[str, Dict[str, any]]] = []
SCHEDULING_CONTEXT: Dict[str, bool] = {
    "high_priority": True,
    "low_priority": True,
    "bulk_insert": True,
    "probe_series": True,
    "probe_events": True,
}

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

def handle_bulk_insertion():
    global FAILED_PAYLOADS

    # Write to db
    results: Dict[str, VLRResult] = SCRAPE_SCHEDULER.get_result_set()
    failed = bulk_insert_results(results)

    FAILED_PAYLOADS.extend(failed)
    

def main():
    global SCRAPER, SCRAPE_SCHEDULER
    # discover_front_page_events(SCRAPER, SCRAPE_SCHEDULER);
    # register_background_tasks()
    pass

def register_background_tasks():
    global SCRAPER, SCRAPE_SCHEDULER, HIGH_PRIORITY_FREQUENCY, LOW_PRIORITY_FREQUENCY, PROBE_SERIES_FREQUENCY

    background_scheduler = BackgroundScheduler()
    background_scheduler.start()

    if SCHEDULING_CONTEXT["high_priority"]:
        background_scheduler.add_job(handle_high_priority_tasks, 'interval', seconds=HIGH_PRIORITY_FREQUENCY, max_instances=1, next_run_time=datetime.now())
    if SCHEDULING_CONTEXT["low_priority"]:
        background_scheduler.add_job(handle_low_priority_tasks, 'interval', seconds=LOW_PRIORITY_FREQUENCY, next_run_time=datetime.now())
    if SCHEDULING_CONTEXT["probe_series"]:
        background_scheduler.add_job(discover_series, 'interval', seconds=PROBE_SERIES_FREQUENCY, next_run_time=datetime.now())
    if SCHEDULING_CONTEXT["probe_events"]:
        background_scheduler.add_job(lambda: discover_front_page_events(SCRAPER, SCRAPE_SCHEDULER), 'interval', seconds=PROBE_EVENTS_FREQUENCY, next_run_time=datetime.now())
    if SCHEDULING_CONTEXT["bulk_insert"]:
        background_scheduler.add_job(handle_bulk_insertion, 'interval', seconds=BULK_INSERT_FREQUENCY)

    atexit.register(lambda: background_scheduler.shutdown(wait=False))

if __name__ == "__main__":

    atexit.register(send_telegram_msg, "vlr gg scraper is shutting down.")
    parser = argparse.ArgumentParser(description="A webscraper for vlr.gg that has a focus on scraping match, team and event data. The webscraper stores scraped data into a postgres database by hitting an external API.")

    parser.add_argument("--build-series", nargs="?", type=int, help="Specify a count (>0). The scraper will do an initial run to build the database, by recursively scraping each series->event->match->team, starting from series id = 0, up to the series id entered OR until 10 404 responses are received. If no series id entered, then it will probe until 10 404 responses are received consecutively.", const=100000)

    parser.add_argument("--build-events", action="store_true", help="Use this flag to scrape old events with no parent series. ONLY USE THIS FLAG IF YOU HAVE USED --build-series FLAG TO SCRAPE ALL series->event->match->team with a parent series. Will attempt to scrape all events up until max(event_id).")

    parser.add_argument("--debug", "-d", action="store_true")

    args = parser.parse_args()
    send_telegram_msg("vlr gg scraper is starting up!")

    try:
        BULK_INSERT_FREQUENCY = int(os.getenv("BULK_INSERT_FREQUENCY", 90))
    except (TypeError, ValueError):
        BULK_INSERT_FREQUENCY = 90
    
    try:
        HIGH_PRIORITY_FREQUENCY = int(os.getenv("HIGH_PRIORITY_FREQUENCY", 60))
    except (TypeError, ValueError):
        HIGH_PRIORITY_FREQUENCY = 60
    
    try:
        LOW_PRIORITY_FREQUENCY = int(os.getenv("LOW_PRIORITY_FREQUENCY", 21600))
    except (TypeError, ValueError):
        LOW_PRIORITY_FREQUENCY = 21600

    try:
        NUM_SCRAPER_WORKERS = int(os.getenv("NUM_SCRAPER_WORKERS", 20))
    except (TypeError, ValueError):
        NUM_SCRAPER_WORKERS = 20

    try:
        PROBE_SERIES_FREQUENCY = int(os.getenv("PROBE_SERIES_FREQUENCY", 172800))
    except (TypeError, ValueError):
        PROBE_SERIES_FREQUENCY = 172800
    
    try:
        PROBE_EVENTS_FREQUENCY = int(os.getenv("PROBE_EVENT_FREQUENCY", 86400))
    except (TypeError, ValueError):
        PROBE_EVENTS_FREQUENCY = 86400

    initialise_scraper()

    if args.debug:
        logging.getLogger().setLevel("DEBUG")

    if args.build_series:
        if args.build_events:
            LOGGER.error("Cannot build event and build series at the same time. Do an initial run with --build-series first (if you haven't already), then run the program with --build-event flag to scrape all events with no parent series.")
            exit(1)

        if args.build_series <= 0:
            LOGGER.error("Invalid args entered for build. Series id of %s is not valid!", args.build_series)
            exit(1)

        SCHEDULING_CONTEXT["high_priority"] = False
        SCHEDULING_CONTEXT["low_priority"] = False
        SCHEDULING_CONTEXT["bulk_insert"] = True
        SCHEDULING_CONTEXT["probe_series"] = False
        SCHEDULING_CONTEXT["probe_events"] = False
        discover_series(SCRAPER, SCRAPE_SCHEDULER, args.build_series)

        register_background_tasks()
    elif args.build_events:
        SCHEDULING_CONTEXT["high_priority"] = False
        SCHEDULING_CONTEXT["low_priority"] = False
        SCHEDULING_CONTEXT["bulk_insert"] = True
        SCHEDULING_CONTEXT["probe_series"] = False
        SCHEDULING_CONTEXT["probe_events"] = False
        discover_lone_events(SCRAPER, SCRAPE_SCHEDULER)

        register_background_tasks()
    else:
        main();

    try:
        user_command = input(">")
        while True:
            match user_command:
                case "help":
                    print("""
                    'quit' | '!q' | 'exit' - forcefully closes the program.
                    """)
                case "quit" | "!q" | "exit":
                    break
                    
            user_command = input("> ")

    except KeyboardInterrupt as e:
        LOGGER.info("Received keyboard interrupt.")
    finally:
        LOGGER.info("Shutting down...")

    dump_failed_payloads(FAILED_PAYLOADS)