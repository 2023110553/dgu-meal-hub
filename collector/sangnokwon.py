from __future__ import annotations

import re
from datetime import date, timedelta

from bs4 import BeautifulSoup, Tag

from .dates import DateRange, parse_date_range
from .validation import validate_sangnokwon_html


SOURCE_URL = "https://dgucoop.dongguk.edu/store/store.php?w=4&l=2"
PRICE_RE = re.compile(r"[￦₩]\s*([\d,]+)")


def decode_html(content: bytes) -> str:
    for encoding in ("euc-kr", "cp949"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            pass
    return content.decode("euc-kr", errors="replace")


def parse_week(text: str) -> DateRange:
    soup = BeautifulSoup(text, "html.parser")
    element = soup.select_one(".menu_date")
    if element is None:
        raise ValueError("menu_date 요소가 없습니다")
    return parse_date_range(element.get_text(" ", strip=True))


def _lines(cell: Tag) -> list[str]:
    price_nodes = cell.find_all("span", style=lambda value: value and "#ff0000" in value.lower())
    for node in price_nodes:
        node.extract()
    return [part.strip() for part in cell.get_text("\n", strip=True).splitlines() if part.strip()]


def parse_day(text: str, requested_date: date) -> dict[str, object]:
    validate_sangnokwon_html(text)
    soup = BeautifulSoup(text, "html.parser")
    week = parse_week(text)
    if not week.contains(requested_date):
        raise ValueError(f"요청일 {requested_date}이 원본 주간 범위에 없습니다")
    day_index = (requested_date - week.start).days
    heading = next((node for node in soup.select("td.menu_st") if "상록원3층식당" in node.get_text("", strip=True).replace(" ", "")), None)
    if heading is None:
        raise ValueError("상록원 3층 식당 구역이 없습니다")

    meals: list[dict[str, object]] = []
    category: str | None = None
    for row in heading.find_parent("tr").find_next_siblings("tr"):
        if row.select_one("td.menu_st") is not None:
            break
        cells = row.find_all("td", recursive=False)
        meal_position = next((index for index, cell in enumerate(cells) if cell.get_text("", strip=True) in {"중식", "석식"}), None)
        if meal_position is None:
            continue
        if meal_position > 0:
            category = cells[meal_position - 1].get_text(" ", strip=True).replace("\n", " ")
        day_cells = cells[meal_position + 1 :]
        if day_index >= len(day_cells):
            raise ValueError("날짜 열과 식단 셀 수가 일치하지 않습니다")
        cell = day_cells[day_index]
        raw_text = cell.get_text("\n", strip=True)
        price_match = PRICE_RE.search(raw_text)
        menu = _lines(cell)
        if not menu:
            continue
        meals.append({
            "meal_type": cells[meal_position].get_text(" ", strip=True),
            "corner": category,
            "menu": menu,
            "price_krw": int(price_match.group(1).replace(",", "")) if price_match else None,
        })
    return {
        "id": "sangnokwon_3f",
        "name": "상록원 3층",
        "status": "SUCCESS" if meals else "NO_MENU",
        "source_url": SOURCE_URL,
        "source_detail_url": None,
        "source_week_start": week.start.isoformat(),
        "source_week_end": week.end.isoformat(),
        "meals": meals,
        "original_image_url": None,
        "daily_crop_path": None,
        "artifacts": {},
        "error": None,
    }


def week_offset(requested_date: date, displayed_week: DateRange) -> int:
    if displayed_week.contains(requested_date):
        return 0
    return (requested_date - displayed_week.start).days // 7
