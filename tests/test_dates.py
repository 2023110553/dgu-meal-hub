from datetime import date

import pytest

from collector.boards import WeeklyPost, select_post
from collector.dates import DateRange, parse_date_range


def test_parse_cross_month_range() -> None:
    period = parse_date_range("주간 식단표 (26.09.28~26.10.02)")
    assert period == DateRange(date(2026, 9, 28), date(2026, 10, 2))


def test_parse_cross_year_range() -> None:
    period = parse_date_range("2026.12.28. ~ 2027.01.01.")
    assert period.contains(date(2027, 1, 1))


def test_select_by_containment_not_latest() -> None:
    old = WeeklyPost("1", "old", DateRange(date(2026, 9, 28), date(2026, 10, 2)), "/1")
    new = WeeklyPost("2", "new", DateRange(date(2026, 10, 5), date(2026, 10, 9)), "/2")
    assert select_post([new, old], date(2026, 10, 2)) == old
    assert select_post([new, old], date(2026, 10, 5)) == new
    assert select_post([new, old], date(2026, 10, 4)) is None


def test_invalid_range_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_date_range("날짜 없음")
