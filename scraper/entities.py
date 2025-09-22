from dataclasses import asdict, dataclass
from typing import Optional
from datetime import date, datetime
from enum import Enum

class CompletionStatus(Enum):
    UNKNOWN=-1
    UPCOMING=0
    ONGOING=1
    COMPLETED=2

class TeamStatus(Enum):
    UNKNOWN=0
    INACTIVE=1
    ACTIVE=2

@dataclass
class BaseEntry:
    def to_dict(self):
        return asdict(self)

@dataclass
class VLRSeries(BaseEntry):
    vlr_id: int
    name: str
    description: Optional[str]
    status: CompletionStatus

@dataclass
class VLREvent(BaseEntry):
    vlr_id: int
    name: str
    status: CompletionStatus
    series_id: Optional[int]
    region: Optional[str]
    location_long: Optional[str]
    tags: list[str]
    prize: str
    date_str: Optional[str]
    date_start: Optional[datetime]
    date_end: Optional[datetime]
    thumbnail: Optional[str]

@dataclass
class VLRMatch(BaseEntry):
    vlr_id: int
    name: str
    stage: str
    status: CompletionStatus
    date_start: Optional[datetime]
    team_1_id: Optional[int]
    team_2_id: Optional[int]
    score_1: Optional[int]
    score_2: Optional[int]

@dataclass
class VLRTeam(BaseEntry):
    vlr_id: int
    name: str
    tricode: Optional[str]
    region: Optional[str]
    country: Optional[str]
    status: TeamStatus
    founded_date: Optional[date]
    disbanded_date: Optional[date]
    logo_url: Optional[str]
    website_url: Optional[str]
    socials_url: Optional[str]