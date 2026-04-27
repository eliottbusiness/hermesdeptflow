from __future__ import annotations

import hashlib
import json
import random
import re
import time
from datetime import UTC, date, datetime
from typing import Any

from dateutil import parser as date_parser


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"(^-|-$)", "", value) or "client"


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    try:
        dt = date_parser.parse(str(value))
    except (ValueError, TypeError, OverflowError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def stable_id(*parts: str) -> str:
    joined = "|".join(parts)
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]
    return f"{datetime.now(tz=UTC).strftime('%Y%m%d')}-{digest}"


def contains_any(haystack: str, needles: list[str]) -> bool:
    hay = normalize_text(haystack)
    return any(normalize_text(needle) in hay for needle in needles if needle)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def sleep_jitter(min_seconds: float, max_seconds: float, dry_run: bool = False) -> float:
    delay = random.uniform(min_seconds, max_seconds)
    if not dry_run:
        time.sleep(delay)
    return delay


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)
