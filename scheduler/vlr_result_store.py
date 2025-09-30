from collections import deque
import threading
from typing import Dict, List, Set

from scheduler.scraper_scheduler import ScraperTask, ScraperTaskType
from scraper.entities import VLREvent, VLRMatch, VLRResult, VLRSeries, VLRTeam

from logging_config import MAIN_LOGGER as LOGGER

class ResultStore():
    def __init__(self, results_lock: threading.Lock):
        self._series_results: deque[VLRSeries] = deque()
        self._event_results: deque[VLREvent] = deque()
        self._match_results: deque[VLRMatch] = deque()
        self._team_results: deque[VLRTeam] = deque()

        self._results = (self._series_results, self._event_results, self._match_results, self._team_results)

        self._seen_series_ids: Set[int] = set()
        self._seen_event_ids: Set[int] = set()
        self._seen_match_ids: Set[int] = set()
        self._seen_team_ids: Set[int] = set()

        self._seen_ids = (self._seen_series_ids, self._seen_event_ids, self._seen_match_ids, self._seen_team_ids)

        self._results_lock = results_lock
    
    def get_lock(self) -> threading.Lock:
        return self._results_lock
    
    def get_seen_series_ids(self) -> Set[int]:
        return self._seen_series_ids

    def get_seen_event_ids(self) -> Set[int]:
        return self._seen_event_ids

    def get_seen_match_ids(self) -> Set[int]:
        return self._seen_match_ids

    def get_seen_team_ids(self) -> Set[int]:
        return self._seen_team_ids
    
    def remove_task_from_seen(self, task: ScraperTask) -> bool:
        already_scraped_set: Set[int]

        with self._results_lock:
            match task.task_type:
                case ScraperTaskType.SCRAPE_SERIES:
                    already_scraped_set = self._seen_series_ids
                case ScraperTaskType.SCRAPE_EVENT:
                    already_scraped_set = self._seen_event_ids
                case ScraperTaskType.SCRAPE_MATCH:
                    already_scraped_set = self._seen_match_ids
                case ScraperTaskType.SCRAPE_TEAM:
                    already_scraped_set = self._seen_team_ids
                case _:
                    LOGGER.error("Failed to add VLR")
                    return False
                
            if task.id in already_scraped_set:
                already_scraped_set.remove(task.id)
                return True
            else:
                return False
    
    def try_enqueue_task(self, task: ScraperTask) -> bool:
        already_scraped_set: Set[int]

        with self._results_lock:
            match task.task_type:
                case ScraperTaskType.SCRAPE_SERIES:
                    already_scraped_set = self._seen_series_ids
                case ScraperTaskType.SCRAPE_EVENT:
                    already_scraped_set = self._seen_event_ids
                case ScraperTaskType.SCRAPE_MATCH:
                    already_scraped_set = self._seen_match_ids
                case ScraperTaskType.SCRAPE_TEAM:
                    already_scraped_set = self._seen_team_ids
                case _:
                    LOGGER.error("Failed to add VLR")
                    return False
            
            already_scraped = task.id in already_scraped_set

            if already_scraped:
                return False
            
            already_scraped_set.add(task.id)
            return True
    
    def append_results(self, *results: VLRResult):
        for result in results:
            with self._results_lock:
                if result == None:
                    continue
                elif isinstance(result, VLRSeries):
                    self._series_results.append(result)
                elif isinstance(result, VLREvent):
                    self._event_results.append(result)
                elif isinstance(result, VLRMatch):
                    self._match_results.append(result)
                elif isinstance(result, VLRTeam):
                    self._team_results.append(result)
                else:
                    LOGGER.error("Unknown VLRResult type passed into append_result, silently failing.")
    
    def get_result_set(self) -> Dict[str, List[VLRResult]]:
        result_dict = {}
        with self._results_lock:
            result_dict["series"] = list(self._series_results)
            result_dict["event"] = list(self._event_results)
            result_dict["match"] = list(self._match_results)
            result_dict["team"] = list(self._team_results)

            for result in self._results:
                result.clear()
            
            for set in self._seen_ids:
                set.clear()

            return result_dict