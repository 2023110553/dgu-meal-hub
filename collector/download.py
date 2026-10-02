from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .validation import validate_pdf, validate_png


USER_AGENT = "dgu-meal-hub-feasibility/0.1 (+https://github.com/2023110553/dgu-meal-hub)"


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7"})
    retry = Retry(total=2, connect=2, read=2, backoff_factor=0.8, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET", "POST"))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch(session: requests.Session, url: str, *, method: str = "GET") -> requests.Response:
    response = session.request(method, url, timeout=(5, 20), allow_redirects=True)
    response.raise_for_status()
    return response


def download_asset(session: requests.Session, base_url: str, asset_url: str, destination: Path, kind: str) -> dict[str, object]:
    response = fetch(session, urljoin(base_url, asset_url))
    content = response.content
    metadata = validate_png(content) if kind == "png" else validate_pdf(content)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return {**metadata, "content_type": response.headers.get("Content-Type"), "url": response.url, "path": str(destination)}
