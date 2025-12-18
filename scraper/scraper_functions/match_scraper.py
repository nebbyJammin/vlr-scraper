from datetime import date, datetime, timedelta, timezone
import re
from typing import List

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from logging_config import VLR_LOGGER as LOGGER
from scraper.entities import CompletionStatus, TeamStatus
from scraper.scraper_utils import VLRScraperMode, get_id_from_url, soup_cast

@soup_cast
def scrape_match_name(root: Tag | BeautifulSoup | str, match_id: int | None) -> tuple[str | None, str | None]:
    stage_name: str
    tournament_round_name: str
    stage_round_tag = root.find("div", class_="match-header-event-series")

    if not stage_round_tag:
        LOGGER.error(f"Couldn't find stage/round tag for match id '{match_id}'")
        return None, None
        
    stage_round_str = re.sub(r"\s+", " ", stage_round_tag.text).strip()
    stage_round_components = stage_round_str.split(":")

    if len(stage_round_components) == 2:
        stage_name = stage_round_components[0].strip()
        tournament_round_name = stage_round_components[1].strip()
    else:
        if len(stage_round_components) > 2:
            stage_name = stage_round_components[0].strip()
            tournament_round_name = ""
            for i in range(1, len(stage_round_components)):
                tournament_round_name += stage_round_components[i].strip()
            LOGGER.warning(f"Received more than 2 stage/round components for match with match id '{match_id}'. Silently failing and combining the last n - 1 components.")
        else:
            LOGGER.error(f"Unexpected number of stage/round components received ({stage_round_components})")
            return None, None
        
    return stage_name, tournament_round_name

@soup_cast
def scrape_match_status(root: Tag | BeautifulSoup | str, match_id: int | None) -> tuple[CompletionStatus, int | None, int | None]:
    match_status: CompletionStatus = CompletionStatus.UNKNOWN
    score_1: int | None = None
    score_2: int | None = None

    # We can determine match_status via the presence/absence of
    #   - div.match-header-vs-placeholder (when the match hasn't happened yet)
    #   - span.match-header-vs-winner and span.match-header-vs-loser (when the match has completed)
    #   - span (span with no classnames when the match is live)

    match_header_container = root.find("div", class_="match-header-vs-score")

    if not match_header_container:
        LOGGER.error(f"Could not find the match score container for match id {match_id}")
        return CompletionStatus.UNKNOWN, None, None

    match_placeholder_tag = match_header_container.find("div", class_="match-header-vs-placeholder")

    # Matches with unknown score will have a match-header-vs-placeholder
    if match_placeholder_tag:
        match_status = CompletionStatus.UPCOMING
        # Upcoming -> No score
        return match_status, None, None

    # Every game has a note -> either time until match, LIVE or FINAL
    match_header_vs_notes: List[Tag] = match_header_container.findAll("div", class_="match-header-vs-note")

    if len(match_header_vs_notes) >= 1:
        first_header_note = match_header_vs_notes[0]
        first_header_text: str = first_header_note.text.strip().lower()
        # Completed match will always have the FINAL label on it
        if first_header_text == "final" or "forfeit" in first_header_text or "cancel" in first_header_text:
            match_status = CompletionStatus.COMPLETED
        elif first_header_text == "live":
            match_status = CompletionStatus.ONGOING
        else:
            # At this point, it can't be upcoming, so must be unknown
            match_status = CompletionStatus.UNKNOWN

    # Only try scrape score if we know that the match is completed or ongoing
    if match_status == CompletionStatus.COMPLETED or match_status == CompletionStatus.ONGOING:
        js_spoiler = match_header_container.find("div", class_="js-spoiler")
        if not js_spoiler:
            LOGGER.error(f"Failed to find match scores for match id '{match_id}'")
            return match_status, None, None

        score_tags = js_spoiler.findAll("span", attrs=lambda x: x is None or 'match-header-vs-score-colon' not in x.split())
        if len(score_tags) == 2:
            score_1_tag, score_2_tag = score_tags
                    
            score_1_str = score_1_tag.text.strip()
            score_2_str = score_2_tag.text.strip()
                    
            try:
                score_1 = int(score_1_str)
            except Exception as e:
                LOGGER.warning(f"Found scores for game with match id of '{match_id}' but could not parse score_1 as an int (score_1='{score_1_str}')")

            try:
                score_2 = int(score_2_str)
            except Exception as e:
                LOGGER.warning(f"Found scores for game with match id of '{match_id}' but could not parse score_2 as an int (score_2='{score_2_str}')")
        else:
            LOGGER.error(f"Could not find score of a game that should have a score (match id of '{match_id}').")
            return CompletionStatus.UNKNOWN, None, None
    
    return match_status, score_1, score_2

