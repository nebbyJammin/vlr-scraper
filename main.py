import sys
from dotenv import load_dotenv

from utils import double_log, dump_failed_payloads

load_dotenv()

import argparse
import atexit
import os
import time
from datetime import timedelta, datetime
from typing import Dict, List, Any

import logging

from logging_config import MAIN_LOGGER as LOGGER
from private_api_utils.private_api_bulk import bulk_insert_results
from private_api_utils.private_api_routine import get_high_priority_tasks_routine, get_low_priority_tasks_routine
from scheduler.scraper_scheduler import ScrapeScheduler
from scraper.entities import VLRResult
from scraper.scraper import VLRScraper, VLRScraperOptions
from scraping_services.initial_run import discover_front_page_events, discover_lone_events, discover_series
from telegram_notify.telegram_utils import send_telegram_msg
from apscheduler.schedulers.background import BackgroundScheduler

SCRAPER: VLRScraper
SCRAPE_SCHEDULER: ScrapeScheduler
BACKGROUND_SCHEDULER: BackgroundScheduler
FAILED_PAYLOADS: List[tuple[str, Dict[str, Any]]] = []
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
        vlr_utc_offset=timedelta(hours=vlr_utc_offset)
    )

    SCRAPER = VLRScraper(SCRAPER_OPTIONS)
    SCRAPE_SCHEDULER = ScrapeScheduler(SCRAPER, NUM_SCRAPER_WORKERS)

def handle_high_priority_tasks():
    global SCRAPER, SCRAPE_SCHEDULER

    tasks = get_high_priority_tasks_routine()

    if not tasks:
        return

    for task in tasks:
        SCRAPE_SCHEDULER.enqueue_task(task, task.context.get("priority", 1))

def handle_low_priority_tasks():
    global SCRAPER, SCRAPE_SCHEDULER

    tasks = get_low_priority_tasks_routine()

    if not tasks:
        return

    for task in tasks:
        SCRAPE_SCHEDULER.enqueue_task(task, task.context.get("priority", 0))

def handle_bulk_insertion():
    global FAILED_PAYLOADS

    # Write to db
    results: Dict[str, List[VLRResult]] = SCRAPE_SCHEDULER.get_result_set()
    failed = bulk_insert_results(results)

    FAILED_PAYLOADS.extend(failed)
    

def main():
    global SCRAPER, SCRAPE_SCHEDULER
    register_background_tasks()

def register_background_tasks():
    global SCRAPER, SCRAPE_SCHEDULER, HIGH_PRIORITY_FREQUENCY, LOW_PRIORITY_FREQUENCY, PROBE_SERIES_FREQUENCY, BACKGROUND_SCHEDULER

    BACKGROUND_SCHEDULER = BackgroundScheduler()
    BACKGROUND_SCHEDULER.start()

    if SCHEDULING_CONTEXT["high_priority"]:
        BACKGROUND_SCHEDULER.add_job(handle_high_priority_tasks, 'interval', seconds=HIGH_PRIORITY_FREQUENCY, max_instances=1, next_run_time=datetime.now())
    if SCHEDULING_CONTEXT["low_priority"]:
        BACKGROUND_SCHEDULER.add_job(handle_low_priority_tasks, 'interval', seconds=LOW_PRIORITY_FREQUENCY, next_run_time=datetime.now())
    if SCHEDULING_CONTEXT["probe_series"]:
        BACKGROUND_SCHEDULER.add_job(lambda: discover_series(SCRAPER, SCRAPE_SCHEDULER), 'interval', seconds=PROBE_SERIES_FREQUENCY, next_run_time=datetime.now())
    if SCHEDULING_CONTEXT["probe_events"]:
        BACKGROUND_SCHEDULER.add_job(lambda: discover_front_page_events(SCRAPER, SCRAPE_SCHEDULER), 'interval', seconds=PROBE_EVENTS_FREQUENCY, next_run_time=datetime.now())
    if SCHEDULING_CONTEXT["bulk_insert"]:
        BACKGROUND_SCHEDULER.add_job(handle_bulk_insertion, 'interval', seconds=BULK_INSERT_FREQUENCY)

    atexit.register(lambda: BACKGROUND_SCHEDULER.shutdown(wait=False))

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
        discover_series(SCRAPER, SCRAPE_SCHEDULER, args.build_series, True)

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
        if not sys.stdin.isatty():
            while True:
                time.sleep(1)
        else:

            user_command = input(">")
            while True:
                args = user_command.strip().split(" ")

                if len(args) == 0:
                    continue

                match args[0]:
                    case "help" | "h":
                        print(
                        "Here are a list of commands you can run:\n" +\
                        "    help             - gives a list of commands.\n" +\
                        "    quit | !q | exit - forcefully closes the program.\n" +\
                        "    scheduler        - provides information and health checks on the scheduler.\n"\
                        , end="")
                    case "quit" | "!q" | "exit":
                        print("Exiting... (This may take a while as the program cleans up background threads. Ctrl+C OR forcefully end this process if this is taking too long)")
                        break
                    case "scheduler" | "sched":
                        scheduler_help_msg = \
                        "    scheduler flags:\n" +\
                        "        help                        - Gives a list of all commands\n" +\
                        "        qsize | size                - Gives a rough estimate for the number of items in the schedulers queue\n"

                        if len(args) > 1:
                            match args[1]:
                                case "help" | "h":
                                    print(scheduler_help_msg, end="")
                                case "qsize" | "size":
                                    qsize, consumed_qsize = SCRAPE_SCHEDULER.get_true_qsize()
                                    print(f"The scrape scheduler has {qsize + consumed_qsize} task(s) in the task queue, of which {qsize} have not been enqueued into the worker pool, and {consumed_qsize} have been enqueued and are waiting to be scraped.")
                                case _:
                                    print("Unknown command for scheduler received... Type 'help' or 'h' for a list of commands.")
                        else:
                            print(scheduler_help_msg, end="")
                    case _:
                        print("""
                        Unknown command entered. Type 'help' or 'h' for a list of commands.
                        """)
                    
                user_command = input("> ")
    except KeyboardInterrupt as e:
        double_log(LOGGER, "Received Keyboard Interrupt.")
    except Exception as e:
        double_log(LOGGER, "Received unknown exception. Forcefully cleaning up main thread...")
    finally:
        pass

    dump_failed_payloads(FAILED_PAYLOADS)

    double_log(LOGGER, "Shutting down...")
    sys.exit(0)
