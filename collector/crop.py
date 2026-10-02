from __future__ import annotations

from datetime import date
from pathlib import Path

from PIL import Image


# Ratios are tied to the two documented table templates and are deliberately
# rejected when the image aspect ratio drifts materially.
PROFILES = {
    "namsan_dorm": {"aspect": 1017 / 753, "table": (0.010, 0.153, 0.991, 0.816), "left_end": 0.136},
    "dflex": {"aspect": 1131 / 808, "table": (0.024, 0.149, 0.971, 0.758), "left_end": 0.179},
}


def crop_daily_column(source: Path, destination: Path, restaurant_id: str, requested_date: date, week_start: date) -> dict[str, object]:
    if restaurant_id not in PROFILES:
        raise ValueError(f"지원하지 않는 크롭 프로필: {restaurant_id}")
    day_index = (requested_date - week_start).days
    if day_index not in range(5):
        raise ValueError("게시판 이미지 크롭은 월~금만 지원합니다")
    profile = PROFILES[restaurant_id]
    with Image.open(source) as image:
        width, height = image.size
        aspect = width / height
        if abs(aspect - profile["aspect"]) / profile["aspect"] > 0.04:
            raise ValueError("이미지 비율이 검증된 템플릿과 다릅니다")
        tx0, ty0, tx1, ty1 = profile["table"]
        left_end = profile["left_end"]
        date_width = (tx1 - left_end) / 5
        x0 = left_end + date_width * day_index
        x1 = x0 + date_width
        left = image.crop((round(tx0 * width), round(ty0 * height), round(left_end * width), round(ty1 * height)))
        day = image.crop((round(x0 * width), round(ty0 * height), round(x1 * width), round(ty1 * height)))
        output = Image.new("RGB", (left.width + day.width, max(left.height, day.height)), "white")
        output.paste(left, (0, 0))
        output.paste(day, (left.width, 0))
        destination.parent.mkdir(parents=True, exist_ok=True)
        output.save(destination, format="PNG", optimize=True)
        return {"path": str(destination), "width": output.width, "height": output.height, "method": "validated-template-ratio"}
