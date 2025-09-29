from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ScraperTaskType(Enum):
    SCRAPE_SERIES=0
    SCRAPE_EVENT=1
    SCRAPE_MATCH=2
    SCRAPE_TEAM=3

@dataclass
class ScraperTask():
    task_type: ScraperTaskType
    id: Optional[int]
    context: Optional[dict[str, any]] = None
    recursive: bool = False