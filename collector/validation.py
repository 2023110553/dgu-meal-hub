from __future__ import annotations

import hashlib
from io import BytesIO

from PIL import Image
from pypdf import PdfReader


class ValidationError(ValueError):
    pass


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
