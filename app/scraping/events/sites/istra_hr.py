from app.scraping.events.registry import register_event_scraper
from app.scraping.events.sites._base_listing import ConfigurableListingScraper


@register_event_scraper("istra_hr")
class IstraHrScraper(ConfigurableListingScraper):
    item_selector = "article, .event, .manifestacija, .views-row"
