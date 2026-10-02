from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .boards import WeeklyPost
from .dates import parse_date_range


BASE_URL = "https://dorm.dongguk.edu"
LIST_URL = f"{BASE_URL}/article/food/list"
DETAIL_RE = re.compile(r"/article/food/detail/(\d+)")


def parse_posts(text: str) -> list[WeeklyPost]:
    soup = BeautifulSoup(text, "html.parser")
    posts: list[WeeklyPost] = []
    for anchor in soup.find_all("a", href=DETAIL_RE):
        match = DETAIL_RE.search(anchor.get("href", ""))
        title = anchor.get_text(" ", strip=True)
        if not match:
            continue
        try:
            period = parse_date_range(title)
        except ValueError:
            continue
        posts.append(WeeklyPost(match.group(1), title, period, urljoin(BASE_URL, anchor["href"].split("?")[0])))
    return _unique(posts)


def _unique(posts: list[WeeklyPost]) -> list[WeeklyPost]:
    return list({post.article_id: post for post in posts}.values())


def parse_detail(text: str) -> dict[str, str | None]:
    soup = BeautifulSoup(text, "html.parser")
    article = soup.select_one("input#article_seq[value]")
    image = next((img.get("src") for img in soup.find_all("img") if "/cmmn/fileView" in img.get("src", "") and "ckeditor" in img.get("src", "")), None)
    pdf = next((a.get("href", "").strip() for a in soup.select(".view_files a[href]") if "fileDown.do" in a.get("href", "")), None)
    return {"article_id": article.get("value") if article else None, "image_url": urljoin(BASE_URL, image) if image else None, "pdf_url": urljoin(BASE_URL, pdf) if pdf else None}
