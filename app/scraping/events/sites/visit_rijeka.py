from app.scraping.events.registry import register_event_scraper
from app.scraping.events.sites._base_listing import ConfigurableListingScraper


@register_event_scraper("visit_rijeka")
class VisitRijekaScraper(ConfigurableListingScraper):
    item_selector = "article, .event, .post"
