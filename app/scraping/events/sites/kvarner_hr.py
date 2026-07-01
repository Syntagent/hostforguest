from app.scraping.events.registry import register_event_scraper
from app.scraping.events.sites._base_listing import ConfigurableListingScraper


@register_event_scraper("kvarner_hr")
class KvarnerHrScraper(ConfigurableListingScraper):
    item_selector = "article, .event-list-item, .calendar-event, .node"
