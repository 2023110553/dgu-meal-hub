from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from . import dflex, namsan, sangnokwon
from .boards import WeeklyPost, select_post
from .crop import crop_daily_column
from .download import build_session, download_asset, fetch
from .validation import ValidationError, sha256_bytes, validate_png


def _base_result(requested_date: date) -> dict[str, object]:
    return {"requested_date": requested_date.isoformat(), "timezone": "Asia/Seoul", "collected_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(), "restaurants": []}


def _board_result(restaurant_id: str, name: str, list_url: str, post: WeeklyPost | None, detail: dict[str, str | None] | None, error: str | None = None) -> dict[str, object]:
    if post is None:
        return {"id": restaurant_id, "name": name, "status": "NOT_PUBLISHED", "source_url": list_url, "source_detail_url": None, "source_week_start": None, "source_week_end": None, "meals": [], "original_image_url": None, "daily_crop_path": None, "artifacts": {}, "error": error or "요청 날짜를 포함하는 게시물이 없습니다"}
    return {"id": restaurant_id, "name": name, "status": "SUCCESS" if detail and detail.get("image_url") else "PARTIAL_SUCCESS", "source_url": list_url, "source_detail_url": post.detail_url, "source_week_start": post.date_range.start.isoformat(), "source_week_end": post.date_range.end.isoformat(), "meals": [], "original_image_url": detail.get("image_url") if detail else None, "pdf_url": detail.get("pdf_url") if detail else None, "daily_crop_path": None, "artifacts": {}, "error": error}


def _attach_offline_image(result: dict[str, object], source: Path, output_dir: Path, requested_date: date) -> None:
    content = source.read_bytes()
    result["artifacts"]["image"] = {**validate_png(content), "path": str(source)}
    crop_path = output_dir / "crops" / f"{result['id']}-{requested_date.isoformat()}.png"
    crop = crop_daily_column(source, crop_path, str(result["id"]), requested_date, date.fromisoformat(str(result["source_week_start"])))
    result["daily_crop_path"] = str(crop_path)
    result["artifacts"]["crop"] = crop


def collect_offline(requested_date: date, fixtures_dir: Path, output_dir: Path) -> dict[str, object]:
    output = _base_result(requested_date)
    sangnok_text = sangnokwon.decode_html((fixtures_dir / "menu.html").read_bytes())
    output["restaurants"].append(sangnokwon.parse_day(sangnok_text, requested_date))
    for module, restaurant_id, name, list_name, detail_name, image_name in (
        (namsan, "namsan_dorm", "남산학사", "dorm.html", "dorm-detail.html", "dorm-week.png"),
        (dflex, "dflex", "경영관 D-Flex", "dflex.html", "dflex-detail.html", "dflex-week.png"),
    ):
        posts = module.parse_posts((fixtures_dir / list_name).read_text(encoding="utf-8"))
        post = select_post(posts, requested_date)
        fixture_detail = module.parse_detail((fixtures_dir / detail_name).read_text(encoding="utf-8"))
        detail = fixture_detail if post and fixture_detail.get("article_id") == post.article_id else None
        result = _board_result(restaurant_id, name, module.LIST_URL, post, detail)
        if detail is not None:
            _attach_offline_image(result, fixtures_dir / image_name, output_dir, requested_date)
        output["restaurants"].append(result)
    return output


def _failure(restaurant_id: str, name: str, source_url: str, exc: Exception) -> dict[str, object]:
    status = "ACCESS_BLOCKED" if "보안 확인" in str(exc) else "DOWNLOAD_ERROR"
    if isinstance(exc, (ValueError, ValidationError)):
        status = "VALIDATION_ERROR"
    return {"id": restaurant_id, "name": name, "status": status, "source_url": source_url, "source_detail_url": None, "source_week_start": None, "source_week_end": None, "meals": [], "original_image_url": None, "daily_crop_path": None, "artifacts": {}, "error": str(exc)}


def collect_live(requested_date: date, output_dir: Path) -> dict[str, object]:
    output = _base_result(requested_date)
    session = build_session()
    try:
        response = fetch(session, sangnokwon.SOURCE_URL)
        text = sangnokwon.decode_html(response.content)
        displayed = sangnokwon.parse_week(text)
        offset = sangnokwon.week_offset(requested_date, displayed)
        if offset:
            response = fetch(session, sangnokwon.SOURCE_URL + "&" + urlencode({"j": offset}))
            text = sangnokwon.decode_html(response.content)
        result = sangnokwon.parse_day(text, requested_date)
        result["artifacts"]["html"] = {"size": len(response.content), "sha256": sha256_bytes(response.content), "content_type": response.headers.get("Content-Type")}
        output["restaurants"].append(result)
    except Exception as exc:
        output["restaurants"].append(_failure("sangnokwon_3f", "상록원 3층", sangnokwon.SOURCE_URL, exc))

    for module, restaurant_id, name in ((namsan, "namsan_dorm", "남산학사"), (dflex, "dflex", "경영관 D-Flex")):
        try:
            listing = fetch(session, module.LIST_URL)
            posts = module.parse_posts(listing.text)
            post = select_post(posts, requested_date)
            if post is None:
                output["restaurants"].append(_board_result(restaurant_id, name, module.LIST_URL, None, None))
                continue
            detail_response = fetch(session, post.detail_url, method="GET")
            detail = module.parse_detail(detail_response.text)
            result = _board_result(restaurant_id, name, module.LIST_URL, post, detail)
            result["artifacts"]["list_html"] = {"size": len(listing.content), "sha256": sha256_bytes(listing.content), "content_type": listing.headers.get("Content-Type")}
            if detail.get("image_url"):
                try:
                    image_path = output_dir / "original" / f"{restaurant_id}-{post.article_id}.png"
                    result["artifacts"]["image"] = download_asset(session, module.BASE_URL, str(detail["image_url"]), image_path, "png")
                    crop_path = output_dir / "crops" / f"{restaurant_id}-{requested_date.isoformat()}.png"
                    result["artifacts"]["crop"] = crop_daily_column(image_path, crop_path, restaurant_id, requested_date, post.date_range.start)
                    result["daily_crop_path"] = str(crop_path)
                except Exception as asset_exc:
                    result["artifacts"]["image_error"] = str(asset_exc)
                    result["status"] = "PARTIAL_SUCCESS"
            if detail.get("pdf_url"):
                try:
                    pdf_path = output_dir / "original" / f"{restaurant_id}-{post.article_id}.pdf"
                    result["artifacts"]["pdf"] = download_asset(session, module.BASE_URL, str(detail["pdf_url"]), pdf_path, "pdf")
                except Exception as asset_exc:
                    result["artifacts"]["pdf_error"] = str(asset_exc)
                    result["status"] = "PARTIAL_SUCCESS"
            output["restaurants"].append(result)
        except Exception as exc:
            output["restaurants"].append(_failure(restaurant_id, name, module.LIST_URL, exc))
    return output
