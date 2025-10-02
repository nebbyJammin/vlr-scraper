import re
from typing import List

from bs4 import BeautifulSoup, Tag

from logging_config import VLR_LOGGER as LOGGER
from scraper.entities import CompletionStatus, TeamStatus
from scraper.scraper_utils import VLRScraperMode, get_id_from_url, soup_cast


@soup_cast
def scrape_series_name(root: Tag | str, series_id: int | None) -> str | None:
    title_tag = root.find("div", class_="wf-title")
    if title_tag is None:
        LOGGER.error(f"Could not find title tag for team with team id'{series_id}'")
        return None
    
    title = title_tag.text.strip()

    return title

@soup_cast
def scrape_series_description(root: Tag | str, series_id: int | None) -> str | None:
    title_tag = root.find("div", class_="wf-title")
    if title_tag is None:
        return None

    description_tag: Tag | None = title_tag.findNextSibling("div", attrs={ "style": "margin-top: 6px;"})

    if description_tag:
        description = description_tag.text.strip()
    else:
        description = None

    return description

@soup_cast  
def scrape_series_status(root: Tag | str, series_id: int | None) -> CompletionStatus:
    pattern = re.compile(r"upcoming", re.IGNORECASE)
    # upcoming_events_col = root.find("div", class_="wf-label mod-large mod-upcoming")
    upcoming_events_col = root.select_one("div.wf-label.mod-large.mod-upcoming")

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
            top_event_status_tag = next_upcoming_event.find("span", class_="event-item-desc-item-status")

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
    
    return series_status

@soup_cast
def scrape_series_dependent_events(root: Tag | str, series_id: int | None) -> List[int]:
    # events: List[Tag] = soup.findAll("a", class_="wf-card mod-flex event-item")
    events: List[Tag] = root.select("a.wf-card.mod-flex.event-item")
    event_ids: List[int] = list()

    for event in events:
        event_id = get_id_from_url(VLRScraperMode.EVENT, event.get('href'))

        if event_id:
            event_ids.append(event_id)
    
    return event_ids