from typing import List
from bs4 import BeautifulSoup, Tag
from logging_config import VLR_LOGGER as LOGGER
from scraper.entities import TeamStatus
from scraper.scraper_utils import soup_cast

@soup_cast
def scrape_team_name(root: Tag | str, team_id: int | None) -> tuple[str | None, str | None]:
    """
    Scrapes team name and team tricode (if exists). `team_id` is an optional argument that provides the logger with more details.
    """
    wf_name_container = root.find("div", class_="team-header-name")

    team_name_tag = wf_name_container.find("h1", class_="wf-title")
    if team_name_tag:
        team_name = team_name_tag.text.strip()
    else:
        LOGGER.error(f"Could not find the team name for team with id '{team_id}'")
        return None, None

    team_tricode_tag = wf_name_container.find("h2", class_="team-header-tag")
    if team_tricode_tag:
        team_tricode = team_tricode_tag.text.strip()
    else:
        team_tricode = None

    return team_name, team_tricode

@soup_cast
def scrape_team_region(root: Tag | str, team_id: int | None) -> tuple[str | None, str | None]:
    """
    Scrapes team region short and long name (e.g. sg would be the short form of singapore). `team_id` is an optional argument that provides the logger with more details.
    """

    if isinstance(root, str):
        root = BeautifulSoup(root, "lxml")

    flag_container = root.find("div", class_="team-header-country")

    if not flag_container:
        LOGGER.error(f"Could not find flag container for team with team id '{team_id}'")
        return None, None
    
    flag_short_tag = flag_container.find("i", class_="flag")
    if flag_short_tag:
        classNames = flag_short_tag.get("class")
        region_short = None
        for className in classNames:
            if className.startswith("mod-"):
                # Found region short name
                region_short = className.strip()[4:] # mod- is 4 characters
                break
    else:
        region_short = None

    # Find full name

    region_long = flag_container.text.strip()

    return region_short, region_long

@soup_cast
def scrape_team_status(root: Tag | str, team_id: int | None) -> TeamStatus:
    """
    Scrapes team status (inactive, active or unknown) for a team. `team_id` is an optional argument that provides the logger with more details.
    """

    if isinstance(root, str):
        root = BeautifulSoup(root, "lxml")
    
    team_header_status_tag: Tag | None = root.find("span", class_="team-header-status")

    if team_header_status_tag:
        team_header_status_str: str = team_header_status_tag.text.strip().lower()
        # A team will be marked inactive if it has "(inactive)" as the text content
        if "inactive" in team_header_status_str:
            return TeamStatus.INACTIVE
        else:
            return TeamStatus.UNKNOWN
    else:
        # No team header status tag means the team is implicitly active
        return TeamStatus.ACTIVE

@soup_cast
def scrape_team_logo(root: Tag | str, team_id: int | None) -> str:
    """
    Scrapes team logo (as a url). `team_id` is an optional argument that provides the logger with more details.
    """

    if isinstance(root, str):
        root = BeautifulSoup(root, "lxml")

    team_logo_container: Tag | None = root.find("div", class_="team-header-logo")

    if not team_logo_container:
        LOGGER.error(f"Could not find team logo for team with team id '{team_id}'")
        return ""
    
    team_logo_tag = team_logo_container.find("img")

    if not team_logo_tag:
        LOGGER.error(f"Could not find team logo img url for team with team id '{team_id}'")
        return ""
    
    team_logo_url = team_logo_tag.get("src")

    return team_logo_url
    
@soup_cast
def scrape_team_socials(root: Tag | str, team_id: int | None) -> list[str]:
    """
    Scrapes team socials. `team_id` is an optional argument that provides the logger with more details.
    """

    if isinstance(root, str):
        root = BeautifulSoup(root, "lxml")
    
    socials_container: Tag | None = root.find("div", class_="team-header-links")

    socials: list[str] = []
    if not socials_container:
        return socials

    socials_links: List[Tag] = socials_container.findAll("a")

    for link in socials_links:
        href = link.get("href")
        href = href.strip()

        if len(href) > 0:
            socials.append(href)
    
    return socials