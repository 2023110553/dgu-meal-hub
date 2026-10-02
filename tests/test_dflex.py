from datetime import date
from pathlib import Path
from urllib.parse import unquote

from collector.boards import select_post
from collector.dflex import parse_detail, parse_posts


FIXTURES = Path(__file__).parent / "fixtures"


def test_javascript_posts_and_date_selection() -> None:
    posts = parse_posts((FIXTURES / "dflex.html").read_text(encoding="utf-8"))
    assert select_post(posts, date(2026, 10, 2)).article_id == "26766355"
    assert select_post(posts, date(2026, 10, 5)).article_id == "26766452"


def test_detail_assets_are_dynamic() -> None:
    assets = parse_detail((FIXTURES / "dflex-detail.html").read_text(encoding="utf-8"))
    assert assets["image_url"].endswith("physical=1790121323439.png&contentType=image")
    decoded = unquote(assets["pdf_url"])
    assert "26766355" in decoded
    assert "9A09437E9075418998AACB2FA415C68D.pdf" in decoded


def test_empty_html() -> None:
    assert parse_posts("<html></html>") == []
