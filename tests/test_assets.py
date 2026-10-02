from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from collector.crop import crop_daily_column
from collector.validation import ValidationError, validate_pdf, validate_png


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("name,size", [("dorm-week.png", (1017, 753)), ("dflex-week.png", (1131, 808))])
def test_png_validation(name: str, size: tuple[int, int]) -> None:
    metadata = validate_png((FIXTURES / name).read_bytes())
    assert (metadata["width"], metadata["height"]) == size


@pytest.mark.parametrize("restaurant,name", [("namsan_dorm", "dorm-week.png"), ("dflex", "dflex-week.png")])
def test_daily_crop(restaurant: str, name: str, tmp_path: Path) -> None:
    destination = tmp_path / f"{restaurant}.png"
    result = crop_daily_column(FIXTURES / name, destination, restaurant, date(2026, 10, 2), date(2026, 9, 28))
    assert destination.exists()
    with Image.open(destination) as image:
        assert image.width == result["width"]
        assert image.height == result["height"]


def test_invalid_signatures() -> None:
    with pytest.raises(ValidationError):
        validate_png(b"<html>error</html>")
    with pytest.raises(ValidationError):
        validate_pdf(b"<html>error</html>")
