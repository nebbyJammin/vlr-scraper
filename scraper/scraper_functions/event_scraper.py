from datetime import date, datetime
import re
from typing import List

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from logging_config import VLR_LOGGER as LOGGER
from scraper.entities import CompletionStatus, TeamStatus
from scraper.scraper_utils import VLRScraperMode, get_id_from_url, soup_cast

# region Helpers
def month_str_to_int(month_str: str) -> int | None:
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
    
def day_str_to_int(day_str: str) -> int | None:
    # Filter out years
    if len(day_str) > 2:
        return None

    try:
        result = int(day_str)
        return result
    except(ValueError, TypeError):
        return None
                
def year_str_to_int(year_str: str) -> int | None:
    try:
        result = int(year_str)
        return result
    except(ValueError, TypeError):
        return None

def try_unpack_date_str(date_str: str) -> tuple[date | None, date | None]:
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
        month_int = month_str_to_int(date_part)

        if month_int:
            month_ints.append(month_int)
            continue

        day_int = day_str_to_int(date_part)

        if day_int:
            day_ints.append(day_int)
            continue
            
        # Has to be year if not a month or day
        year_int = year_str_to_int(date_part)

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

# endregion

@soup_cast
def scrape_event_name(root: Tag | BeautifulSoup | str, event_id: int | None) -> str | None:
    event_title_tag: Tag = root.find("h1", class_="wf-title")
    if not event_title_tag:
        LOGGER.error(f"Could not find event title tag for event with event id '{event_id}'", exc_info=True)
        return None
        
    event_title: str = event_title_tag.text.strip()
    return event_title

@soup_cast
def scrape_event_region(root: Tag | BeautifulSoup | str, event_id: int | None) -> tuple[str | None, str | None]:
        region_code: str | None = None
        region_long_name: str | None = None

        region_tag = root.find("i", class_="flag")

        if region_tag:
            region_tag_class_list: list[str] = region_tag.get("class")

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
            region_long_name = None

        return region_code, region_long_name

@soup_cast
def scrape_event_tag(root: Tag | BeautifulSoup | str, event_id: int | None) -> list[str]:
    tags: list[str] = list()
    tags_container_parent_tag = root.find("div", class_="event-desc-inner")

    if tags_container_parent_tag:
        tags_container_tag: Tag = tags_container_parent_tag.findChild("div")
        if tags_container_tag:
            a_tags: List[Tag] = tags_container_tag.findAll("a")
            for a_tag in a_tags:
                tags.append(a_tag.text)
    
    return tags

@soup_cast
def scrape_event_prize(root: Tag | BeautifulSoup | str, event_id: int | None) -> str | None:
    prize: str | None = None

    prize_pattern = re.compile(r"prize", re.IGNORECASE)
    prize_label_tag = root.find("div", class_="event-desc-item-label", text=prize_pattern)

    if prize_label_tag:
        prize_tag: Tag = prize_label_tag.findNextSibling("div") # type: ignore
        if prize_tag:
            prize_str = prize_tag.text.strip()
            # Prize + Dates are very weirdly formatted with whitespace for some reason
            whitespace_collapse_regex = r"\s+" # get all whitespace runs
            prize = re.sub(whitespace_collapse_regex, " ", prize_str).strip()
    
    if prize == "":
        prize = None
    
    return prize

@soup_cast
def scrape_event_date(root: Tag | BeautifulSoup | str, event_id: int | None) -> tuple[str | None, date | None, date | None]:
    date_str: str | None = None
    date_start: date | None = None
    date_end: date | None = None

    date_pattern = re.compile(r"dates", re.IGNORECASE)
    date_label_tag = root.find("div", class_="event-desc-item-label", text=date_pattern)

    if isinstance(date_label_tag, Tag):
        date_tag: Tag = date_label_tag.findNextSibling("div") # type: ignore
        if date_tag:
            date_str = date_tag.text.strip()
            # Prize + Dates are very weirdly formatted with whitespace for some reason
            whitespace_collapse_regex = r"\s+" # get all whitespace runs
            date_str = re.sub(whitespace_collapse_regex, " ", date_str).strip()

    if date_str:
        date_start, date_end = try_unpack_date_str(date_str)

    return date_str, date_start, date_end

@soup_cast
def scrape_event_thumbnail(root: Tag | BeautifulSoup | str, event_id: int | None) -> str | None:
    thumbnail: str | None = None
    thumbnail_container = root.select_one("div.wf-avatar.event-header-thumb")

    if thumbnail_container:
        thumbnail_tag = thumbnail_container.find("img")

        if thumbnail_tag:
            thumbnail = thumbnail_tag.get("src", None)

    return thumbnail

@soup_cast
def scrape_event_dependent_matches(root: Tag | BeautifulSoup | str, event_id: int | None) -> tuple[CompletionStatus, list[int]]:
    results: List[Tag] = root.select("a.wf-module-item.match-item.mod-color")

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
        elif ml_status == "upcoming" or ml_status == "tbd":
            found_upcoming_event = True
        else:
            LOGGER.error(f"Found unknown ml_status '{ml_status}' while scraping the dependent matches for event_id '{event_id}'", exc_info=True)

        # Match ID from href
        href = result.get("href")
        id = get_id_from_url(VLRScraperMode.MATCH, url=href)

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