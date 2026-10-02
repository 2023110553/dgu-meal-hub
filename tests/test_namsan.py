from datetime import date
from pathlib import Path

from collector.boards import select_post
from collector.namsan import parse_detail, parse_posts


FIXTURES = Path(__file__).parent / "fixtures"


def test_posts_and_date_selection() -> None:
    posts = parse_posts((FIXTURES / "dorm.html").read_text(encoding="utf-8"))
    assert select_post(posts, date(2026, 10, 2)).article_id == "215215"
    assert select_post(posts, date(2026, 10, 5)).article_id == "215423"
    assert select_post(posts, date(2026, 10, 4)) is None


def test_detail_assets_are_dynamic() -> None:
    assets = parse_detail((FIXTURES / "dorm-detail.html").read_text(encoding="utf-8"))
    assert assets["image_url"].endswith("physical=1790128846944.png&contentType=image")
    assert "fileDown.do" in assets["pdf_url"]
    assert "215215" in assets["pdf_url"]


def test_empty_html() -> None:
    assert parse_posts("<html></html>") == []
    assert parse_detail("<html></html>") == {"article_id": None, "image_url": None, "pdf_url": None}
