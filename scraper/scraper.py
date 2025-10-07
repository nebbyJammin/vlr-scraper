import time
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

from scraper.entities import CompletionStatus, VLREvent, VLRMatch, VLRSeries, VLRTeam
from scraper.scraper_functions.event_scraper import scrape_event_date, scrape_event_dependent_matches, scrape_event_name, scrape_event_prize, scrape_event_region, scrape_event_tag, scrape_event_thumbnail
from scraper.scraper_functions.match_scraper import infer_event_from_match, scrape_match_date, scrape_match_dependent_teams, scrape_match_name, scrape_match_note, scrape_match_status
from scraper.scraper_functions.series_scraper import scrape_series_dependent_events, scrape_series_description, scrape_series_name, scrape_series_status
from scraper.scraper_functions.team_scraper import scrape_team_logo, scrape_team_name, scrape_team_region, scrape_team_socials, scrape_team_status
from scraper.scraper_utils import BASE_URL, SCRAPER_MODE_TO_URL_ENDPOINT, VLRScraperMode, VLRScraperOptions, get_id_from_url, get_vlr_url

class VLRScraper: 
    """
    The scraper class that has the methods to scrape each entity from the vlr.gg website. Is thread safe.
    """

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

        NUM_ATTEMPTS = 5
        for attempt in range(NUM_ATTEMPTS):
            try:
                response = requests.get(url, timeout=self.timeout, params=headers)

                if response.status_code == 404:
                    LOGGER.warning(f"No page found for {url}: {e}", exc_info=True)
                    return None

                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                if attempt == NUM_ATTEMPTS - 1:
                    LOGGER.error(f"Failed to fetch {url}: {e}", exc_info=True)
                    return None
            except Exception as e:
                if attempt == NUM_ATTEMPTS - 1:
                    LOGGER.error(f"Unknown exception occurred at {url}: {e}", exc_info=True)
                
    def scrape_series(self, series_id: int) -> tuple[VLRSeries | None, List[int] | None]:
        """
        Scrapes a series with id `series_id`. 
        Returns `None, None` if no event could be found with id `series_id` or if other HTTP Exception occurred.
        Returns a `VLRSeries` then a `List[int]` representing its child event ids. Use the child event ids if you need to scrape the child events recursively.
        """

        if not isinstance(series_id, int):
            LOGGER.error(f"Invalid series ID entered: '{series_id}'")
            return None, None

        url = get_vlr_url(f"series/{series_id}")
        LOGGER.info(f"Scraping series with url '{url}'")
        html = self._fetch_page(url)

        # Check if HTML was retrieved successfully
        if html is None:
            return None, None
        # Parse HTML
        soup = BeautifulSoup(html, features="lxml")

        # Scrape Title
        title: str | None = scrape_series_name(soup, series_id)
        if title is None:
            LOGGER.error(f"Could not find title_tag at url '{url}'")
            return None, None

        # Scrape Description
        description: str | None = scrape_series_description(soup, series_id)
        # Scrape Status
        series_status: CompletionStatus = scrape_series_status(soup, series_id)
        # Get list of events categorised under this series
        event_ids = scrape_series_dependent_events(soup, series_id)

        return VLRSeries(
            vlr_id=series_id,
            name=title,
            description=description,
            status=series_status,
            date_scraped=datetime.now(timezone.utc),
        ),\
        event_ids

    def scrape_event(self, event_id: int, series_id: int | None) -> tuple[VLREvent | None, list[int] | None]:
        """
        Scrapes an event with id `event_id` and optional parent series `series_id`. 
        Returns `None, None` if no event could be found with id `event_id` or if other HTTP Exception occurred.
        Returns a `VLREvent` then a `List[int]` representing its child match ids. Use the child match ids if you need to scrape the child matches recursively.

        `series_id` parameter is optional since not all events belong to a league/series. However, if it is well known that an event belongs to a parent series, never call this function to scrape that event with `None` `series_id`
        """

        if not isinstance(event_id, int):
            LOGGER.error(f"Invalid event ID entered: '{event_id}'")
            return None, None
        # Series ID is not always required to return a structurally complete VLREvent object, but 99% of events have an associated series. Edge case includes some off season events that are one-off.

        url = get_vlr_url(f"event/{event_id}/")
        LOGGER.info(f"Scraping event with url: '{url}'")
        html = self._fetch_page(url)

        # Check if HTML was retrieved successfully
        if html is None:
            return None, None
        # Parse HTML
        soup = BeautifulSoup(html, features="lxml")
        event_card = soup.find("div", class_="event-header")

        if not event_card:
            LOGGER.error(f"Could not find the event header for event with event id '{event_id}'")
            return None

        # Scrape event name
        event_title: str = scrape_event_name(event_card, event_id)
        if not event_title:
            LOGGER.error(f"Could not find event title for event with url '{url}'")
            return None, None

        # Scrape region/location
        region_code, region_long_name = scrape_event_region(event_card, event_id)
        # Scrape tags
        tags = scrape_event_tag(event_card, event_id)
        # Scrape prize
        prize: str | None = scrape_event_prize(event_card, event_id)
        # Scrape date
        date_str, date_start, date_end = scrape_event_date(event_card, event_id) 
        # Scrape thumbnail
        thumbnail = scrape_event_thumbnail(event_card, event_id)
        # Scrape completion status + dependent events
        completion_status, dependent_matches = self.scrape_dependent_matches(event_id)

        return VLREvent(
            vlr_id=event_id,
            name=event_title,
            status=completion_status,
            series_id=series_id,
            region=region_code,
            location_long=region_long_name,
            tags=tags,
            prize=prize,
            date_str=date_str,
            date_start=date_start,
            date_end=date_end,
            thumbnail=thumbnail,
            date_scraped=datetime.now(timezone.utc),
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
        url = get_vlr_url(f"event/matches/{event_id}/")
        params = {
            "series_id": "all", # Query all matches under all stages
            "group": "all", # Query all matches under any completion status
        }
        LOGGER.info(f"Scraping dependent matches of event '{event_id}' with url '{url}' and params '{params}'")

        html = self._fetch_page(url=url, params=params)

        if html is None:
            return None, None
        
        soup = BeautifulSoup(html, features="lxml")

        return scrape_event_dependent_matches(soup, event_id) 
                
    def scrape_match(self, match_id: int, event_id: int | None = None) -> VLRMatch | None:
        """
        Scrapes a match with id `match_id` and optional event_id `event_id`.
        Returns `None` if no match could be found with id `match_id` or if other HTTP Exception occurred.
        Returns a `VLRMatch`.

        `event_id` parameter is optional, however, it should always be called with a parent `event_id`.
        All matches MUST belong under an `event_id`, but the scraper will try to infer the parent `event_id` if it is for some reason not known.
        """

        should_infer_event_id: bool = False
        if event_id is None:
            should_infer_event_id = True
        elif not isinstance(event_id, int):
            LOGGER.error(f"Invalid event id '{event_id}' entered")
            return None

        if not isinstance(match_id, int):
            LOGGER.error(f"Invalid match id '{match_id}' entered")
            return None

        url = get_vlr_url(f"/{match_id}/")
        html = self._fetch_page(url)

        if not html:
            return None
        
        soup = BeautifulSoup(html, features="lxml")
        match_card = soup.select_one("div.wf-card.match-header")

        if not match_card:
            LOGGER.error(f"Couldn't find match wf-card for match id '{match_id}'")
            return None
        
        # Get event_id if there is no event id argument passed
        if should_infer_event_id:
            event_id = infer_event_from_match(match_card, match_id)
            if not event_id:
                LOGGER.error(f"Couldn't infer event id from match id '{match_id}' which did not have a known event id")
                return None
        
        # Get Stage + Tournament Round name
        stage_name, tournament_round_name = scrape_match_name(match_card, match_id)
        # Get match status + match_score
        match_status, score_1, score_2 = scrape_match_status(match_card, match_id)
        if match_status is None:
            LOGGER.error(f"Failed to parse match status for match with url '{url}'")
            return None
        # Get match note
        tournament_note = scrape_match_note(match_card, match_id)
        # Get date_start
        date_start = scrape_match_date(match_card, match_id)
        # Get team
        team_1_id, team_2_id = scrape_match_dependent_teams(match_card, match_id)

        return VLRMatch(
            vlr_id=match_id,
            event_id=event_id,
            stage=stage_name,
            tournament_round=tournament_round_name,
            tournament_note=tournament_note,
            status=match_status,
            date_start=date_start,
            team_1_id=team_1_id,
            team_2_id=team_2_id,
            score_1=score_1,
            score_2=score_2,
            date_scraped=datetime.now(timezone.utc),
        )

    def scrape_team(self, team_id: int) -> VLRTeam | None:
        """
        Scrapes a team with id `team_id`.
        Returns `None` if no team could be found with id `team_id` or if other HTTP Exception occurred.
        Returns a `VLRMatch` if successful.
        """
        url = get_vlr_url(f"/team/{team_id}/")
        response = self._fetch_page(url=url)
        if not response:
            LOGGER.error(f"Error scraping VLRTeam for team with team id '{team_id}'")
            return None

        soup = BeautifulSoup(response, "lxml")

        team_card = soup.find("div", class_="team-header")
        
        # Name + Tricode
        name, tricode = scrape_team_name(team_card, team_id)
        if name == None:
            LOGGER.error(f"Failed to scrape team for team with team id '{team_id}'")
            return None

        # Region
        region, region_long = scrape_team_region(team_card, team_id)
        # Status
        status = scrape_team_status(team_card, team_id)
        # Logo
        logo = scrape_team_logo(team_card, team_id)
        # Socials
        socials = scrape_team_socials(team_card, team_id)

        return VLRTeam(
            vlr_id=team_id,
            name=name,
            tricode=tricode,
            country_short=region,
            country_long=region_long,
            status=status,
            logo=logo,
            socials=socials,
            date_scraped=datetime.now(timezone.utc),
        )

    def discover_series(self, already_seen_series: List[int], series_max: int | None) -> List[int]:
        """
        Takes a list of already seen series ids `already_seen_series` and an upper bound (inclusive) for the search space `series_max`.
        Will keep searching up for series ids until `series_max` if defined, OR until 10 invalid series ids in a row.
        vlr.gg will have some 'skipped' series ids. This function searches for not yet seen series by fetching the pages of each series and seeing if we get 200 status code (400 status code returned for page not found).

        Returns a list of new series_ids
        """
        probed_series : List[int] = []

        consecutive_failures = 0
        MAXIMUM_CONSECUTIVE_FAILURES = 10
        ATTEMPTS = 10
        curr_series_id = 1

        # Continue until we consecutively fail 10 times AND are below series_max
        while consecutive_failures < MAXIMUM_CONSECUTIVE_FAILURES \
            and (not series_max or curr_series_id <= series_max):

            if curr_series_id not in already_seen_series:
                url = urljoin(BASE_URL, f"series/{curr_series_id}")
                LOGGER.info("Probing %s", url)
                for attempt in range(ATTEMPTS):
                    try:
                        response = requests.get(url, timeout=self.timeout, headers={
                            "User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/117.0.0.0 Safari/537.36"
                            )
                        })

                        if response and response.ok:
                            consecutive_failures = 0
                            probed_series.append(curr_series_id)
                            break
                        else:
                            consecutive_failures += 1
                            LOGGER.info("Failed by bad status")
                            break
                    except Exception as e:
                        if attempt == ATTEMPTS - 1:
                            LOGGER.info("Failed by no response")
                            consecutive_failures += 1 
            else:
                LOGGER.info("Already seen series id %s and will skip.", curr_series_id)
                consecutive_failures = 0
            
            curr_series_id += 1
        
        return probed_series

    def discover_front_page_event_ids(self) -> List[int]:
        """
        Searches the front page of the events tab. This is important to search for events that do not belong under any leagues/series.

        Returns a list of all the event ids on the front page.
        """
        front_page_events: List[int] = []

        url = urljoin(BASE_URL, f"/events")
        response = self._fetch_page(url, {
            "tier": "all"
        })

        soup = BeautifulSoup(response, features="lxml")
        events_container = soup.find("div", class_="events-container")

        a_events: List[Tag] = events_container.findAll("a", class_=["wf-card", "event-item"])

        for a_event in a_events:
            href = a_event.get("href")
            success = True

            if not href:
                success = False
            else:
                event_id = get_id_from_url(VLRScraperMode.EVENT, href)

                if not event_id:
                    success = False
                else:
                    front_page_events.append(event_id)

            if not success:
                LOGGER.warning("Potentially missed an event -> Couldn't find the id from event a tag.")
        
        return front_page_events