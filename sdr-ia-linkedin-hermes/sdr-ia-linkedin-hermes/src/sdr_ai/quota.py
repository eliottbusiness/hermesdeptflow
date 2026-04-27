from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from .config import ClientConfig


@dataclass
class QuotaState:
    day: str
    iso_week: str
    daily_connections: int = 0
    weekly_connections: int = 0
    daily_visits: int = 0


class QuotaManager:
    def __init__(self, config: ClientConfig, state_dir: str | Path = "runs/quota") -> None:
        self.config = config
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.state_dir / f"{config.slug}.json"
        self.state = self._load()

    def _load(self) -> QuotaState:
        today = date.today().isoformat()
        week = _iso_week_key(date.today())
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            state = QuotaState(**data)
            if state.day != today:
                state.day = today
                state.daily_connections = 0
                state.daily_visits = 0
            if state.iso_week != week:
                state.iso_week = week
                state.weekly_connections = 0
            return state
        return QuotaState(day=today, iso_week=week)

    def save(self) -> None:
        self.path.write_text(json.dumps(self.state.__dict__, indent=2), encoding="utf-8")

    def can_visit(self) -> bool:
        return self.state.daily_visits < self.config.bereach.daily_profile_visit_limit

    def can_connect(self) -> bool:
        return (
            self.state.daily_connections < self.config.bereach.daily_connection_limit
            and self.state.weekly_connections < self.config.bereach.weekly_connection_limit
        )

    def register_visit(self) -> None:
        self.state.daily_visits += 1
        self.save()

    def register_connection(self) -> None:
        self.state.daily_connections += 1
        self.state.weekly_connections += 1
        self.save()

    def weekly_usage_ratio(self) -> float:
        limit = max(self.config.bereach.weekly_connection_limit, 1)
        return self.state.weekly_connections / limit


def _iso_week_key(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def working_window_ok(config: ClientConfig, now: datetime | None = None) -> bool:
    now = now or datetime.now(tz=UTC).astimezone()
    if config.bereach.weekend_pause and now.weekday() >= 5:
        return False
    if config.bereach.working_hours_only and not (8 <= now.hour < 18):
        return False
    return True
