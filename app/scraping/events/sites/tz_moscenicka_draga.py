"""Visit Mošćenička Draga — disabled until listing URL is stable."""

from app.scraping.events.registry import register_event_scraper
from app.scraping.events.sites._base_listing import ConfigurableListingScraper


@register_event_scraper("tz_moscenicka_draga")
class TzMoscenickaDragaScraper(ConfigurableListingScraper):
    item_selector = "article, .event, .views-row, .card, .post"
