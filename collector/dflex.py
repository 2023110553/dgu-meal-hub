from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from .boards import WeeklyPost
from .dates import parse_date_range


BASE_URL = "https://www.dongguk.edu"
LIST_URL = f"{BASE_URL}/article/FOODDFLEX/list"
DETAIL_RE = re.compile(r"goDetail\(\s*(\d+)\s*\)")
DOWNLOAD_RE = re.compile(r"downGO\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*\)")


def parse_posts(text: str) -> list[WeeklyPost]:
    soup = BeautifulSoup(text, "html.parser")
    posts: list[WeeklyPost] = []
    for anchor in soup.find_all("a", onclick=DETAIL_RE):
        match = DETAIL_RE.search(anchor.get("onclick", ""))
        title_node = anchor.select_one(".tit")
        title = (title_node or anchor).get_text(" ", strip=True)
        if not match:
            continue
        try:
            period = parse_date_range(title)
        except ValueError:
            continue
        article_id = match.group(1)
        posts.append(WeeklyPost(article_id, title, period, f"{BASE_URL}/article/FOODDFLEX/detail/{article_id}"))
    return list({post.article_id: post for post in posts}.values())


def parse_detail(text: str) -> dict[str, str | None]:
    soup = BeautifulSoup(text, "html.parser")
    article = soup.select_one("input#article_seq[value]")
    image = next((img.get("src") for img in soup.find_all("img") if "/cmmn/fileView" in img.get("src", "") and "FOODDFLEX" in img.get("src", "")), None)
    pdf_url = None
    for anchor in soup.select(".view_files a[href]"):
        match = DOWNLOAD_RE.search(anchor.get("href", ""))
        if match:
            query = urlencode({"filename": match.group(1), "filepath": match.group(2), "filerealname": match.group(3)})
            pdf_url = f"{BASE_URL}/cmmn/fileDown.do?{query}"
            break
    return {"article_id": article.get("value") if article else None, "image_url": urljoin(BASE_URL, image) if image else None, "pdf_url": pdf_url}
