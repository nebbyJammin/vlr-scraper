import atexit
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from itertools import count
from queue import Empty, PriorityQueue
import random
import threading
import time
from typing import Dict, List, Optional, Set, Tuple
from logging_config import MAIN_LOGGER as LOGGER
from apscheduler.schedulers.background import BackgroundScheduler

from scheduler.scraper_tasks import ScraperTask, ScraperTaskType
from scheduler.vlr_result_store import ResultStore
from scraper.entities import VLRResult, VLREvent, VLRMatch, VLRSeries, VLRTeam
from scraper.scraper import VLRScraper

class ScrapeScheduler():
    """
    The class that uses a single instance of the `VLRScraper` class and orchestrates multiple threads to pull from a queue of tasks and scrape more efficiently. 
    For `max_workers`, as of 7/10/2025, somewhere between 20-25 seems to be the upper limit without being rate limited. 
    It is strongly recommended to go with 20 workers in the thread pool.
    """

    MIN_SLEEP_TIME = 0.5
    MAX_SLEEP_TIME = 2

    def __init__(self, VLR_Scraper: VLRScraper, max_workers: int = 20):
        self._scraper = VLR_Scraper
        self._random = random.Random(time.time())

        self._task_queue: PriorityQueue[Tuple[int, ScraperTask]] = PriorityQueue()
        self._task_counter = count()
        self._is_completing_scraper_tasks = False
        self._task_thread_pool_executor = ThreadPoolExecutor(max_workers=max_workers)

        self._results_lock = threading.Lock()
        self._result_store = ResultStore(self._results_lock)

        self._task_scheduler_lock = threading.Lock()

        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        self._scheduler.add_job(self._task_scheduler_heartbeat, 'interval', seconds=10, max_instances=1)

        atexit.register(self.shutdown) # register shutdown atexit

    def shutdown(self):
        """Shut down the executor and scheduler safely"""
        self._task_thread_pool_executor.shutdown(wait=False)
        self._scheduler.shutdown(wait=False)

    def _do_random_sleep(self):
        """Sleeps a random time interval"""
        random_time = self._random.uniform(ScrapeScheduler.MIN_SLEEP_TIME, ScrapeScheduler.MAX_SLEEP_TIME)
        time.sleep(random_time)

    def _append_result(self, *results: VLRResult): 
        self._result_store.append_results(*results)

    def get_result_set(self) -> Dict[str, List[VLRResult]]:
        """Returns a dictionary that contains each VLRResult grouped by type of VLRResult. Use series, event, match, team keys to access each VLRResult list."""
        return self._result_store.get_result_set()
    
    def _task_scheduler_heartbeat(self):
        """Checks if there are tasks to do. Will spawn a ThreadPoolExecutor to handle these tasks if there are tasks to complete."""

        LOGGER.info("Sending task scheduler heartbeat...")
        LOGGER.info("Estimated size of task queue is %s", self.get_task_qsize())

        with self._task_scheduler_lock:
            if self._is_completing_scraper_tasks:
                # Already completing scraper tasks just return
                LOGGER.info("Already completing scraper tasks...")
                return
        
            if self.get_task_qsize() > 0:
                # Start handling tasks
                self._is_completing_scraper_tasks = True # Update immediately so that we don't accidently spawn two thread pools.

        self._spawn_scraper_task_thread_pool()

    def _spawn_scraper_task_thread_pool(self):
        """Delegates tasks to each thread in the thread pool."""

        LOGGER.info("Beginning to execute tasks - estimated size is %s", self.get_task_qsize())

        # Drain tasks into a batch
        tasks = []
        while True:
            try:
                _, _, task = self._task_queue.get_nowait()
                tasks.append(task)
            except Empty:
                break
        
        # Submit each task to the persistent executor
        futures = []
        for task in tasks:
            futures.append(
                self._task_thread_pool_executor.submit(
                    self._handle_task, task)
            )

        # for f in futures:
        #     try:
        #         f.result()
        #     except Exception as e:
        #         LOGGER.error(f"Failed to retrieve result.", exc_info=True)
        
        with self._task_scheduler_lock:
            self._is_completing_scraper_tasks = False

    def enqueue_task(self, task: ScraperTask, priority:int=0):
        """Tries to enqueue the task, if the task is already added, then silently fail and do not add to queue."""
        if self._result_store.try_enqueue_task(task):
            count_id: int = next(self._task_counter)
            self._task_queue.put((-priority, count_id, task))
    
    def remove_task_from_seen(self, task: ScraperTask):
        """Removes task from seen list. Usually, only call this if the task has failed somehow."""
        self._result_store.remove_task_from_seen(task)
    
    def get_task_qsize(self) -> int:
        """Calls queue.qsize(). Is unreliable (Not thread safe)."""
        return self._task_queue.qsize()
    
    def _handle_task(self, task: ScraperTask) -> any:
        """Handles a scraping task. Any dependent entities that need to be scraped will be scraped."""

        if task.task_type == ScraperTaskType.SCRAPE_SERIES:
            LOGGER.info(f"Scraping series task {task.id, task}")
            success = self._handle_scrape_series_task(task)
        elif task.task_type == ScraperTaskType.SCRAPE_EVENT:
            LOGGER.info(f"Scraping event task {task.id, task}")
            success = self._handle_scrape_event_task(task)
        elif task.task_type == ScraperTaskType.SCRAPE_MATCH:
            LOGGER.info(f"Scraping match task {task.id, task}")
            success = self._handle_scrape_match_task(task)
        elif task.task_type == ScraperTaskType.SCRAPE_TEAM:
            LOGGER.info(f"Scraping team task {task.id, task}")
            success = self._handle_scrape_team_task(task)
        
        if not success:
            LOGGER.error("Unsuccessful scrape for task %s. Attempting to remove from seen list.", task)
            removed = self.remove_task_from_seen(task)
            if removed:
                LOGGER.info("Successfully removed from seen list.")
            else:
                LOGGER.warning("Failed to remove from seen list.")
            
    
    def _handle_scrape_series_task(self, task: ScraperTask) -> bool:
        if not task.id:
            LOGGER.error(f"Could not begin scraper task {task}. Unknown ID given.")
            return False

        series, dependent_event_ids = self._scraper.scrape_series(task.id)

        if series:
            self._append_result(series)

            if task.recursive:
                for event_id in dependent_event_ids:
                    self.enqueue_task(
                        task=ScraperTask(
                            task_type=ScraperTaskType.SCRAPE_EVENT, 
                            id=event_id, 
                            context={ 
                                "id": task.id # Set the parent series id to the origin task.id
                            },
                            recursive=True
                        ),
                        priority=10
                    )

            return True
        else:
            return False
    
    def _handle_scrape_event_task(self, task: ScraperTask) -> bool:
        if not task.id:
            LOGGER.error(f"Could not begin scraper task {task}. Unknown ID given.")
            return False

        # if not task.context or not task.context.get("id"):
        #     LOGGER.error(f"Could not begin scraper task {task}. Insufficient context given. Check if context dict is defined, and task.context[id] provides context for the dependent series.")
        #     return False

        if task.context:
            series_id = task.context.get("id")
        else:
            series_id = None

        event, dependent_match_ids = self._scraper.scrape_event(task.id, series_id=series_id)

        if event:
            self._append_result(event)

            if task.recursive:
                for match_id in dependent_match_ids:
                    self.enqueue_task(
                        task=ScraperTask(
                            task_type=ScraperTaskType.SCRAPE_MATCH,
                            id=match_id,
                            context={
                                "id": task.id
                            },
                            recursive=True
                        ),
                        priority=20
                    )
                
            return True
        else:
            return False
    
    def _handle_scrape_match_task(self, task: ScraperTask) -> bool:
        if not task.id:
            LOGGER.error(f"Could not begin scraper task {task}. Unknown ID given.")
            return False

        if not task.context or not task.context.get("id"):
            LOGGER.error(f"Could not begin scraper task {task}. Insufficient context given. Check if context dict is defined, and task.context[id] provides context for the dependent event.")
            return False
        
        match = self._scraper.scrape_match(task.id, task.context.get("id"))
        team_1, team_2 = None, None

        if match:
            # Immediately scrape the dependent teams -> match has a foreign key for team id that needs to be scraped (IRRESPECTIVE OF task.recursive)

            # ! It's okay not to use the lock here since the only time we get a false positive is if we have scraped the team previously -> cleared the batch -> inserted batch into db while this method is running
            if match:
                if match.team_1_id and match.team_1_id not in self._result_store.get_seen_team_ids():
                    team_1 = self._scraper.scrape_team(match.team_1_id)
                if match.team_2_id and match.team_2_id not in self._result_store.get_seen_team_ids():
                    team_2 = self._scraper.scrape_team(match.team_2_id)
            
                # Append results at the same time to ensure thread safety
                self._append_result(match, team_1, team_2)
            return True
        else:
            return False
        
    
    def _handle_scrape_team_task(self, task: ScraperTask) -> bool:
        if not task.id:
            LOGGER.error(f"Could not begin scraper task {task}. Unknown ID given.")
            return False

        team = self._scraper.scrape_team(task.id)

        if team:
            self._append_result(team)
            return True
        else:
            return False

