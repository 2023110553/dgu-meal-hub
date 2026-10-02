from __future__ import annotations

import re
from datetime import date
from io import BytesIO
from urllib.parse import urlencode, urljoin

import pdfplumber
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


def _line_values(words: list[dict[str, object]]) -> list[str]:
    lines: list[list[object]] = []
    for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
        if not lines or abs(float(lines[-1][0]) - float(word["top"])) > 2:
            lines.append([float(word["top"]), str(word["text"])])
        else:
            lines[-1][1] = str(lines[-1][1]) + " " + str(word["text"])
    merged: list[str] = []
    for _, value in lines:
        text = str(value).strip()
        if text.startswith("&") and merged:
            merged[-1] += text
        elif text:
            merged.append(text)
    return merged


def parse_pdf_day(content: bytes, requested_date: date) -> list[dict[str, object]]:
    """Extract one D-Flex day using the PDF's vector text coordinates."""
    with pdfplumber.open(BytesIO(content)) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError("D-Flex PDF는 1쪽이어야 합니다")
        page = pdf.pages[0]
        words = page.extract_words(x_tolerance=2, y_tolerance=2, keep_blank_chars=False)

        month_words = [word for word in words if re.fullmatch(r"\d{1,2}월", str(word["text"])) and float(word["top"]) < 200]
        day_words = [word for word in words if re.fullmatch(r"\d{1,2}일", str(word["text"])) and float(word["top"]) < 200]
        headers: list[tuple[int, int, float]] = []
        for month_word in month_words:
            month_center = (float(month_word["x0"]) + float(month_word["x1"])) / 2
            day_word = min(day_words, key=lambda item: abs(((float(item["x0"]) + float(item["x1"])) / 2) - month_center))
            day_center = (float(day_word["x0"]) + float(day_word["x1"])) / 2
            headers.append((int(str(month_word["text"])[:-1]), int(str(day_word["text"])[:-1]), (month_center + day_center) / 2))
        headers.sort(key=lambda item: item[2])
        if len(headers) != 5:
            raise ValueError(f"D-Flex 날짜 열 5개를 찾지 못했습니다: {len(headers)}개")
        target_index = next((index for index, item in enumerate(headers) if item[:2] == (requested_date.month, requested_date.day)), None)
        if target_index is None:
            raise ValueError(f"D-Flex PDF에 요청일 {requested_date} 열이 없습니다")

        centers = [item[2] for item in headers]
        middle_edges = [(centers[index - 1] + centers[index]) / 2 for index in range(1, len(centers))]
        left_edge = centers[0] - (middle_edges[0] - centers[0])
        right_edge = centers[-1] + (centers[-1] - middle_edges[-1])
        column_edges = [left_edge, *middle_edges, right_edge]

        row_edges = sorted({
            round(float(rect["top"]), 2)
            for rect in page.rects
            if float(rect["width"]) > float(page.width) * 0.7
            and float(rect["height"]) < 4
            and 180 < float(rect["top"]) < 650
        })
        if len(row_edges) != 4:
            raise ValueError(f"D-Flex 식사 행 경계 4개를 찾지 못했습니다: {len(row_edges)}개")

        definitions = (
            ("중식", "일반식 A코너", 6500),
            ("중식", "특별식 B코너", 7500),
            ("석식", "석식", 6500),
        )
        meals: list[dict[str, object]] = []
        for row_index, (meal_type, corner, price) in enumerate(definitions):
            cell_words = [
                word
                for word in words
                if column_edges[target_index] <= (float(word["x0"]) + float(word["x1"])) / 2 < column_edges[target_index + 1]
                and row_edges[row_index] <= float(word["top"]) < row_edges[row_index + 1]
            ]
            menu = _line_values(cell_words)
            if not menu:
                raise ValueError(f"D-Flex {requested_date} {corner} 메뉴가 비어 있습니다")
            meals.append({"meal_type": meal_type, "corner": corner, "menu": menu, "price_krw": price})
        return meals
