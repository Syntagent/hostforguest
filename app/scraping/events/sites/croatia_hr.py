from app.scraping.events.registry import register_event_scraper
from app.scraping.events.sites._base_listing import ConfigurableListingScraper


@register_event_scraper("croatia_hr")
class CroatiaHrScraper(ConfigurableListingScraper):
    item_selector = "article, .event-item, .news-item, .card"
