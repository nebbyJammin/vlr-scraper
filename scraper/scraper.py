from typing import List
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from dataclasses import dataclass
from logging_config import VLR_LOGGER as LOGGER
from datetime import date
from enum import Enum
import requests
import re

from scraper.entities import CompletionStatus, VLREvent, VLRSeries

@dataclass
class VLRScraperOptions:
    timeout: int = 10

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

        LOGGER.info("Scraper has been successfully created!")
        pass

    def _fetch_page(self, url: str) -> str | None:
        """Fetch HTML content. Return None if request fails"""
        headers = {
            "User-Agent": "nebbys-scraper"
        }

        try:
            response = requests.get(url, headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Failed to fetch {url}: {e}")
            return None

    @staticmethod
    def _get_id_from_url(mode: VLRScraperMode, url: str) -> int | None:
        if not isinstance(mode, VLRScraperMode):
            LOGGER.error(f"Invalid scraper mode entered. Mode was of type {mode.__class__}")
        if not isinstance(url, str):
            LOGGER.error(f"Invalid url entered. URL was of type {mode.__class__}")
        
        url = url.strip()

        paths: list[str] = url.split('/')
        LOGGER.debug(f"Paths found: {paths}")
        
        id: int | None = None
        id_as_string: str
        if mode == VLRScraperMode.MATCH:
            # Matches do not have a special URL path prefix
            for i, path in enumerate(paths):
                if len(path) == 0:
                    if i < len(paths) - 1:
                        id_as_string = paths[i + 1]
                    else:
                        LOGGER.error(f"No ID could be extracted from URL {url}")
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
    def _unpack_date_str(date_str: str) -> tuple[str | None, str | None]:
        return None, None

    def scrape_series(self, series_id: int) -> tuple[VLRSeries | None, list[int] | None]:
        if not isinstance(series_id, int):
            LOGGER.error(f"Invalid series ID entered: {series_id}")
            return None, None

        url = urljoin(VLRScraper.BASE_URL, f"series/{series_id}")
        LOGGER.info(f"Scraping series with url: {url}")
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
            LOGGER.error(f"Could not find title_tag for at {url}")
            return None, None
        else:
            title = title_tag.text.strip()

        LOGGER.debug(f"Got title {title}")

        # Scrape Description
        description_tag: Tag | None = title_tag.findNextSibling("div", attrs={ "style": "margin-top: 6px;"}) # type: ignore
        description: str | None = None

        if description_tag:
            description = description_tag.text.strip()

        # Scrape Status
        series_status: CompletionStatus
        
        pattern = re.compile(r"upcoming", re.IGNORECASE)
        upcoming_events_col = soup.find("div", class_="wf-label mod-large mod-upcoming", text=pattern)

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
                top_event_status_tag = next_upcoming_event.findChildren("span", class_="event-item-desc-item-status") # type: ignore

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
            LOGGER.debug(f"Found EVENT HREF {event.get('href')}")

            event_id = VLRScraper._get_id_from_url(VLRScraperMode.EVENT, event.get('href')) # type: ignore
            LOGGER.debug(f"Found EVENT_ID {event_id}")

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
            LOGGER.error(f"Invalid event ID entered: {event_id}")
            return None, None
        # Series ID is required to return a structurally complete VLREvent object
        if not isinstance(series_id, int):
            LOGGER.error(f"Invalid series ID given: {series_id}")
            return None, None

        url = urljoin(VLRScraper.BASE_URL, f"event/{event_id}")
        LOGGER.info(f"Scraping event with url: {url}")
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

                    LOGGER.debug(f"Got short region code: {region_code}")
                    LOGGER.debug(f"Got long region name: {region_long_name}")
                    break

        if region_code == '':
            region_code = None
        if region_long_name == '':
            region_code = None

        # Scrape tags
        tags: list[str] = list()
        tags_container_parent_tag = soup.find("div", class_="event-desc-inner")

        if tags_container_parent_tag:
            tags_container_tag: Tag = tags_container_parent_tag.findChild("div") # type: ignore

            if tags_container_tag:
                a_tags: List[Tag] = tags_container_tag.findChildren("a") # type: ignore

                for a_tag in a_tags:
                    tags.append(a_tag.text)

        LOGGER.debug(f"Got tags {tags}")

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
                LOGGER.debug(f"Got prize {prize}")

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

                LOGGER.debug(f"Got date_str {date_str}")

        if date_str:
            date_start, date_end = VLRScraper._unpack_date_str(date_str)
        
        # Scrape thumbnail
        thumbnail: str | None = None

        return VLREvent(
            vlr_id=event_id,
            name=event_title,
            status=CompletionStatus.UNKNOWN, # TODO NEED TO IMPLEMENT STATUS
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
        list()
                
    def scrape_match(match_id: int):
        pass


        
        



        
        