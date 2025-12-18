from dataclasses import asdict, dataclass, field
import json 
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
class ScrapableEntry:
    """
    The base class for all scrapable entities. Has members to help serialisation and database insertion.
    """
    date_scraped: Optional[datetime] = field(default=None, kw_only=True) # Can omit if we are using this dataclass outside of a web scraping context.

    def _serializer(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, (CompletionStatus, TeamStatus)):
            return o.value
        return str(o)
    
    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self), default=self._serializer)

@dataclass
class VLRSeries(ScrapableEntry):
    vlr_id: int
    name: str
    description: Optional[str]
    status: CompletionStatus

@dataclass
class VLREvent(ScrapableEntry):
    vlr_id: int
    name: str
    status: CompletionStatus
    series_id: Optional[str]
    region: Optional[str]
    location_long: Optional[str]
    tags: List[str]
    prize: str
    date_str: Optional[str]
    date_start: Optional[date]
    date_end: Optional[date]
    thumbnail: Optional[str]

@dataclass
class VLRMatch(ScrapableEntry):
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
    vods: Optional[List[str]]
    streams: Optional[List[str]]

@dataclass
class VLRTeam(ScrapableEntry):
    vlr_id: int
    name: str
    tricode: Optional[str]
    country_short: Optional[str]
    country_long: Optional[str]
    status: TeamStatus
    logo: str
    socials: List[str]

VLRResult = VLRSeries | VLREvent | VLRMatch | VLRTeam
