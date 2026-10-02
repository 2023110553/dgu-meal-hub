from datetime import date
from pathlib import Path

from collector.dflex import parse_pdf_day


FIXTURES = Path(__file__).parent / "fixtures"


def test_october_second_pdf_menu_matches_original_image() -> None:
    meals = parse_pdf_day((FIXTURES / "dflex-week.pdf").read_bytes(), date(2026, 10, 2))
    assert meals == [
        {
            "meal_type": "중식",
            "corner": "일반식 A코너",
            "menu": ["(뚝)우삼겹순두부찌개&쫄면사리", "쌀밥", "너비아니그린빈스조림", "올리브샐러드", "배추김치"],
            "price_krw": 6500,
        },
        {
            "meal_type": "중식",
            "corner": "특별식 B코너",
            "menu": ["돼지고기마제덮밥&계란후라이", "콩나물국", "치킨커틀렛", "매콤떡볶이", "배추김치"],
            "price_krw": 7500,
        },
        {
            "meal_type": "석식",
            "corner": "석식",
            "menu": ["미트소스스파게티&해물굴소스볶음밥", "어묵국", "고구마고로케", "그린샐러드&오리엔탈D", "오이피클/배추김치"],
            "price_krw": 6500,
        },
    ]


def test_pdf_rejects_date_outside_week() -> None:
    try:
        parse_pdf_day((FIXTURES / "dflex-week.pdf").read_bytes(), date(2026, 10, 5))
    except ValueError as exc:
        assert "요청일" in str(exc)
    else:
        raise AssertionError("주간 범위 밖 날짜가 거부되지 않았습니다")


def test_all_five_date_columns_are_structured_without_ai() -> None:
    pdf = (FIXTURES / "dflex-week.pdf").read_bytes()
    expected_first_menu = {
        date(2026, 9, 28): "(뚝)돈가스김치나베&우동사리",
        date(2026, 9, 29): "(뚝)주꾸미샤브샤브&만두사리",
        date(2026, 9, 30): "(뚝)육개장&칼국수사리",
        date(2026, 10, 1): "(뚝)순살돼지갈비찜&당면사리",
        date(2026, 10, 2): "(뚝)우삼겹순두부찌개&쫄면사리",
    }
    for requested_date, first_menu in expected_first_menu.items():
        meals = parse_pdf_day(pdf, requested_date)
        assert len(meals) == 3
        assert meals[0]["menu"][0] == first_menu
        assert [meal["price_krw"] for meal in meals] == [6500, 7500, 6500]
