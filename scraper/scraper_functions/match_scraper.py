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
        if stage_round_components > 2:
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
                    
                try:
                    score_1 = int(score_1_str)
                    score_2 = int(score_2_str)
                except Exception as e:
                    LOGGER.error(f"Found scores for game with match id of '{match_id}' but could not parse score as an int (score_1='{score_1_str}', score_2='{score_2_str}')")
                    return None, None, None
            elif len(winner_loser_team_tags) != 0:
                LOGGER.error(f"Could not find score of a game that should have a score (match id of '{match_id}').")
                return None, None, None
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
    elif len(match_header_links) == 2:
        team_1_tag = match_header_links[0]
        team_2_tag = match_header_links[1]

        team_1_str = team_1_tag.get("href", None)
        team_2_str = team_2_tag.get("href", None)

        try:
            if team_1_str:
                team_1_id = get_id_from_url(VLRScraperMode.MATCH, team_1_str)
        except Exception:
            team_1_id = None
                
        try:
            if team_2_str:
                team_2_id = get_id_from_url(VLRScraperMode.MATCH, team_2_str)
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