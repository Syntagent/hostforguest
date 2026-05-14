"""AttractionUpdate accepts gallery / featured image for host photo workflows."""
from app.models.attraction import AttractionUpdate


def test_attraction_update_accepts_image_gallery():
    u = AttractionUpdate(image_gallery=["https://example.com/a.jpg", "data:image/png;base64,xxx"])
    assert u.image_gallery is not None
    assert len(u.image_gallery) == 2


def test_attraction_update_accepts_featured_image():
    u = AttractionUpdate(featured_image_url="https://example.com/hero.jpg")
    assert u.featured_image_url == "https://example.com/hero.jpg"
