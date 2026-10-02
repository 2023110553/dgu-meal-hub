from datetime import date
from pathlib import Path

import pytest

from collector.sangnokwon import decode_html, parse_day, parse_mobile_day, parse_week
from collector.service import _raise_sangnokwon_structure_failure, _sangnokwon_attempt
from collector.validation import ResponseClassificationError, ValidationError, classify_sangnokwon_response, validate_sangnokwon_html


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


def test_mobile_fallback_matches_desktop_menu() -> None:
    mobile = (FIXTURES / "sangnokwon-mobile.html").read_text(encoding="utf-8")
    result = parse_mobile_day(mobile, date(2026, 10, 2))
    assert result["status"] == "SUCCESS"
    assert result["source_data_scope"] == "day"
    assert any("쇠고기국밥(뚝)" in meal["menu"] for meal in result["meals"])
    assert any("간장파불고기(뚝)" in meal["menu"] for meal in result["meals"])
    assert all(meal["price_krw"] == 7000 for meal in result["meals"])


@pytest.mark.parametrize(
    ("text", "status_code", "final_url", "kind"),
    [
        ("<html>Please prove that you are human.</html>", 200, "https://dgucoop.dongguk.edu/store/store.php?w=4&l=2", "CAPTCHA"),
        ("<html>Forbidden</html>", 403, "https://dgucoop.dongguk.edu/store/store.php?w=4&l=2", "ACCESS_RESTRICTED"),
        ("<html>error</html>", 503, "https://dgucoop.dongguk.edu/store/store.php?w=4&l=2", "SERVER_ERROR"),
        ("<html>login</html>", 200, "https://example.com/login", "UNEXPECTED_REDIRECT"),
        ("<html>changed</html>", 200, "https://dgucoop.dongguk.edu/store/store.php?w=4&l=2", "HTML_STRUCTURE_CHANGED"),
    ],
)
def test_sangnokwon_failure_classification(text: str, status_code: int, final_url: str, kind: str) -> None:
    with pytest.raises(ResponseClassificationError) as captured:
        classify_sangnokwon_response(text, status_code=status_code, final_url=final_url, content_type="text/html", route="desktop_week")
    assert captured.value.failure_kind == kind


def test_normal_sangnokwon_response_is_accepted(html: str) -> None:
    classify_sangnokwon_response(
        html,
        status_code=200,
        final_url="https://dgucoop.dongguk.edu/store/store.php?w=4&l=2",
        content_type="text/html",
        route="desktop_week",
    )


def test_failed_response_is_saved_without_headers(tmp_path: Path) -> None:
    class FakeResponse:
        content = b"<html>Please prove that you are human.</html>"
        status_code = 200
        url = "https://dgucoop.dongguk.edu/store/store.php?w=4&l=2"
        headers = {"Content-Type": "text/html; charset=UTF-8", "Set-Cookie": "must-not-be-recorded"}
        history = []

    class FakeSession:
        def request(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    attempts: list[dict[str, object]] = []
    with pytest.raises(ResponseClassificationError):
        _sangnokwon_attempt(
            FakeSession(),
            FakeResponse.url,
            "desktop_week",
            tmp_path,
            attempts,
        )

    debug_path = tmp_path / "debug" / "sangnokwon-desktop_week-response.html"
    assert debug_path.read_bytes() == FakeResponse.content
    assert attempts[0]["status_code"] == 200
    assert attempts[0]["final_url"] == FakeResponse.url
    assert attempts[0]["content_type"] == "text/html; charset=UTF-8"
    assert attempts[0]["size"] == len(FakeResponse.content)
    assert attempts[0]["failure_kind"] == "CAPTCHA"
    assert "Set-Cookie" not in attempts[0]


def test_parser_failure_is_classified_and_archived(tmp_path: Path) -> None:
    class FakeResponse:
        content = b"<html>menu_date changed table</html>"

    attempts: list[dict[str, object]] = [{"status": "SUCCESS"}]
    with pytest.raises(ResponseClassificationError) as captured:
        _raise_sangnokwon_structure_failure(
            FakeResponse(),
            "desktop_week",
            tmp_path,
            attempts,
            ValueError("table layout changed"),
        )

    assert captured.value.failure_kind == "HTML_STRUCTURE_CHANGED"
    assert attempts[0]["status"] == "PARSE_ERROR"
    assert attempts[0]["failure_kind"] == "HTML_STRUCTURE_CHANGED"
    assert (tmp_path / "debug" / "sangnokwon-desktop_week-response.html").read_bytes() == FakeResponse.content
