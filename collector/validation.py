from __future__ import annotations

import hashlib
from io import BytesIO
from urllib.parse import urlparse

from PIL import Image
from pypdf import PdfReader


class ValidationError(ValueError):
    pass


class ResponseClassificationError(ValidationError):
    def __init__(self, status: str, failure_kind: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.failure_kind = failure_kind


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_png(content: bytes) -> dict[str, object]:
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValidationError("PNG 시그니처가 없습니다")
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
    except Exception as exc:
        raise ValidationError(f"PNG 디코딩 실패: {exc}") from exc
    return {"format": "PNG", "width": width, "height": height, "size": len(content), "sha256": sha256_bytes(content)}


def validate_pdf(content: bytes) -> dict[str, object]:
    if not content.startswith(b"%PDF-"):
        raise ValidationError("PDF 시그니처가 없습니다")
    if len(content) < 1024:
        raise ValidationError("PDF가 비정상적으로 작습니다")
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        extracted = "".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValidationError(f"PDF 로드 실패: {exc}") from exc
    return {
        "format": "PDF",
        "size": len(content),
        "sha256": sha256_bytes(content),
        "pages": len(reader.pages),
        "extracted_text_chars": len(extracted.strip()),
        "has_extractable_text": bool(extracted.strip()),
    }


def validate_sangnokwon_html(text: str) -> None:
    lowered = text.lower()
    if "please prove that you are human" in lowered:
        raise ValidationError("보안 확인 페이지가 반환되었습니다")
    required = ("menu_date", "상록원3층식당")
    missing = [token for token in required if token not in text]
    if missing:
        raise ValidationError(f"필수 콘텐츠가 없습니다: {', '.join(missing)}")


def classify_sangnokwon_response(
    text: str,
    *,
    status_code: int,
    final_url: str,
    content_type: str | None,
    route: str,
) -> None:
    """Reject non-menu responses while preserving a machine-readable reason."""
    if status_code >= 500:
        raise ResponseClassificationError("DOWNLOAD_ERROR", "SERVER_ERROR", f"상록원 서버 오류 HTTP {status_code}")
    if status_code in {401, 403, 429}:
        raise ResponseClassificationError("ACCESS_BLOCKED", "ACCESS_RESTRICTED", f"상록원 접근 제한 HTTP {status_code}")
    if status_code >= 400:
        raise ResponseClassificationError("DOWNLOAD_ERROR", "HTTP_ERROR", f"상록원 HTTP 오류 {status_code}")

    parsed = urlparse(final_url)
    expected_path = "/store/store.php" if route == "desktop_week" else "/mobile/menu.html"
    if parsed.hostname != "dgucoop.dongguk.edu" or parsed.path != expected_path:
        raise ResponseClassificationError(
            "DOWNLOAD_ERROR",
            "UNEXPECTED_REDIRECT",
            f"예상하지 못한 최종 URL: {final_url}",
        )
    if content_type and "html" not in content_type.lower():
        raise ResponseClassificationError(
            "VALIDATION_ERROR",
            "UNEXPECTED_CONTENT_TYPE",
            f"HTML이 아닌 Content-Type: {content_type}",
        )

    lowered = text.lower()
    captcha_markers = (
        "please prove that you are human",
        "자동등록방지를 위해 보안절차",
        "captcha",
        "cf-chl-",
        "hcaptcha",
        "g-recaptcha",
    )
    access_markers = ("access denied", "request blocked", "forbidden", "접근이 제한", "접근 권한이 없습니다")
    if any(marker in lowered for marker in captcha_markers):
        raise ResponseClassificationError("ACCESS_BLOCKED", "CAPTCHA", "자동등록 방지 또는 CAPTCHA 페이지가 반환되었습니다")
    if any(marker in lowered for marker in access_markers):
        raise ResponseClassificationError("ACCESS_BLOCKED", "ACCESS_RESTRICTED", "접근 제한 페이지가 반환되었습니다")

    required = ("menu_date", "상록원3층식당") if route == "desktop_week" else ("상록원3층식당", "중식", "석식")
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ResponseClassificationError(
            "PARSE_ERROR",
            "HTML_STRUCTURE_CHANGED",
            f"정상 식단 HTML 식별자가 없습니다: {', '.join(missing)}",
        )
