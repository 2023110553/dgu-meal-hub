from datetime import date
from pathlib import Path

import pytest

from collector.sangnokwon import decode_html, parse_day, parse_week
from collector.validation import ValidationError, validate_sangnokwon_html


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def html() -> str:
    return decode_html((FIXTURES / "menu.html").read_bytes())


def test_week_range(html: str) -> None:
    period = parse_week(html)
    assert period.start == date(2026, 9, 27)
    assert period.end == date(2026, 10, 3)


def test_october_second_menu_and_price(html: str) -> None:
    result = parse_day(html, date(2026, 10, 2))
    assert result["id"] == "sangnokwon_3f"
    assert result["status"] == "SUCCESS"
    assert any("쇠고기국밥(뚝)" in meal["menu"] for meal in result["meals"])
    assert any("간장파불고기(뚝)" in meal["menu"] for meal in result["meals"])
    assert all(meal["price_krw"] == 7000 for meal in result["meals"])


def test_other_restaurant_is_not_mixed(html: str) -> None:
    result = parse_day(html, date(2026, 10, 2))
    flattened = " ".join(item for meal in result["meals"] for item in meal["menu"])
    assert "교직원식당" not in flattened


def test_wrong_week_is_rejected(html: str) -> None:
    with pytest.raises(ValueError):
        parse_day(html, date(2026, 10, 5))


def test_captcha_is_detected() -> None:
    with pytest.raises(ValidationError):
        validate_sangnokwon_html("<html>Please prove that you are human.</html>")
