from typing import List
from bs4 import BeautifulSoup, Tag
from logging_config import VLR_LOGGER as LOGGER
from scraper.entities import TeamStatus
from scraper.scraper_utils import soup_cast

@soup_cast
def scrape_series_name(root: Tag | str, team_id: int | None) -> str | None:
    title_tag = root.find("div", class_="wf-title")
    if title_tag is None:
        LOGGER.error(f"Could not find title tag for team with team id'{team_id}'")
        return None
    
    title = title_tag.text.strip()

    return title