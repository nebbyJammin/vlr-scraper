from dataclasses import asdict, dataclass
from typing import List, Optional
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
    series_id: int
    region: Optional[str]
    location_long: Optional[str]
    tags: List[str]
    prize: str
    date_str: Optional[str]
    date_start: Optional[date]
    date_end: Optional[date]
    thumbnail: Optional[str]

@dataclass
class VLRMatch(BaseEntry):
    vlr_id: int
    event_id: int
    stage: str
    tournament_round: str
    tournament_note: Optional[str]
    status: CompletionStatus
    date_start: Optional[datetime]
    # team_n_id = None implies a TBD team
    team_1_id: Optional[int]
    team_2_id: Optional[int]
    # score_n = None implies the game hasn't started yet
    score_1: Optional[int]
    score_2: Optional[int]

@dataclass
class VLRTeam(BaseEntry):
    vlr_id: int
    name: str
    tricode: Optional[str]
    country_short: Optional[str]
    country_long: Optional[str]
    status: TeamStatus
    logo: str
    socials: List[str]