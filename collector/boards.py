from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .dates import DateRange


@dataclass(frozen=True)
class WeeklyPost:
    article_id: str
    title: str
    date_range: DateRange
    detail_url: str


def select_post(posts: list[WeeklyPost], requested_date: date) -> WeeklyPost | None:
    matching = [post for post in posts if post.date_range.contains(requested_date)]
    if not matching:
        return None
    return sorted(matching, key=lambda post: (post.date_range.start, int(post.article_id)), reverse=True)[0]
