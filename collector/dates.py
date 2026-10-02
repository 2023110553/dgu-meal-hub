from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end


_DATE = re.compile(r"(?P<year>\d{2,4})\s*[./-]\s*(?P<month>\d{1,2})\s*[./-]\s*(?P<day>\d{1,2})")


def _as_date(match: re.Match[str]) -> date:
    year = int(match.group("year"))
    if year < 100:
        year += 2000
    return date(year, int(match.group("month")), int(match.group("day")))


def parse_date_range(text: str) -> DateRange:
    matches = list(_DATE.finditer(text))
    if len(matches) < 2:
        raise ValueError(f"날짜 범위를 찾을 수 없습니다: {text!r}")
    start, end = _as_date(matches[0]), _as_date(matches[1])
    if end < start:
        raise ValueError(f"종료일이 시작일보다 빠릅니다: {text!r}")
    return DateRange(start, end)


def korean_today() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()