@soup_cast
def scrape_match_note(root: Tag | BeautifulSoup | str, match_id: int | None) -> str | None:
    tournament_note: str | None = None
    tournament_note_tags = root.findAll("div", class_="match-header-vs-note")
    if len(tournament_note_tags) > 0:
        tournament_note_tag = tournament_note_tags[-1]
        tournament_note = re.sub(r"\s+", " ", tournament_note_tag.text).strip()
    
    return tournament_note

@soup_cast
def scrape_match_date(root: Tag | BeautifulSoup | str, match_id: int | None) -> datetime | None:
    date_start: datetime | None = None

    # div.moment-tz-card has attribute "data-utc-ts" that gives information about the UTC time of the event
    date_start_tag = root.find("div", class_="moment-tz-convert")

    if date_start_tag:
        date_start_str = date_start_tag.get("data-utc-ts") # Will return something like 2025-09-25 09:00:00

        if date_start_str:
            if date_start_str == "0000-00-00 00:00:00": # Extremely odd case where the match is complete, but completed at an unknown time -> see match id 528615
                return None

            try:
                VLR_UTC_OFFSET = timedelta(hours=4) # vlr page gives time meta data in UTC-4
                date_start = datetime.strptime(date_start_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) + VLR_UTC_OFFSET # add 4 hours to properly convert to UTC time
            except Exception as e:
                LOGGER.error(f"Failed to parse '{date_start_str}' as a datetime object for match id '{match_id}'", exc_info=True)
                date_start = None
    
    return date_start

@soup_cast
def scrape_match_dependent_teams(root: Tag | BeautifulSoup | str, match_id: int | None) -> tuple[int | None, int | None]:
    team_1_id: int | None = None
    team_2_id: int | None = None

    match_header_links: list[Tag] = root.findAll("a", class_=["match-header-link"])

    if len(match_header_links) > 2:
        LOGGER.error(f"More than 2 match header link tags scraped, and therefore, cannot infer the teams involved for match id '{match_id}'")
        return None, None
    elif len(match_header_links) >= 1:
        team_1_tag = match_header_links[0]
        team_1_str = team_1_tag.get("href", None)

        team_2_tag = match_header_links[1]
        team_2_str = team_2_tag.get("href", None)

        try:
            if team_1_str:
                team_1_id = get_id_from_url(VLRScraperMode.TEAM, team_1_str)
        except Exception:
            team_1_id = None
        
        try:
            if team_2_str:
                team_2_id = get_id_from_url(VLRScraperMode.TEAM, team_2_str)
        except Exception:
            team_2_id = None
    else:
        LOGGER.error(f"Not enough match header link tags scraped, and therefore, cannot infer the teams involved for match id '{match_id}'")
        return None, None
    
    return team_1_id, team_2_id

@soup_cast 
def infer_event_from_match(root: Tag | BeautifulSoup | str, match_id: int | None) -> int | None:
    match_header_event_tag = root.find("a", class_="match-header-event")

    if not match_header_event_tag:
        LOGGER.error(f"Could not find match header event tag for match with match id '{match_id}'")
        return None
    
    href = match_header_event_tag.get("href", None)
    if not href:
        LOGGER.error(f"Could not retrieve href property from tag {match_header_event_tag} for match with match id '{match_id}'")

    event_id = get_id_from_url(VLRScraperMode.EVENT, url=href)

    return event_id

@soup_cast
def scrape_match_vods(root: Tag | BeautifulSoup | str) -> List[str]:
    links: List[Tag] = root.findAll('a')
    return [href for link in links if (href := link.get('href')) is not None]

@soup_cast
def scrape_match_streams(root: Tag | BeautifulSoup | str) -> List[str]:
    links: List[Tag] = root.findAll('a')
    return [href for link in links if (href := link.get('href')) is not None]
