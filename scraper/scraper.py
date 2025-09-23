from typing import List
from urllib.parse import quote, urljoin
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from dataclasses import dataclass
from logging_config import VLR_LOGGER as LOGGER
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import requests
import re

from scraper.entities import CompletionStatus, VLREvent, VLRMatch, VLRSeries

@dataclass
class VLRScraperOptions:
    timeout: int = 10
    local_tz: str = "UTC"
    vlr_utc_offset: timedelta = timedelta(hours=4)

class VLRScraperMode(Enum):
    SERIES=0
    EVENT=1
    MATCH=2
    TEAM=3
    EVENT_MATCHES=10

class VLRScraper:
    BASE_URL = "https://vlr.gg/"
    SCRAPER_MODE_TO_URL_ENDPOINT = {
        VLRScraperMode.SERIES: "series",
        VLRScraperMode.EVENT: "event",
        VLRScraperMode.EVENT_MATCHES: "matches",
        VLRScraperMode.MATCH: "",
        VLRScraperMode.TEAM: "team",
    }
    
    def __init__(self, options: VLRScraperOptions | None = None):
        if options is None:
            options = VLRScraperOptions()

        self.timeout = options.timeout
        self.local_tz = options.local_tz
        self.vlr_utc_offset = options.vlr_utc_offset

        LOGGER.info("Scraper has been successfully created!")
        pass

    def _fetch_page(self, url: str, params: dict[str, str] = {}) -> str | None:
        """Fetch HTML content. Return None if request fails"""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/117.0.0.0 Safari/537.36"
            )
        }

        headers |= params

        try:
            response = requests.get(url, timeout=self.timeout, params=headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Failed to fetch {url}: {e}")
            return None

    @staticmethod
    def _get_id_from_url(mode: VLRScraperMode, url: str) -> int | None:
        if not isinstance(mode, VLRScraperMode):
            LOGGER.error(f"Invalid scraper mode entered. Mode was of type '{mode.__class__}'")
        if not isinstance(url, str):
            LOGGER.error(f"Invalid url entered. URL was of type '{mode.__class__}'")
        
        url = url.strip()

        paths: list[str] = url.split('/')
        
        id: int | None = None
        id_as_string: str
        if mode == VLRScraperMode.MATCH:
            # Matches do not have a special URL path prefix
            for i, path in enumerate(paths):
                if len(path) == 0:
                    if i < len(paths) - 1:
                        id_as_string = paths[i + 1]
                    else:
                        LOGGER.error(f"No ID could be extracted from URL '{url}'")
                        return None
                else:
                    # Try to just cast current path as a number
                    id_as_string = path

                try:
                    id = int(id_as_string)
                    break
                except ValueError:
                    continue
        else:
            scraper_prefix: str = VLRScraper.SCRAPER_MODE_TO_URL_ENDPOINT.get(mode, "")

            prefix_idx = paths.index(scraper_prefix)
            if prefix_idx < len(paths) - 1:
                id_as_string = paths[prefix_idx + 1]
                try:
                    id = int(id_as_string)
                except ValueError:
                    LOGGER.error(f"Got invalid ID from {mode}")
                    return None
            else:
                LOGGER.error(f"No ID could be extracted from URL {url}")
                return None


        return id
                
    @staticmethod
    def _month_str_to_int(month_str: str) -> int | None:
        """
        Convert a 3-letter month abbreviation to an integer (1-12).

        Returns:
            int: month number if valid
            None: if invalid input
        """

        try:
            return datetime.strptime(month_str[:3], "%b").month
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _day_str_to_int(day_str: str) -> int | None:
        # Filter out years
        if len(day_str) > 2:
            return None

        try:
            result = int(day_str)
            return result
        except(ValueError, TypeError):
            return None
                
    @staticmethod
    def _year_str_to_int(year_str: str) -> int | None:
        try:
            result = int(year_str)
            return result
        except(ValueError, TypeError):
            return None

    @staticmethod
    def _try_unpack_date_str(date_str: str) -> tuple[date | None, date | None]:

        # date_str can be in many different forms
        # MONTH DAY, YEAR - MONTH DAY, YEAR
        # MONTH DAY - MONTH DAY, YEAR
        # MONTH DAY - MONTH DAY

        # MONTH DAY - DAY
        # MONTH DAY - DAY, YEAR

        # Assumptions
        # 1) At least 1 month will be stated
        # 2) At Least 1 year will be stated
        # 3) MONTH will be listed as 3 letter abbreviation always
        
        month_ints: list[int] = list()
        day_ints: list[int] = list()
        year_ints: list[int] = list()

        split_regex = r"[\s,\-]+"
        date_parts: list[str] = re.split(split_regex, date_str)

        for date_part in date_parts:
            month_int = VLRScraper._month_str_to_int(date_part)

            if month_int:
                month_ints.append(month_int)
                continue

            day_int = VLRScraper._day_str_to_int(date_part)

            if day_int:
                day_ints.append(day_int)
                continue
            
            # Has to be year if not a month or day
            year_int = VLRScraper._year_str_to_int(date_part)

            if year_int:
                year_ints.append(year_int)
                continue

        if len(month_ints) > 0 \
            and len(day_ints) > 0 \
                and len(year_ints) > 0:
                    try:
                        first_date = date(year_ints[0], month_ints[0], day_ints[0])
                        second_date = date(year_ints[-1], month_ints[-1], day_ints[-1])

                        return first_date, second_date
                    except(ValueError):
                        return None, None
        
        return None, None

    def scrape_series(self, series_id: int) -> tuple[VLRSeries | None, list[int] | None]:
        if not isinstance(series_id, int):
            LOGGER.error(f"Invalid series ID entered: '{series_id}'")
            return None, None

        url = urljoin(VLRScraper.BASE_URL, f"series/{series_id}")
        LOGGER.info(f"Scraping series with url '{url}'")
        html = self._fetch_page(url)

        # Check if HTML was retrieved successfully
        if html is None:
            return None, None

        # Parse HTML
        soup = BeautifulSoup(html, features="lxml")

        # Scrape Title
        title_tag = soup.find("div", class_="wf-title")
        title: str

        if title_tag is None:
            LOGGER.error(f"Could not find title_tag at url '{url}'")
            return None, None
        else:
            title = title_tag.text.strip()

        # Scrape Description
        description_tag: Tag | None = title_tag.findNextSibling("div", attrs={ "style": "margin-top: 6px;"}) # type: ignore
        description: str | None = None

        if description_tag:
            description = description_tag.text.strip()

        # Scrape Status
        series_status: CompletionStatus
        
        pattern = re.compile(r"upcoming", re.IGNORECASE)
        upcoming_events_col = soup.find("div", class_="wf-label mod-large mod-upcoming")

        if not isinstance(upcoming_events_col, Tag):
            # No upcoming events just assume the event is complete
            series_status = CompletionStatus.COMPLETED
        else:
            next_upcoming_event = upcoming_events_col.find_next_sibling()

            if not isinstance(next_upcoming_event, Tag):
                # No upcoming events just assume the event is complete
                series_status = CompletionStatus.COMPLETED
            else:
                # Check the event status of the top event
                top_event_status_tag = next_upcoming_event.find("span", class_="event-item-desc-item-status", text=pattern)

                if top_event_status_tag is None:
                    series_status = CompletionStatus.COMPLETED
                else:
                    top_event_status = top_event_status_tag.text.strip().lower()

                    if top_event_status == "ongoing":
                        series_status = CompletionStatus.ONGOING
                    elif top_event_status == "upcoming":
                        series_status = CompletionStatus.UPCOMING
                    else:
                        series_status = CompletionStatus.COMPLETED


        # Get list of events categorised under this series
        events: List[Tag] = soup.findAll("a", class_="wf-card mod-flex event-item") # type: ignore
        event_ids: List[int] = list()

        for event in events:
            event_id = VLRScraper._get_id_from_url(VLRScraperMode.EVENT, event.get('href')) # type: ignore

            if event_id:
                event_ids.append(event_id)

        return VLRSeries(
            vlr_id=series_id,
            name=title,
            description=description,
            status=series_status
        ),\
        event_ids

    def scrape_event(self, event_id: int, series_id: int) -> tuple[VLREvent | None, list[int] | None]:
        if not isinstance(event_id, int):
            LOGGER.error(f"Invalid event ID entered: '{event_id}'")
            return None, None
        # Series ID is required to return a structurally complete VLREvent object
        if not isinstance(series_id, int):
            LOGGER.error(f"Invalid series ID given: '{series_id}'")
            return None, None

        url = urljoin(VLRScraper.BASE_URL, f"event/{event_id}")
        LOGGER.info(f"Scraping event with url: '{url}'")
        html = self._fetch_page(url)

        # Check if HTML was retrieved successfully
        if html is None:
            return None, None

        # Parse HTML
        soup = BeautifulSoup(html, features="lxml")

        # Get basic event details
        # Event Name
        # Region (Short)
        # Location (Long)
        # tags
        # prize
        # datestart
        # dateend
        # thumbnail


        # Event Status -> Not basic 
        # Series ID -> Passed in as arg

        # Scrape event name
        event_title_tag: Tag = soup.find("h1", class_="wf-title") # type: ignore
        if not event_title_tag:
            LOGGER.error(f"Could not find event title tag on event page with url {url}")
            return None, None
        
        event_title: str = event_title_tag.text.strip()
        region_code: str | None = None
        region_long_name: str | None = None

        # Scrape region/location
        region_tag = soup.find("i", class_="flag")

        if region_tag:
            region_tag_class_list: list[str] = region_tag.get("class") # type: ignore

            for class_name in region_tag_class_list:
                trimmed_name = class_name.strip()
                if trimmed_name.startswith('mod'):
                    # Regions will have classname mod-us for example
                    region_code = trimmed_name[4:] # mod- is 4 characters

                    # Now try to get the location long name
                    region_long_tag: NavigableString | None = region_tag.nextSibling # Get the next text
                    if region_long_tag:
                        region_long_name = region_long_tag.text.strip()
                    break

        if region_code == '':
            region_code = None
        if region_long_name == '':
            region_code = None

        # Scrape tags
        tags: list[str] = list()
        tags_container_parent_tag = soup.find("div", class_="event-desc-inner")

        if tags_container_parent_tag:
            tags_container_tag: Tag = tags_container_parent_tag.findChild("div")

            if tags_container_tag:
                a_tags: List[Tag] = tags_container_tag.findAll("a")

                for a_tag in a_tags:
                    tags.append(a_tag.text)

        # Scrape prize
        prize: str | None = ""

        prize_pattern = re.compile(r"prize", re.IGNORECASE)
        prize_label_tag = soup.find("div", class_="event-desc-item-label", text=prize_pattern)

        if prize_label_tag:
            prize_tag: Tag = prize_label_tag.findNextSibling("div") # type: ignore
            if prize_tag:
                prize_str = prize_tag.text.strip()
                # Prize + Dates are very weirdly formatted with whitespace for some reason
                whitespace_collapse_regex = r"\s+" # get all whitespace runs
                prize = re.sub(whitespace_collapse_regex, " ", prize_str).strip()

        # Scrape date
        date_str: str | None = None
        date_start: date | None = None
        date_end: date | None = None

        date_pattern = re.compile(r"dates", re.IGNORECASE)
        date_label_tag = soup.find("div", class_="event-desc-item-label", text=date_pattern)

        if isinstance(date_label_tag, Tag):
            date_tag: Tag = date_label_tag.findNextSibling("div") # type: ignore
            if date_tag:
                date_str = date_tag.text.strip()
                # Prize + Dates are very weirdly formatted with whitespace for some reason
                whitespace_collapse_regex = r"\s+" # get all whitespace runs
                date_str = re.sub(whitespace_collapse_regex, " ", date_str).strip()

        if date_str:
            date_start, date_end = VLRScraper._try_unpack_date_str(date_str)
        
        # Scrape thumbnail
        # TODO: Implement
        thumbnail: str | None = None

        # thumbnail_container = soup.find("div", class_=["wf-avatar", "event-header-thumb"])
        thumbnail_container = soup.select("div.wf-avatar.event-header-thumb")

        if isinstance(thumbnail_container, Tag):
            thumbnail_tag = thumbnail_container.find("img")

            if thumbnail_tag:
                thumbnail = thumbnail_tag.get("src", None)
        # Scrape completion status + dependent events
        completion_status, dependent_matches = self.scrape_dependent_matches(event_id)

        return VLREvent(
            vlr_id=event_id,
            name=event_title,
            status=completion_status, # TODO NEED TO IMPLEMENT STATUS
            series_id=series_id, # TODO What if series id is unknown? is that okay
            region=region_code,
            location_long=region_long_name,
            tags=tags,
            prize=prize,
            date_str=date_str,
            date_start=date_start,
            date_end=date_end,
            thumbnail=thumbnail
        ),\
        dependent_matches

    def scrape_dependent_matches(self, event_id: int) -> tuple[CompletionStatus, list[int]]:
        """
        Gets the completion status of an event (by looking at the status of its dependent matches) and returns a list of match ids that correspond to matches belonging to event with event id `event_id`

        Returns
            `CompletionStatus`, `List[event_id]` - when the completion status can be inferred.  
            None, None - if the completion status can be inferred OR when an invalid event_id is entered.
        """
        if not isinstance(event_id, int):
            LOGGER.error(f"Invalid event ID entered: '{event_id}'")
            return None, None

        # Matches are listed on the vlr.gg/event/matches/${event_id}/ endpoint
        url = urljoin(VLRScraper.BASE_URL, f"event/matches/{event_id}/")
        params = {
            "series_id": "all", # Query all matches under all stages
            "group": "all", # Query all matches under any completion status
        }
        LOGGER.info(f"Scraping dependent matches of event '{event_id}' with url '{url}' and params '{params}'")

        html = self._fetch_page(url=url, params=params)

        if html is None:
            return None, None
        
        soup = BeautifulSoup(html, features="lxml")

        # results: List[Tag] = soup.findAll("a", class_=["wf-module-item", "match-item", "mod-color"])
        results: List[Tag] = soup.select("a.wf-module-item.match-item.mod-color")

        event_completion_status = CompletionStatus.UNKNOWN
        found_completed_event: bool = False
        found_live_event: bool = False
        found_upcoming_event: bool = False

        dependent_match_list: list[int] = []

        # Loop through each match-item. Get completion status + match id from href
        for result in results:
            # Completion Status

            # Every match-item should have a div with class name "ml-status"
            ml_status_tag: Tag = result.find("div", class_="ml-status")

            if not ml_status_tag:
                continue

            # Parse the text content
            ml_status = ml_status_tag.text.strip().lower()

            if ml_status == "completed":
                found_completed_event = True
            elif ml_status == "live" or ml_status == "ongoing":
                found_live_event = True
            elif ml_status == "upcoming":
                found_upcoming_event = True
            else:
                LOGGER.error(f"Found unknown ml_status '{ml_status}' while scraping the dependent matches for event_id '{event_id}'")

            # Match ID from href
            href = result.get("href")
            id = VLRScraper._get_id_from_url(VLRScraperMode.MATCH, url=href)

            if id:
                dependent_match_list.append(id)
        
        # Infer completion status of the event from its matches
        # Case 1: Event is complete -> All match events are complete
        if found_completed_event and not found_live_event and not found_upcoming_event:
            # True, False, False
            event_completion_status = CompletionStatus.COMPLETED
        # Case 2: Event is ongoing -> Found at least one match complete or live
        elif (found_completed_event and found_upcoming_event) or found_live_event:
            # True False True OR * True *
            event_completion_status = CompletionStatus.ONGOING
        # Case 3: Event is upcoming -> No completed nor live events
        elif found_upcoming_event:
            # * * True
            CompletionStatus.UPCOMING
        else:
            # Somehow no completed, live or completed events were found -> probably no matches listed under this event
            CompletionStatus.UNKNOWN

        return event_completion_status, dependent_match_list
                
                
    def scrape_match(self, match_id: int, event_id: int) -> tuple[VLRMatch, list[int]]:
        if not isinstance(event_id, int):
            LOGGER.error(f"Invalid event id '{event_id}' entered")
            return None, None
        if not isinstance(match_id, int):
            LOGGER.error(f"Invalid match id '{match_id}' entered")
            return None, None

        url = urljoin(VLRScraper.BASE_URL, f"/{match_id}/")
        html = self._fetch_page(url)

        if not html:
            return None, None
        
        soup = BeautifulSoup(html, features="lxml")
        match_card = soup.select_one("div.wf-card.mod-color")

        if not match_card:
            LOGGER.error(f"Couldn't find match wf-card for match id '{match_id}'")
            return None, None
        
        # Get Stage + Tournament Round name

        stage_name: str
        tournament_round_name: str
        stage_round_tag = match_card.find("div", class_="match-header-event-series")

        if not stage_round_tag:
            LOGGER.error(f"Couldn't find stage/round tag for match id '{match_id}'")
            return None, None
        
        stage_round_str = re.sub(r"\s+", " ", stage_round_tag.text).strip()
        stage_round_components = stage_round_str.split(":")

        if len(stage_round_components) == 2:
            stage_name = stage_round_components[0]
            tournament_round_name = stage_round_components[1]
        else: 
            LOGGER.error(f"Unknown number of stage/round components received ({stage_round_components})")
            return None, None
        
        LOGGER.debug(f"Received {stage_name, tournament_round_name}")

        # Get match status + match_score

        match_status: CompletionStatus = CompletionStatus.UNKNOWN
        score_1: int | None = None
        score_2: int | None = None

        # We can determine match_status via the presence/absence of
        #   - div.match-header-vs-placeholder (when the match hasn't happened yet)
        #   - span.match-header-vs-winner and span.match-header-vs-loser (when the match has completed)
        #   - span (span with no classnames when the match is live)

        match_header_container = match_card.find("div", class_="match-header-vs-score")

        if not match_header_container:
            LOGGER.error(f"Could not find the match score container for match id {match_id}")
        else:
            match_placeholder_tag = match_header_container.find("div", class_="match-header-vs-placeholder")

            if match_placeholder_tag:
                match_status = CompletionStatus.UPCOMING
                score_1 = None
                score_2 = None
            else:
                # Completed match will have one score tag with classname match-header-vs-winner
                winner_loser_team_tags = match_header_container.findAll("span", class_=["match-header-vs-score-winner", "match-header-vs-score-loser"])

                if len(winner_loser_team_tags) == 2:
                    match_status = CompletionStatus.COMPLETED

                    score_1_tag, score_2_tag = winner_loser_team_tags
                    
                    score_1_str = score_1_tag.text.strip()
                    score_2_str = score_2_tag.text.strip()
                    
                    # LOGGER.debug([score_1_str, score_2_str])

                    try:
                        score_1 = int(score_1_str)
                        score_2 = int(score_2_str)
                    except Exception as e:
                        LOGGER.error(f"Found scores for game with match id of '{match_id}' but could not parse score as an int (score_1='{score_1_str}', score_2='{score_2_str}')")
                        return None, None
                elif len(winner_loser_team_tags) != 0:
                    LOGGER.error(f"Could not find score of a game that should have a score (match id of '{match_id}').")
                    return None, None
                else:
                    # match_live_tag = match_header_container.find("span", class_=lambda x: x is None) # Ensure we only select span with no class names
                    match_live_tag = next(
                        (
                            t for t in match_header_container.find_all("span") if t.has_attr("class") and not t.get("class")
                        ),
                            None)

                    # Score is represented by span with no classnames
                    if match_live_tag:
                        match_status = CompletionStatus.ONGOING
                    else:
                        LOGGER.error(f"Could not find the match status of match id '{match_id}'")
                        match_status = CompletionStatus.UNKNOWN
        
        # LOGGER.debug(f"Got match status {match_status}")
        
        # Get match note

        tournament_note: str | None = None
        tournament_note_tags = match_card.findAll("div", class_="match-header-vs-note")
        if len(tournament_note_tags) > 0:
            tournament_note_tag = tournament_note_tags[-1]
            tournament_note = re.sub(r"\s+", " ", tournament_note_tag.text).strip()
        
        # Get date_start and date_end

        date_start: datetime | None = None

        # div.moment-tz-card has attribute "data-utc-ts" that gives information about the UTC time of the event
        date_start_tag = match_card.find("div", class_="moment-tz-convert")

        if date_start_tag:
            date_start_str = date_start_tag.get("data-utc-ts") # Will return something like 2025-09-25 09:00:00
            if date_start_str:
                try:
                    VLR_UTC_OFFSET = timedelta(hours=4) # vlr page gives time meta data in UTC-4
                    date_start = datetime.strptime(date_start_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) + VLR_UTC_OFFSET # add 4 hours to properly convert to UTC time
                except Exception as e:
                    LOGGER.error(f"Failed to parse '{date_start_str}' as a datetime object for match id '{match_id}'")

        # LOGGER.debug(f"Got time {date_start}")

        # Get team

        team_1_id: int | None = None
        team_2_id: int | None = None

        match_header_links: list[Tag] = match_card.findAll("a", class_=["match-header-link"])

        if len(match_header_links) > 2:
            LOGGER.error(f"More than 2 match header link tags scraped, and therefore, cannot infer the teams involved for match id '{match_id}'")
            return None, None
        elif len(match_header_links) == 2:
            team_1_tag = match_header_links[0]
            team_2_tag = match_header_links[1]

            team_1_str = team_1_tag.get("href", None)
            team_2_str = team_2_tag.get("href", None)
            # LOGGER.debug(f"{team_1_str, team_2_str}")

            try:
                if team_1_str:
                    team_1_id = VLRScraper._get_id_from_url(VLRScraperMode.MATCH, team_1_str)
            except Exception:
                # LOGGER.debug("failed team 1")
                team_1_id = None
                
            try:
                if team_2_str:
                    team_2_id = VLRScraper._get_id_from_url(VLRScraperMode.MATCH, team_2_str)
            except Exception:
                # LOGGER.debug("failed team 2")
                team_2_id = None
        else:
            LOGGER.error(f"Not enough match header link tags scraped, and therefore, cannot infer the teams involved for match id '{match_id}'")
            return None, None

        # score_1: Optional[int]
        # score_2: Optional[int]

        # return None, None
        return \
            VLRMatch(
                vlr_id=match_id,
                stage=stage_name,
                tournament_round=tournament_round_name,
                tournament_note=tournament_note,
                status=match_status,
                date_start=date_start,
                team_1_id=team_1_id,
                team_2_id=team_2_id,
                score_1=score_1,
                score_2=score_2
                # score_1=score_1,
                # score_2=score_2,
            ), \
            list()

        
        



        
        