
from logging_config import MAIN_LOGGER as LOGGER
from scraper.entities import VLRSeries
from scraper.scraper import VLRScraper, VLRScraperOptions

SCRAPER: VLRScraper

def main():
    global SCRAPER  

    SCRAPER_OPTIONS = VLRScraperOptions(

    )

    SCRAPER = VLRScraper(SCRAPER_OPTIONS)
    debugSeries(74)
    # debugSeries(79)
    # debugSeries(82)

def debugSeries(series_id: int):
    global SCRAPER

    series, event_ids = SCRAPER.scrape_series(series_id)
    LOGGER.debug(series)
    LOGGER.debug(event_ids)

    event, match_ids = SCRAPER.scrape_event(event_ids.pop(), series_id)

    LOGGER.debug(event)
    LOGGER.debug(match_ids)



if __name__ == "__main__":
    main();